"""Loading the bundled history into an empty database."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pymongo.database import Database

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "hollins.json"

STAMPS = {
    "articles": ("updated_at",),
    "accounts": ("created_at",),
    "tickets": ("opened_at", "first_reply_at", "closed_at"),
}


def read_history(path: Optional[Path] = None) -> Dict[str, Any]:
    with open(path or DATA_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def as_datetime(value: Any) -> Any:
    """The file keeps its times as text; the database wants them as dates."""
    if not isinstance(value, str):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def prepared(rows: List[Dict[str, Any]], fields: tuple) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        row = dict(row)
        for field in fields:
            if field in row:
                row[field] = as_datetime(row[field])
        out.append(row)
    return out


def load_seed(database: Database, path: Optional[Path] = None) -> Dict[str, int]:
    """Put the history in. Writes nothing to a collection that already has rows in it."""
    history = read_history(path)
    written = {}
    for name, fields in STAMPS.items():
        collection = database[name]
        if collection.estimated_document_count():
            written[name] = 0
            continue
        rows = prepared(history.get(name, []), fields)
        if rows:
            collection.insert_many(rows)
        written[name] = len(rows)
    return written
