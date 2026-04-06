"""
server.py — FastAPI backend for the wiki knowledge base.
Run:  .venv/bin/uvicorn server:app --reload --port 8000
"""
import asyncio
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "scripts"))

WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
SETTINGS_FILE = ROOT / "settings.json"

app = FastAPI(title="Wiki KB")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Background ingest worker (started once at import time) ─────────────────────
from ingest import IngestWorker

worker = IngestWorker()
worker.start()

# Queue any files left unprocessed from before server restart
_pending = worker.enqueue_unprocessed()
if _pending:
    print(f"[ingest-worker] queued {_pending} previously unprocessed file(s)")


# ── Models ────────────────────────────────────────────────────────────────────

class ClipRequest(BaseModel):
    url: str

class IngestRequest(BaseModel):
    files: list[str] = []  # empty = all new

class QueryRequest(BaseModel):
    question: str
    save: bool = False

class SettingsPayload(BaseModel):
    model_config = {"extra": "allow"}


# ── Settings ──────────────────────────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    from llm import DEFAULT_SETTINGS
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return DEFAULT_SETTINGS


@app.post("/api/settings")
async def save_settings(data: dict):
    SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return {"ok": True}


# ── Graph ─────────────────────────────────────────────────────────────────────

@app.get("/api/graph")
async def get_graph():
    all_pages = {p.stem: p for p in WIKI.rglob("*.md")}
    link_counts: dict[str, int] = {stem: 0 for stem in all_pages}
    nodes = []
    links = []

    for stem, path in all_pages.items():
        content = path.read_text(encoding="utf-8")
        type_m = re.search(r"\*\*Type:\*\*\s*(\w+)", content)
        page_type = type_m.group(1) if type_m else "unknown"

        refs = re.findall(r"\[\[([^\]|#]+)\]\]", content)
        for ref in set(refs):
            ref = ref.strip()
            if ref in all_pages and ref != stem:
                links.append({"source": stem, "target": ref})
                link_counts[ref] = link_counts.get(ref, 0) + 1

        nodes.append({
            "id": stem,
            "label": stem.replace("-", " ").title(),
            "type": page_type,
            "path": str(path.relative_to(ROOT)),
        })

    for node in nodes:
        node["linkCount"] = link_counts.get(node["id"], 0)

    return {"nodes": nodes, "links": links}


# ── Wiki ──────────────────────────────────────────────────────────────────────

@app.get("/api/wiki")
async def list_wiki():
    pages = []
    for p in sorted(WIKI.rglob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True):
        content = p.read_text(encoding="utf-8")
        title_m = re.search(r"^# (.+)$", content, re.MULTILINE)
        type_m = re.search(r"\*\*Type:\*\*\s*(\w+)", content)
        pages.append({
            "path":        str(p.relative_to(ROOT)),
            "stem":        p.stem,
            "title":       title_m.group(1) if title_m else p.stem,
            "type":        type_m.group(1) if type_m else "unknown",
            "source_type": _detect_source_type(content),
            "mtime":       p.stat().st_mtime,
        })
    return pages


@app.get("/api/wiki/{path:path}")
async def get_wiki_page(path: str):
    full_path = ROOT / path
    if not full_path.exists():
        matches = list(WIKI.rglob(f"{Path(path).stem}.md"))
        if not matches:
            raise HTTPException(404, "Page not found")
        full_path = matches[0]

    content = full_path.read_text(encoding="utf-8")
    stem = full_path.stem

    backlinks = []
    for p in WIKI.rglob("*.md"):
        if p == full_path:
            continue
        if f"[[{stem}]]" in p.read_text(encoding="utf-8"):
            backlinks.append({"stem": p.stem, "label": p.stem.replace("-", " ").title()})

    return {
        "path": str(full_path.relative_to(ROOT)),
        "stem": stem,
        "content": content,
        "backlinks": backlinks,
    }


# ── Ignored files ─────────────────────────────────────────────────────────────

IGNORED_FILE = ROOT / ".ignored.json"

def load_ignored() -> set:
    if IGNORED_FILE.exists():
        return set(json.loads(IGNORED_FILE.read_text()))
    return set()

