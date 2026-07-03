"""Persistence for deals — JSON file store (local) or SQLite (deployable).

The store interface is deliberately small (save / load / list / delete / exists)
so the backend can be swapped without touching the engine. ``get_store`` picks the
backend: an explicit JSON root wins (test isolation), else the ``DEALLENS_DB``
env var selects SQLite, else the JSON default. SQLite is a one-line change away
from Postgres for hosted multi-user use.
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Dict, List, Optional

from .models import Deal


def default_root() -> str:
    """Resolve the data directory: env override, else ./data/deals beside the pkg."""
    env = os.environ.get("DEALLENS_DATA")
    if env:
        return env
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(pkg_root, "data", "deals")


class JSONFileStore:
    def __init__(self, root: Optional[str] = None):
        self.root = root or default_root()
        os.makedirs(self.root, exist_ok=True)

    def _path(self, deal_id: str) -> str:
        safe = "".join(c for c in deal_id if c.isalnum() or c in ("-", "_"))
        if not safe:
            raise ValueError(f"invalid deal id: {deal_id!r}")
        return os.path.join(self.root, f"{safe}.json")

    def exists(self, deal_id: str) -> bool:
        return os.path.isfile(self._path(deal_id))

    def save(self, deal: Deal) -> None:
        with open(self._path(deal.id), "w", encoding="utf-8") as fh:
            json.dump(deal.to_dict(), fh, indent=2)

    def load(self, deal_id: str) -> Deal:
        path = self._path(deal_id)
        if not os.path.isfile(path):
            raise KeyError(f"deal not found: {deal_id}")
        with open(path, "r", encoding="utf-8") as fh:
            return Deal.from_dict(json.load(fh))

    def delete(self, deal_id: str) -> None:
        path = self._path(deal_id)
        if os.path.isfile(path):
            os.remove(path)

    def list(self) -> List[Dict[str, object]]:
        out = []
        for name in sorted(os.listdir(self.root)):
            if name.endswith(".json"):
                try:
                    with open(os.path.join(self.root, name), "r", encoding="utf-8") as fh:
                        out.append(Deal.from_dict(json.load(fh)).summary())
                except (json.JSONDecodeError, OSError):
                    continue
        return out


class SQLiteStore:
    """SQLite-backed store — one row per deal. Safe for the threaded server.

    A new connection is opened per operation so it works across request threads.
    ``root`` points at a directory (next to the DB file) where reports are written.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("DEALLENS_DB") or os.path.join(default_root(), "..", "deallens.db")
        self.db_path = os.path.abspath(self.db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.root = os.path.dirname(self.db_path)
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS deals (id TEXT PRIMARY KEY, data TEXT NOT NULL, "
                      "updated_at TEXT)")

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def exists(self, deal_id: str) -> bool:
        with self._conn() as c:
            return c.execute("SELECT 1 FROM deals WHERE id=?", (deal_id,)).fetchone() is not None

    def save(self, deal: Deal) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO deals (id, data, updated_at) VALUES (?,?,?) "
                      "ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
                      (deal.id, json.dumps(deal.to_dict()), deal.updated_at))

    def load(self, deal_id: str) -> Deal:
        with self._conn() as c:
            row = c.execute("SELECT data FROM deals WHERE id=?", (deal_id,)).fetchone()
        if row is None:
            raise KeyError(f"deal not found: {deal_id}")
        return Deal.from_dict(json.loads(row["data"]))

    def delete(self, deal_id: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM deals WHERE id=?", (deal_id,))

    def list(self) -> List[Dict[str, object]]:
        with self._conn() as c:
            rows = c.execute("SELECT data FROM deals ORDER BY updated_at DESC").fetchall()
        out = []
        for row in rows:
            try:
                out.append(Deal.from_dict(json.loads(row["data"])).summary())
            except (json.JSONDecodeError, TypeError):
                continue
        return out


def get_store(store_root: Optional[str] = None):
    """Pick a backend: explicit JSON root > DEALLENS_DB (SQLite) > JSON default."""
    if store_root:
        return JSONFileStore(store_root)
    if os.environ.get("DEALLENS_DB"):
        return SQLiteStore(os.environ["DEALLENS_DB"])
    return JSONFileStore(default_root())
