"""Small durable JSON metadata registry; no raw source CSV in routine logs."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class LocalStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS objects (kind TEXT NOT NULL, id TEXT NOT NULL, "
                       "payload TEXT NOT NULL, created_at_utc TEXT NOT NULL, PRIMARY KEY(kind,id))")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def put(self, kind: str, object_id: str, payload: dict) -> None:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO objects(kind,id,payload,created_at_utc) VALUES(?,?,?,?)",
                       (kind, object_id, encoded, datetime.now(timezone.utc).isoformat()))

    def get(self, kind: str, object_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM objects WHERE kind=? AND id=?", (kind, object_id)).fetchone()
        return None if row is None else json.loads(row[0])

    def list(self, kind: str) -> tuple[dict, ...]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM objects WHERE kind=? ORDER BY created_at_utc", (kind,)).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

    def delete(self, kind: str, object_id: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM objects WHERE kind=? AND id=?", (kind, object_id))
