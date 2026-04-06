"""review_gen.py — Generate weekly reviews and topic research using LLM."""
import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
REVIEWS_FILE = ROOT / "reviews.json"
WIKI = ROOT / "wiki"


def _load_reviews() -> list[dict]:
    if REVIEWS_FILE.exists():
        return json.loads(REVIEWS_FILE.read_text(encoding="utf-8"))
    return []


def _save_reviews(reviews: list[dict]) -> None:
    REVIEWS_FILE.write_text(json.dumps(reviews, indent=2, ensure_ascii=False))


def list_reviews() -> list[dict]:
    return sorted(_load_reviews(), key=lambda x: x["created_at"], reverse=True)


def _load_recent_wiki(days: int = 7) -> str:
    cutoff = datetime.now() - timedelta(days=days)
    pages = []
    for p in sorted(WIKI.rglob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True):
        mtime = datetime.fromtimestamp(p.stat().st_mtime)
        if mtime < cutoff:
            break
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            pages.append(f"--- {p.stem} ---\n{content[:600]}")
        except Exception:
            pass
    return "\n\n".join(pages[:20]) if pages else ""


def _load_all_wiki(max_pages: int = 40) -> str:
    pages = []
    for p in sorted(WIKI.rglob("*.md"))[:max_pages]:
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            pages.append(f"--- {p.stem} ---\n{content[:800]}")
        except Exception:
            pass
    return "\n\n".join(pages) if pages else "(暂无内容)"


def generate_weekly_review() -> dict:
    from llm import chat  # noqa: PLC0415

    context = _load_recent_wiki(days=7)
    if not context:
        context = "(本周暂无新增内容)"

    system = (
        "你是用户的知识助手 Echo。请根据本周添加的知识内容，"
        "生成一份简洁的周回顾报告，包括：主要主题总结、关键洞察、"
        "知识关联发现、以及建议下周深入探索的方向。"
        "用中文回答，语气友好，格式清晰（使用 markdown）。"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"本周新增知识内容：\n\n{context}"},
    ]
    content = chat(messages)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    review: dict = {
        "id": str(uuid.uuid4()),
        "type": "weekly",
        "title": f"{datetime.now().strftime('%Y年%m月%d日')} 周回顾",
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    reviews = _load_reviews()
    reviews.insert(0, review)
    _save_reviews(reviews)
    return review


def generate_topic_review(topic: str) -> dict:
    from llm import chat  # noqa: PLC0415

    wiki_context = _load_all_wiki()
    system = (
        "你是用户的知识助手 Echo。请根据用户的知识库内容，"
        "针对指定主题进行深度分析，包括：相关知识点梳理、关联概念、"
        "知识盲区、以及推荐进一步学习的方向。"
        "用中文回答，结构清晰（使用 markdown）。"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"知识库内容：\n\n{wiki_context}\n\n请深度分析主题：{topic}"},
    ]
    content = chat(messages)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    review: dict = {
        "id": str(uuid.uuid4()),
        "type": "topic",
        "title": f"主题研究：{topic}",
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    reviews = _load_reviews()
    reviews.insert(0, review)
    _save_reviews(reviews)
    return review
