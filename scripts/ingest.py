"""
ingest.py — compile raw/ files into wiki/ pages.

Usage:
    python3 scripts/ingest.py             # process all new files
    python3 scripts/ingest.py --all       # reprocess everything
    python3 scripts/ingest.py raw/articles/foo.md
"""
import argparse
import json
import queue as _queue
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from llm import IMAGE_SUFFIXES, BillingExhaustedException, chat, describe_image, load_settings, schema_text

_LOCK = threading.Lock()

ROOT = Path(__file__).parent.parent
RAW = ROOT / "raw"
WIKI = ROOT / "wiki"
LOG = WIKI / "log.md"
PROCESSED = ROOT / ".processed.json"

SYSTEM_PROMPT = f"""You are a knowledge base compiler. Your job is to read source material
and update a structured wiki following the schema below.

{schema_text()}

CRITICAL LANGUAGE RULE:
Write ALL page content in Chinese (Simplified): titles, section headings, body text, bullet points.
Only keep English for: file paths, wikilink slugs [[like-this]], and metadata field labels
(**Type:**, **Status:**, **Last updated:**) plus their identifier values (concept, stub, etc.).

IMPORTANT OUTPUT FORMAT:
Return ONLY a JSON array. Each element is a wiki page to create or update:
[
  {{
    "path": "wiki/concepts/attention-mechanism.md",
    "action": "create" | "update",
    "content": "full markdown content of the page"
  }},
  ...
]

Rules:
- Maximum 12 pages per ingest
- Use [[wikilinks]] for all cross-references
- Every page must follow the template in schema.md exactly
- Return valid JSON only, no commentary outside the JSON array
"""


def load_processed() -> set[str]:
    if PROCESSED.exists():
        return set(json.loads(PROCESSED.read_text()))
    return set()


def save_processed(processed: set[str]) -> None:
    PROCESSED.write_text(json.dumps(sorted(processed), indent=2))


def route_backend(content_len: int) -> str | None:
    """Return backend override based on article size, or None to use global setting."""
    s = load_settings()
    p = s.get("parallel", {})
    if not p.get("enabled", False):
        return None
    threshold = p.get("size_threshold_chars", 3000)
    if content_len >= threshold:
        return p.get("large_backend", "claude")
    return p.get("small_backend", "ollama")


def build_raw_image_index() -> dict[str, Path]:
    """Index all image files in raw/ by filename for fast lookup."""
    return {f.name: f for f in RAW.rglob("*") if f.suffix in IMAGE_SUFFIXES}


def find_images_for_article(md_path: Path, raw_index: dict[str, Path]) -> list:
    """
    Parse image references from a .md file.
    Returns local Path objects (found in raw/) and remote URL strings.
    """
    content = md_path.read_text(encoding="utf-8", errors="ignore")
    results = []
    seen: set[str] = set()

    for pattern in [r"!\[.*?\]\(([^)\s]+)[^)]*\)", r"!\[\[([^\]|#]+)\]\]"]:
        for m in re.finditer(pattern, content):
            ref = m.group(1).strip()
            if ref in seen:
                continue
            seen.add(ref)
            if ref.startswith(("http://", "https://")):
                results.append(ref)
            else:
                filename = Path(ref).name
                if filename in raw_index:
                    results.append(raw_index[filename])

    return results


def read_file(path: Path) -> str:
    if path.suffix == ".pdf":
        try:
            import subprocess
            result = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(path)],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout[:8000] if result.returncode == 0 else f"[PDF: {path.name}]"
        except Exception:
            return f"[PDF: {path.name}]"
    return path.read_text(encoding="utf-8", errors="ignore")[:8000]


def get_wiki_context() -> str:
    pages = list(WIKI.rglob("*.md"))
    if not pages:
        return "Wiki is empty — create new pages as needed."
    titles = [str(p.relative_to(ROOT)) for p in pages if p.name not in {"index.md", "log.md"}]
    return f"Existing wiki pages ({len(titles)}):\n" + "\n".join(f"- {t}" for t in titles[:50])


