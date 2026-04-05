"""
query.py — ask questions against the wiki.

Usage:
    python3 scripts/query.py "transformer 和 RNN 的核心区别是什么?"
    python3 scripts/query.py "..." --save   # write answer back to wiki
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

from llm import chat, schema_text

ROOT = Path(__file__).parent.parent
WIKI = ROOT / "wiki"

SYSTEM_PROMPT = f"""You are a knowledge base assistant. Answer questions using ONLY
the wiki pages provided. If the wiki doesn't contain enough information, say so clearly.

Wiki schema for reference:
{schema_text()}

Rules:
- Cite the specific wiki pages you used: [[page-name]]
- If information is missing from the wiki, say "Wiki doesn't cover this yet"
- Be concise and direct
- Respond in the same language as the question
"""


def load_wiki(max_chars: int = 60000) -> str:
    """Load all wiki pages into a single context string."""
    pages = sorted(WIKI.rglob("*.md"))
    parts = []
    total = 0
    for page in pages:
        rel = str(page.relative_to(ROOT))
        content = page.read_text(encoding="utf-8")
        entry = f"\n\n=== {rel} ===\n{content}"
        if total + len(entry) > max_chars:
            parts.append(f"\n\n[... {len(pages) - len(parts)} more pages truncated]")
            break
        parts.append(entry)
        total += len(entry)
    return "".join(parts) if parts else "Wiki is empty."


def save_answer_to_wiki(question: str, answer: str) -> None:
    """Optionally save Q&A as a new wiki page."""
    slug = re.sub(r"[^\w\s-]", "", question.lower())
    slug = re.sub(r"[\s_]+", "-", slug)[:50].strip("-")
    path = WIKI / "topics" / f"qa-{slug}.md"

    content = f"""# Q: {question}

**Type:** topic
**Domain:** query-log
**Status:** draft
**Last updated:** {date.today()}

## Answer

{answer}

## Sources

Generated from wiki query on {date.today()}
"""
    path.write_text(content, encoding="utf-8")
    print(f"\n  saved to {path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the wiki")
    parser.add_argument("question", help="your question")
    parser.add_argument("--save", action="store_true", help="save answer as wiki page")
    args = parser.parse_args()

    print("Loading wiki...")
    wiki_context = load_wiki()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"WIKI CONTENT:\n{wiki_context}\n\n"
            f"QUESTION: {args.question}"
        )},
    ]

    print("Thinking...\n")
    answer = chat(messages)

    # Strip <think> blocks from output
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()

    print(answer)

    if args.save:
        save_answer_to_wiki(args.question, answer)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