def save_ignored(ignored: set):
    IGNORED_FILE.write_text(json.dumps(sorted(ignored), indent=2))


# ── Raw files ─────────────────────────────────────────────────────────────────

@app.get("/api/raw")
async def list_raw():
    from ingest import load_processed
    processed = load_processed()
    ignored   = load_ignored()
    current   = worker.get_status().get("current_file")
    files = []
    for f in RAW.rglob("*"):
        if not f.is_file() or f.name.startswith("."):
            continue
        rel = str(f.relative_to(ROOT))

        # Determine type by parent folder
        parts = f.relative_to(RAW).parts
        if parts and parts[0] == "articles":
            ftype = "article"
        elif parts and parts[0] == "images":
            ftype = "image"
        else:
            ftype = "other"

        # For articles parse embedded image refs
        images = []
        if ftype == "article" and f.suffix == ".md":
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                imgs = re.findall(r"!\[.*?\]\((raw/images/[^)]+)\)", content)
                images = list(dict.fromkeys(imgs))
            except Exception:
                pass

        files.append({
            "path":      rel,
            "name":      f.name,
            "type":      ftype,
            "processed": rel in processed,
            "ignored":   rel in ignored,
            "active":    rel == current,
            "mtime":     f.stat().st_mtime,
            "images":    images,
        })
    # Sort by mtime descending (newest first) as default
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files


class IgnoreRequest(BaseModel):
    paths: list[str]

@app.post("/api/raw/ignore")
async def ignore_files(req: IgnoreRequest):
    ignored = load_ignored()
    ignored.update(req.paths)
    save_ignored(ignored)
    return {"ok": True}

@app.post("/api/raw/unignore")
async def unignore_files(req: IgnoreRequest):
    ignored = load_ignored()
    ignored.difference_update(req.paths)
    save_ignored(ignored)
    return {"ok": True}


# ── Clip ──────────────────────────────────────────────────────────────────────

@app.post("/api/clip")
async def clip_url(req: ClipRequest):
    from clip import clip
    result = await asyncio.to_thread(clip, req.url, RAW)
    if result.get("error"):
        raise HTTPException(400, result["error"])
    if result.get("path"):
        # Auto-enqueue only when auto_ingest is enabled
        settings = json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}
        if settings.get("auto_ingest", True):
            worker.enqueue(ROOT / result["path"])
    return result


# ── Ingest (background queue) ─────────────────────────────────────────────────

@app.post("/api/ingest")
async def ingest_queue(req: IngestRequest):
    """Enqueue files for background processing. Returns immediately."""
    if req.files:
        ignored = load_ignored()
        added = sum(1 for f in req.files if f not in ignored and worker.enqueue(ROOT / f))
        return {"queued": added}
    else:
        n = worker.enqueue_unprocessed()
        return {"queued": n}


@app.get("/api/ingest/status")
async def ingest_status():
    return worker.get_status()


@app.post("/api/ingest/dismiss-billing")
async def dismiss_billing():
    worker.clear_billing_fallback()
    return {"ok": True}


@app.post("/api/ingest/confirm-ollama")
async def confirm_ollama():
    """User agreed to use local Ollama as emergency fallback. Resume worker."""
    worker.confirm_ollama()
    return {"ok": True}


@app.post("/api/ingest/reject-ollama")
async def reject_ollama():
    """User declined Ollama fallback. Skip current file and resume queue."""
    worker.reject_ollama()
    return {"ok": True}


class TestProviderRequest(BaseModel):
    backend: str  # "ollama", "claude", "custom", "preset:<name>"

@app.post("/api/test-provider")
async def test_provider(req: TestProviderRequest):
    """Test connectivity to a backend. Returns latency on success or error message."""
    def run_sync():
        from llm import test_connection
        return test_connection(req.backend)
    result = await asyncio.to_thread(run_sync)
    return result


# ── Query ─────────────────────────────────────────────────────────────────────

