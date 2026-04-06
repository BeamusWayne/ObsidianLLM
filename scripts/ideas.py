"""ideas.py — Simple CRUD for quick ideas/notes stored in ideas.json."""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
IDEAS_FILE = ROOT / "ideas.json"


def _load() -> list[dict]:
    if IDEAS_FILE.exists():
        return json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    return []


def _save(ideas: list[dict]) -> None:
    IDEAS_FILE.write_text(json.dumps(ideas, indent=2, ensure_ascii=False))


def list_ideas() -> list[dict]:
    return sorted(_load(), key=lambda x: x["created_at"], reverse=True)


def create_idea(content: str) -> dict:
    ideas = _load()
    idea: dict = {
        "id": str(uuid.uuid4()),
        "content": content,
        "created_at": datetime.now().isoformat(),
        "ai_expanded": None,
        "tags": [],
    }
    ideas.append(idea)
    _save(ideas)
    return idea


def update_idea(idea_id: str, data: dict) -> Optional[dict]:
    ideas = _load()
    for i, idea in enumerate(ideas):
        if idea["id"] == idea_id:
            updated = {**idea, **{k: v for k, v in data.items() if k != "id"}}
            ideas[i] = updated
            _save(ideas)
            return updated
    return None


def delete_idea(idea_id: str) -> bool:
    ideas = _load()
    new_ideas = [x for x in ideas if x["id"] != idea_id]
    if len(new_ideas) == len(ideas):
        return False
    _save(new_ideas)
    return True