def parse_llm_response(response: str) -> list[dict]:
    response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
    match = re.search(r"\[.*\]", response, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return []


def apply_pages(pages: list[dict], log: Callable) -> tuple[int, int]:
    created = updated = 0
    for page in pages:
        path = ROOT / page["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        existed = path.exists()
        path.write_text(page["content"], encoding="utf-8")
        if existed:
            updated += 1
            log(f"  updated  {page['path']}")
        else:
            created += 1
            log(f"  created  {page['path']}")
    return created, updated


def append_log(source: str, created: int, updated: int, pages: list[dict]) -> None:
    entry = "\n".join([
        f"## {date.today()} — ingest\n",
        f"**Operation:** ingest  ",
        f"**Source:** {source}  ",
        f"**Pages created:** {created}  ",
        f"**Pages updated:** {updated}\n",
        "### Changes\n",
        *[f"- {p['action']} `{p['path']}`" for p in pages],
        "\n---\n",
    ])
    existing = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
    LOG.write_text(entry + "\n" + existing, encoding="utf-8")


def describe_and_label(source, log: Callable) -> str | None:
    label = source if isinstance(source, str) else source.name
    try:
        desc = describe_image(source)
        desc = re.sub(r"<think>.*?</think>", "", desc, flags=re.DOTALL).strip()
        return f"[Image: {label}]\n{desc}"
    except Exception as e:
        log(f"    WARNING: could not describe {label}: {e}")
        return None


def ingest_article(
    path: Path,
    raw_index: dict[str, Path],
    progress_cb: Callable | None = None,
    wiki_context: str | None = None,
    allow_ollama_fallback: bool = False,
) -> None:
    log = progress_cb or print
    rel = str(path.relative_to(ROOT))

    content = read_file(path)
    backend = route_backend(len(content))
    backend_label = f"[{backend or 'default'}]"
    log(f"→ ingesting {rel} {backend_label}")

    image_context = ""
    if path.suffix == ".md":
        images = find_images_for_article(path, raw_index)
        if images:
            log(f"  found {len(images)} image reference(s), describing...")
            descriptions = []
            for src in images:
                label = src if isinstance(src, str) else src.name
                log(f"  vision: {label}")
                result = describe_and_label(src, log)
                if result:
                    descriptions.append(result)
                if isinstance(src, Path):
                    with _LOCK:
                        processed = load_processed()
                        processed.add(str(src.relative_to(ROOT)))
                        save_processed(processed)
            image_context = "\n\n---\nIMAGES REFERENCED IN ARTICLE:\n" + "\n\n".join(descriptions)

    ctx = wiki_context if wiki_context is not None else get_wiki_context()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"SOURCE FILE: {rel}\n\n{content}{image_context}\n\n---\n{ctx}"},
    ]

    log("  calling LLM...")
    response = chat(messages, backend=backend, warn_cb=log, allow_ollama_fallback=allow_ollama_fallback)
    pages = parse_llm_response(response)

    if not pages:
        log("  no pages generated")
        return

    with _LOCK:
        created, updated = apply_pages(pages, log)
        append_log(rel, created, updated, pages)
        processed = load_processed()
        processed.add(rel)
        save_processed(processed)
    log(f"  done: {created} created, {updated} updated")


def ingest_standalone_image(
    path: Path,
    progress_cb: Callable | None = None,
    wiki_context: str | None = None,
    allow_ollama_fallback: bool = False,
) -> None:
    log = progress_cb or print
    rel = str(path.relative_to(ROOT))
    log(f"→ ingesting standalone image {rel}")

    result = describe_and_label(path, log)
    if not result:
        log("  skipping — could not describe image")
        return

    backend = route_backend(len(result))
    ctx = wiki_context if wiki_context is not None else get_wiki_context()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"SOURCE FILE: {rel} (standalone image)\n\n"
            f"FILENAME: {path.name}\n\nIMAGE DESCRIPTION:\n{result}\n\n---\n{ctx}"
        )},
    ]

    log("  calling LLM...")
    response = chat(messages, backend=backend, warn_cb=log, allow_ollama_fallback=allow_ollama_fallback)
    pages = parse_llm_response(response)

    if not pages:
        log("  no pages generated")
        return

    with _LOCK:
        created, updated = apply_pages(pages, log)
        append_log(rel, created, updated, pages)
        processed = load_processed()
        processed.add(rel)
        save_processed(processed)
    log(f"  done: {created} created, {updated} updated")


def find_raw_files(only_new: bool = True, specific: Path | None = None) -> list[Path]:
    if specific:
        return [specific]
    all_files = [
        f for f in RAW.rglob("*")
        if f.is_file()
        and f.suffix in {".md", ".txt", ".pdf"} | IMAGE_SUFFIXES
        and not f.name.startswith(".")
    ]
    if not only_new:
        return all_files
    processed = load_processed()
    return [f for f in all_files if str(f.relative_to(ROOT)) not in processed]