@app.post("/api/query")
async def query(req: QueryRequest):
    def run_sync():
        from llm import chat, schema_text
        from query import load_wiki, save_answer_to_wiki

        system = (
            "You are a knowledge base assistant. Answer using ONLY the wiki pages provided.\n"
            "Cite pages you used as [[page-name]]. If wiki lacks info, say so clearly.\n"
            "Respond in the same language as the question.\n\n"
            f"{schema_text()}"
        )
        wiki_context = load_wiki()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"WIKI:\n{wiki_context}\n\nQUESTION: {req.question}"},
        ]
        answer = chat(messages)
        answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()

        if req.save:
            save_answer_to_wiki(req.question, answer)

        return answer

    answer = await asyncio.to_thread(run_sync)
    return {"answer": answer}


# ── Models ────────────────────────────────────────────────────────────────────

@app.get("/api/models")
async def get_models():
    """Return installed Ollama models."""
    from llm import load_settings, _SSL_CTX
    s = load_settings()
    base = s.get("ollama", {}).get("base_url", "http://localhost:11434")
    installed = []
    available = True
    try:
        req = urllib.request.Request(f"{base}/api/tags")
        with urllib.request.urlopen(req, timeout=4, context=_SSL_CTX) as resp:
            for m in json.loads(resp.read()).get("models", []):
                sz = m.get("size", 0)
                installed.append({
                    "name": m["name"],
                    "size": sz,
                    "size_str": f"{sz/1e9:.1f}GB" if sz >= 1e9 else f"{sz/1e6:.0f}MB",
                })
    except Exception:
        available = False
    return {"installed": installed, "available": available}


@app.post("/api/models/pull")
async def pull_model(data: dict):
    """Pull an Ollama model, streaming progress as SSE."""
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(400, "model name required")
    from llm import load_settings, _SSL_CTX
    s = load_settings()
    base = s.get("ollama", {}).get("base_url", "http://localhost:11434")

    async def generate():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def pull_sync():
            try:
                req = urllib.request.Request(
                    f"{base}/api/pull",
                    data=json.dumps({"name": name}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=3600, context=_SSL_CTX) as resp:
                    for line in resp:
                        line = line.strip()
                        if line:
                            try:
                                loop.call_soon_threadsafe(queue.put_nowait, json.loads(line))
                            except Exception:
                                pass
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"error": str(e)})
            loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.ensure_future(asyncio.to_thread(pull_sync))
        while True:
            item = await queue.get()
            if item is None:
                yield f"data: {json.dumps({'status': 'done'})}\n\n"
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Source type detection ──────────────────────────────────────────────────────

def _detect_source_type(content: str) -> str:
    import re as _re
    m = _re.search(r"\*\*SourceType:\*\*\s*(\w+)", content, _re.IGNORECASE)
    if m:
        return m.group(1).lower()
    for url in _re.findall(r"https?://[^\s\)\"\'\]]+", content):
        u = url.lower()
        if "youtube.com" in u or "youtu.be" in u:
            return "youtube"
        if "twitter.com" in u or "x.com" in u:
            return "twitter"
        if "xiaohongshu.com" in u or "xhslink.com" in u:
            return "xiaohongshu"
    return "article"


# ── Chat (Ori) ────────────────────────────────────────────────────────────────

class ChatMsg(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMsg]
    context: str = "free"  # "free" | "wiki"

@app.post("/api/chat")
async def chat_ori(req: ChatRequest):
    def run_sync():
        from llm import chat
        from query import load_wiki

        msgs = [{"role": m.role, "content": m.content} for m in req.messages]
        if req.context == "wiki":
            wiki_ctx = load_wiki()
            system = (
                "你是 Echo，用户的 AI 知识伙伴。基于以下知识库内容回答问题，"
                "用 [[页面名]] 格式引用相关页面。用提问的语言回答。\n\n"
                f"知识库：\n{wiki_ctx}"
            )
        else:
            system = (
                "你是 Echo，用户的 AI 知识伙伴。帮助用户整理、分析、串联他们收藏的知识。"
                "友好、聪明、有洞察力。用提问的语言回答。"
            )
        reply = chat([{"role": "system", "content": system}] + msgs)
        reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
        return reply

    reply = await asyncio.to_thread(run_sync)
    return {"reply": reply}


