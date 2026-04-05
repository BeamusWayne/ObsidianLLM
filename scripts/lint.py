"""
lint.py — health check the wiki for inconsistencies, orphans, missing fields.

Usage:
    python3 scripts/lint.py           # report only
    python3 scripts/lint.py --fix     # report and auto-fix
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

from llm import chat, schema_text

ROOT = Path(__file__).parent.parent
WIKI = ROOT / "wiki"

SYSTEM_PROMPT = f"""You are a wiki quality auditor. Analyze the provided wiki pages and find issues.

{schema_text()}

IMPORTANT OUTPUT FORMAT:
Return ONLY a JSON object:
{{
  "issues": [
    {{
      "type": "orphan" | "stub" | "broken_link" | "contradiction" | "missing_field" | "stale",
      "page": "wiki/path/to/page.md",
      "description": "what is wrong",
      "fix": "suggested fix or null if manual review needed"
    }}
  ],
  "fixes": [
    {{
      "path": "wiki/path/to/page.md",
      "content": "full corrected page content"
    }}
  ]
}}

Only include fixes for issues you are confident about (orphans, missing fields, broken links).
Do NOT include fixes for contradictions — flag them for human review.
"""


def find_all_pages() -> list[Path]:
    return [p for p in WIKI.rglob("*.md") if p.name not in {"log.md"}]


def find_broken_links(pages: list[Path]) -> dict[str, list[str]]:
    """Find [[wikilinks]] that point to non-existent pages."""
    all_names = {p.stem for p in WIKI.rglob("*.md")}
    broken: dict[str, list[str]] = {}
    for page in pages:
        content = page.read_text(encoding="utf-8")
        links = re.findall(r"\[\[([^\]|#]+)", content)
        bad = [l for l in links if l.strip() not in all_names]
        if bad:
            broken[str(page.relative_to(ROOT))] = bad
    return broken


def find_orphans(pages: list[Path]) -> list[str]:
    """Find pages that no other page links to."""
    all_content = " ".join(p.read_text(encoding="utf-8") for p in pages)
    orphans = []
    for page in pages:
        if page.name in {"index.md", "log.md"}:
            continue
        if f"[[{page.stem}]]" not in all_content:
            orphans.append(str(page.relative_to(ROOT)))
    return orphans


def build_context(pages: list[Path]) -> str:
    broken = find_broken_links(pages)
    orphans = find_orphans(pages)

    parts = [f"WIKI STATS: {len(pages)} pages\n"]

    if orphans:
        parts.append(f"ORPHAN PAGES (no inbound links):\n" + "\n".join(f"- {o}" for o in orphans))

    if broken:
        parts.append("BROKEN LINKS:")
        for page, links in broken.items():
            parts.append(f"- {page}: {', '.join(links)}")

    parts.append("\nPAGE CONTENTS (sample — first 200 chars each):")
    for page in pages[:30]:
        rel = str(page.relative_to(ROOT))
        preview = page.read_text(encoding="utf-8")[:200].replace("\n", " ")
        parts.append(f"\n=== {rel} ===\n{preview}...")

    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint the wiki")
    parser.add_argument("--fix", action="store_true", help="auto-fix issues where possible")
    args = parser.parse_args()

    pages = find_all_pages()
    if not pages:
        print("Wiki is empty — nothing to lint.")
        return

    print(f"Checking {len(pages)} pages...")
    context = build_context(pages)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]

    print("Analyzing...")
    import json
    response = chat(messages)
    response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()

    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        print("Could not parse lint response.")
        print(response)
        return

    result = json.loads(match.group())
    issues = result.get("issues", [])
    fixes = result.get("fixes", [])

    if not issues:
        print("Wiki looks healthy — no issues found.")
        return

    print(f"\nFound {len(issues)} issue(s):\n")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. [{issue['type'].upper()}] {issue['page']}")
        print(f"     {issue['description']}")
        if issue.get("fix"):
            print(f"     Fix: {issue['fix']}")
        print()

    if args.fix and fixes:
        print(f"Applying {len(fixes)} fix(es)...")
        for fix in fixes:
            path = ROOT / fix["path"]
            path.write_text(fix["content"], encoding="utf-8")
            print(f"  fixed {fix['path']}")

        # Log the lint run
        log = WIKI / "log.md"
        entry = (
            f"## {date.today()} — lint\n\n"
            f"**Operation:** lint  \n"
            f"**Issues found:** {len(issues)}  \n"
            f"**Issues fixed:** {len(fixes)}\n\n---\n\n"
        )
        existing = log.read_text(encoding="utf-8") if log.exists() else ""
        log.write_text(entry + existing, encoding="utf-8")
    elif args.fix:
        print("No auto-fixable issues.")
    else:
        print("Run with --fix to auto-fix where possible.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