def run_ingest(
    files: list[Path] | None = None,
    only_new: bool = True,
    progress_cb: Callable | None = None,
) -> None:
    """
    Core ingest runner used by both CLI and server.
    Reads parallel settings from settings.json automatically.
    """
    log = progress_cb or print

    if files is None:
        files = find_raw_files(only_new=only_new)
    if not files:
        log("No new files to process.")
        return

    raw_index = build_raw_image_index()
    text_files = [f for f in files if f.suffix not in IMAGE_SUFFIXES]
    image_files = [f for f in files if f.suffix in IMAGE_SUFFIXES]

    log(f"Found {len(files)} file(s) ({len(text_files)} text, {len(image_files)} image).")

    # Snapshot wiki context once so parallel workers share a consistent baseline
    wiki_ctx = get_wiki_context()

    s = load_settings()
    p = s.get("parallel", {})
    workers = p.get("workers", 3) if p.get("enabled", False) else 1

    if workers > 1 and len(text_files) > 1:
        log(f"Running {workers} parallel workers...")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {
                pool.submit(ingest_article, f, raw_index, log, wiki_ctx): f
                for f in text_files
            }
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as e:
                    log(f"  ERROR: {futs[fut].name}: {e}")
    else:
        for f in text_files:
            ingest_article(f, raw_index, log, wiki_ctx)

    processed = load_processed()
    remaining = [f for f in image_files if str(f.relative_to(ROOT)) not in processed]
    for f in remaining:
        ingest_standalone_image(f, log, wiki_ctx)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest raw files into wiki")
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    specific = [args.file] if args.file else None
    run_ingest(files=specific, only_new=not args.all)
    print("\nAll done.")