# ── Ideas ─────────────────────────────────────────────────────────────────────

class IdeaCreate(BaseModel):
    content: str

class IdeaUpdate(BaseModel):
    model_config = {"extra": "allow"}

@app.get("/api/ideas")
async def list_ideas_api():
    from ideas import list_ideas
    return list_ideas()

@app.post("/api/ideas")
async def create_idea_api(req: IdeaCreate):
    from ideas import create_idea
    return create_idea(req.content)

@app.patch("/api/ideas/{idea_id}")
async def update_idea_api(idea_id: str, data: dict):
    from ideas import update_idea
    result = update_idea(idea_id, data)
    if result is None:
        raise HTTPException(404, "Idea not found")
    return result

@app.delete("/api/ideas/{idea_id}")
async def delete_idea_api(idea_id: str):
    from ideas import delete_idea
    if not delete_idea(idea_id):
        raise HTTPException(404, "Idea not found")
    return {"ok": True}

@app.post("/api/ideas/{idea_id}/expand")
async def expand_idea_api(idea_id: str):
    from ideas import list_ideas, update_idea

    ideas = list_ideas()
    idea = next((i for i in ideas if i["id"] == idea_id), None)
    if not idea:
        raise HTTPException(404, "Idea not found")

    def run_sync():
        from llm import chat
        system = (
            "你是 Echo，用户的知识伙伴。用户有一个想法，请你帮助展开："
            "分析它的潜在含义、关联概念、可以深入探索的方向，以及可能的应用场景。"
            "简洁但有深度，用中文回答。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"我的想法：{idea['content']}"},
        ]
        reply = chat(messages)
        reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
        return reply

    expanded = await asyncio.to_thread(run_sync)
    return update_idea(idea_id, {"ai_expanded": expanded})


# ── Collections ───────────────────────────────────────────────────────────────

class CollectionCreate(BaseModel):
    name: str

class CollectionItemAdd(BaseModel):
    stem: str

@app.get("/api/collections")
async def list_collections_api():
    from collections_store import list_collections
    return list_collections()

@app.post("/api/collections")
async def create_collection_api(req: CollectionCreate):
    from collections_store import create_collection
    return create_collection(req.name)

@app.patch("/api/collections/{col_id}")
async def update_collection_api(col_id: str, data: dict):
    from collections_store import update_collection
    result = update_collection(col_id, data)
    if result is None:
        raise HTTPException(404, "Collection not found")
    return result

@app.delete("/api/collections/{col_id}")
async def delete_collection_api(col_id: str):
    from collections_store import delete_collection
    if not delete_collection(col_id):
        raise HTTPException(404, "Collection not found")
    return {"ok": True}

@app.post("/api/collections/{col_id}/items")
async def add_collection_item(col_id: str, req: CollectionItemAdd):
    from collections_store import add_item
    result = add_item(col_id, req.stem)
    if result is None:
        raise HTTPException(404, "Collection not found")
    return result

@app.delete("/api/collections/{col_id}/items/{stem}")
async def remove_collection_item(col_id: str, stem: str):
    from collections_store import remove_item
    result = remove_item(col_id, stem)
    if result is None:
        raise HTTPException(404, "Collection not found")
    return result


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    from stats import compute_stats
    return await asyncio.to_thread(compute_stats)


# ── Review ────────────────────────────────────────────────────────────────────

class TopicRequest(BaseModel):
    topic: str

@app.get("/api/review")
async def list_reviews_api():
    from review_gen import list_reviews
    return list_reviews()

@app.post("/api/review/weekly")
async def generate_weekly_api():
    from review_gen import generate_weekly_review
    return await asyncio.to_thread(generate_weekly_review)

@app.post("/api/review/topic")
async def generate_topic_api(req: TopicRequest):
    from review_gen import generate_topic_review
    return await asyncio.to_thread(generate_topic_review, req.topic)


# ── Serve raw files (for image thumbnails) ────────────────────────────────────

if RAW.exists():
    app.mount("/raw-files", StaticFiles(directory=str(RAW)), name="raw-files")


# ── Serve frontend (production) ───────────────────────────────────────────────

dist = ROOT / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
