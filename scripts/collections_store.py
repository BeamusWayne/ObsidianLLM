"""collections_store.py — CRUD for named collections of wiki items."""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
COLLECTIONS_FILE = ROOT / "collections.json"


def _load() -> list[dict]:
    if COLLECTIONS_FILE.exists():
        return json.loads(COLLECTIONS_FILE.read_text(encoding="utf-8"))
    return []


def _save(cols: list[dict]) -> None:
    COLLECTIONS_FILE.write_text(json.dumps(cols, indent=2, ensure_ascii=False))


def list_collections() -> list[dict]:
    return _load()


def create_collection(name: str) -> dict:
    cols = _load()
    col: dict = {
        "id": str(uuid.uuid4()),
        "name": name,
        "items": [],
        "created_at": datetime.now().isoformat(),
    }
    cols.append(col)
    _save(cols)
    return col


def update_collection(col_id: str, data: dict) -> Optional[dict]:
    cols = _load()
    for i, col in enumerate(cols):
        if col["id"] == col_id:
            updated = {**col, **{k: v for k, v in data.items() if k != "id"}}
            cols[i] = updated
            _save(cols)
            return updated
    return None


def delete_collection(col_id: str) -> bool:
    cols = _load()
    new_cols = [c for c in cols if c["id"] != col_id]
    if len(new_cols) == len(cols):
        return False
    _save(new_cols)
    return True


def add_item(col_id: str, stem: str) -> Optional[dict]:
    cols = _load()
    for i, col in enumerate(cols):
        if col["id"] == col_id:
            if stem not in col["items"]:
                col["items"].append(stem)
            cols[i] = col
            _save(cols)
            return col
    return None


def remove_item(col_id: str, stem: str) -> Optional[dict]:
    cols = _load()
    for i, col in enumerate(cols):
        if col["id"] == col_id:
            col["items"] = [x for x in col["items"] if x != stem]
            cols[i] = col
            _save(cols)
            return col
    return None