class IngestWorker(threading.Thread):
    """Persistent background thread — processes ingest queue one file at a time."""

    STATUS_FILE = ROOT / ".ingest_status.json"

    def __init__(self):
        super().__init__(daemon=True, name="ingest-worker")
        self._q: _queue.Queue = _queue.Queue()
        self._queued_set: set[str] = set()
        self._lock = threading.Lock()
        self._status: dict = {
            "running": False,
            "current_file": None,
            "queued": 0,
            "log": [],
            "started_at": None,
            "finished_at": None,
            "total_processed": 0,
            "last_error": None,
            "billing_fallback": False,
            "billing_fallback_msg": "",
            "billing_needs_confirm": False,
            "billing_confirm_msg": "",
        }
        # Event used to pause/resume the worker while awaiting user confirmation
        self._confirm_event = threading.Event()
        self._confirm_result: bool | None = None  # True=use Ollama, False=skip
        self._restore_status()

    # ── Public API ─────────────────────────────────────────────────────────────

    def enqueue(self, path: Path) -> bool:
        """Add a single file. Returns False if already queued or processed."""
        rel = str(path.relative_to(ROOT))
        if rel in load_processed():
            return False
        with self._lock:
            if rel in self._queued_set:
                return False
            self._queued_set.add(rel)
        self._q.put(path)
        self._update_queued()
        return True

    def clear_billing_fallback(self) -> None:
        with self._lock:
            self._status["billing_fallback"] = False
            self._status["billing_fallback_msg"] = ""
        self._persist()

    def confirm_ollama(self) -> None:
        """User agreed to use local Ollama as fallback. Resume worker."""
        with self._lock:
            self._status["billing_needs_confirm"] = False
            self._status["billing_confirm_msg"] = ""
        self._confirm_result = True
        self._confirm_event.set()
        self._persist()

    def reject_ollama(self) -> None:
        """User declined Ollama fallback. Skip current file and resume queue."""
        with self._lock:
            self._status["billing_needs_confirm"] = False
            self._status["billing_confirm_msg"] = ""
        self._confirm_result = False
        self._confirm_event.set()
        self._persist()

    def enqueue_unprocessed(self) -> int:
        """Queue all files not yet processed. Returns count added."""
        files = find_raw_files(only_new=True)
        added = 0
        for f in files:
            if self.enqueue(f):
                added += 1
        return added

    def get_status(self) -> dict:
        with self._lock:
            s = dict(self._status)
            s["log"] = list(self._status["log"])
        s["queued"] = self._q.qsize()
        return s

    # ── Internals ──────────────────────────────────────────────────────────────

    def _update_queued(self):
        with self._lock:
            self._status["queued"] = self._q.qsize()
        self._persist()

    def _log(self, msg: str):
        with self._lock:
            self._status["log"].append(msg)
            if len(self._status["log"]) > 80:
                self._status["log"] = self._status["log"][-80:]
            if "余额不足" in msg:
                self._status["billing_fallback"] = True
                self._status["billing_fallback_msg"] = msg.strip().lstrip("WARNING:").strip()
        self._persist()

    def _persist(self):
        try:
            self.STATUS_FILE.write_text(
                json.dumps(self.get_status(), indent=2, default=str),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _restore_status(self):
        if self.STATUS_FILE.exists():
            try:
                data = json.loads(self.STATUS_FILE.read_text())
                with self._lock:
                    self._status["total_processed"] = data.get("total_processed", 0)
                    self._status["finished_at"] = data.get("finished_at")
                    self._status["log"] = data.get("log", [])[-20:]
                    self._status["billing_fallback"] = data.get("billing_fallback", False)
                    self._status["billing_fallback_msg"] = data.get("billing_fallback_msg", "")
                    # Never restore a pending confirmation across restarts — let user re-trigger
                    self._status["billing_needs_confirm"] = False
                    self._status["billing_confirm_msg"] = ""
            except Exception:
                pass

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _run_with_confirm(
        self,
        path: Path,
        raw_index: dict[str, Path],
        wiki_ctx: str,
        allow_ollama_fallback: bool = False,
    ) -> bool | None:
        """Run ingest for one file, handling BillingExhaustedException.

        Returns True on success, None if user rejected Ollama (file skipped).
        Raises on other errors.
        """
        try:
            if path.suffix in IMAGE_SUFFIXES:
                ingest_standalone_image(
                    path,
                    progress_cb=self._log,
                    wiki_context=wiki_ctx,
                    allow_ollama_fallback=allow_ollama_fallback,
                )
            else:
                ingest_article(
                    path,
                    raw_index,
                    progress_cb=self._log,
                    wiki_context=wiki_ctx,
                    allow_ollama_fallback=allow_ollama_fallback,
                )
            return True
        except BillingExhaustedException as e:
            confirm_msg = str(e)
            self._log(f"  WARNING: {confirm_msg}")
            with self._lock:
                self._status["billing_needs_confirm"] = True
                self._status["billing_confirm_msg"] = confirm_msg
            self._persist()

            # Block until user responds (confirm_ollama / reject_ollama sets the event)
            self._confirm_event.clear()
            self._confirm_result = None
            self._confirm_event.wait()  # indefinitely — user must respond

            if self._confirm_result:
                self._log("  用户确认：启用 Ollama，重试处理中…")
                return self._run_with_confirm(path, raw_index, wiki_ctx, allow_ollama_fallback=True)
            else:
                self._log("  用户拒绝启用 Ollama，跳过此文件")
                return None

    # ── Worker loop ────────────────────────────────────────────────────────────

    def run(self):
        raw_index = build_raw_image_index()
        idle_ticks = 0

        while True:
            try:
                path = self._q.get(timeout=5)
            except _queue.Empty:
                idle_ticks += 1
                if idle_ticks % 12 == 0:          # rebuild image index every ~60s
                    raw_index = build_raw_image_index()
                continue

            idle_ticks = 0
            rel = str(path.relative_to(ROOT))

            # Skip if meanwhile processed by another run
            if rel in load_processed():
                with self._lock:
                    self._queued_set.discard(rel)
                self._q.task_done()
                continue

            with self._lock:
                self._status.update({
                    "running": True,
                    "current_file": rel,
                    "started_at": datetime.now().isoformat(),
                    "log": [],
                    "last_error": None,
                    "billing_fallback": False,
                    "billing_fallback_msg": "",
                    "billing_needs_confirm": False,
                    "billing_confirm_msg": "",
                })
            self._persist()

            try:
                wiki_ctx = get_wiki_context()
                allow_ollama = self._run_with_confirm(path, raw_index, wiki_ctx)
                if allow_ollama is None:
                    # User rejected Ollama — file skipped, not an error
                    with self._lock:
                        self._status["last_error"] = "用户拒绝启用 Ollama，已跳过此文件"
                else:
                    with self._lock:
                        self._status["total_processed"] += 1
                        self._status["last_error"] = None

            except Exception as e:
                with self._lock:
                    self._status["last_error"] = str(e)
                self._log(f"ERROR: {e}")

            finally:
                with self._lock:
                    self._queued_set.discard(rel)
                    self._status.update({
                        "running": False,
                        "current_file": None,
                        "finished_at": datetime.now().isoformat(),
                    })
                self._persist()
                self._q.task_done()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
