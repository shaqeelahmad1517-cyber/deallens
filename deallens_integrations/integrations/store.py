"""Per-user provider connections (tokens) — SQLite (deployed) or JSON (local).

Security note: OAuth tokens are sensitive. They are stored here so imports work
without re-auth. In production, rely on encrypted storage / restricted DB access
(and consider setting DEALLENS_SECRET to enable at-rest obfuscation — see below).
Pending OAuth ``state`` values are also tracked to prevent CSRF on the callback.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
from typing import Dict, List, Optional


def _key(user_id: str, provider: str) -> str:
    return f"{user_id}::{provider}"


def _obfuscate(s: str) -> str:
    """Light XOR obfuscation with DEALLENS_SECRET (NOT a substitute for real
    encryption; deters casual disk inspection only)."""
    secret = os.environ.get("DEALLENS_SECRET")
    if not secret or not s:
        return s
    kb = secret.encode()
    xored = bytes(b ^ kb[i % len(kb)] for i, b in enumerate(s.encode()))
    return "enc:" + base64.b64encode(xored).decode()


def _deobfuscate(s: str) -> str:
    secret = os.environ.get("DEALLENS_SECRET")
    if not s or not s.startswith("enc:") or not secret:
        return s
    kb = secret.encode()
    raw = base64.b64decode(s[4:])
    return bytes(b ^ kb[i % len(kb)] for i, b in enumerate(raw)).decode()


def default_root() -> str:
    env = os.environ.get("DEALLENS_INTEGRATIONS")
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class JSONConnectionStore:
    def __init__(self, root: Optional[str] = None):
        self.root = root or default_root()
        os.makedirs(self.root, exist_ok=True)
        self._path = os.path.join(self.root, "connections.json")
        self._states = os.path.join(self.root, "oauth_states.json")

    def _load(self, path):
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, path, data):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def put(self, user_id, provider, conn):
        data = self._load(self._path)
        conn = dict(conn)
        conn["access_token"] = _obfuscate(conn.get("access_token", ""))
        conn["refresh_token"] = _obfuscate(conn.get("refresh_token", ""))
        data[_key(user_id, provider)] = conn
        self._save(self._path, data)

    def get(self, user_id, provider):
        conn = self._load(self._path).get(_key(user_id, provider))
        if conn:
            conn = dict(conn)
            conn["access_token"] = _deobfuscate(conn.get("access_token", ""))
            conn["refresh_token"] = _deobfuscate(conn.get("refresh_token", ""))
        return conn

    def delete(self, user_id, provider):
        data = self._load(self._path)
        data.pop(_key(user_id, provider), None)
        self._save(self._path, data)

    def list_for_user(self, user_id) -> List[str]:
        return [k.split("::", 1)[1] for k in self._load(self._path) if k.startswith(user_id + "::")]

    def put_state(self, state, user_id, provider):
        d = self._load(self._states)
        d[state] = {"user_id": user_id, "provider": provider}
        self._save(self._states, d)

    def pop_state(self, state):
        d = self._load(self._states)
        v = d.pop(state, None)
        self._save(self._states, d)
        return v


class SQLiteConnectionStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = os.path.abspath(db_path or os.environ.get("DEALLENS_DB") or
                                       os.path.join(default_root(), "integrations.db"))
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS connections (k TEXT PRIMARY KEY, data TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS oauth_states (state TEXT PRIMARY KEY, "
                      "user_id TEXT, provider TEXT)")

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def put(self, user_id, provider, conn):
        conn = dict(conn)
        conn["access_token"] = _obfuscate(conn.get("access_token", ""))
        conn["refresh_token"] = _obfuscate(conn.get("refresh_token", ""))
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO connections (k, data) VALUES (?,?)",
                      (_key(user_id, provider), json.dumps(conn)))

    def get(self, user_id, provider):
        with self._conn() as c:
            row = c.execute("SELECT data FROM connections WHERE k=?", (_key(user_id, provider),)).fetchone()
        if not row:
            return None
        conn = json.loads(row["data"])
        conn["access_token"] = _deobfuscate(conn.get("access_token", ""))
        conn["refresh_token"] = _deobfuscate(conn.get("refresh_token", ""))
        return conn

    def delete(self, user_id, provider):
        with self._conn() as c:
            c.execute("DELETE FROM connections WHERE k=?", (_key(user_id, provider),))

    def list_for_user(self, user_id):
        with self._conn() as c:
            rows = c.execute("SELECT k FROM connections WHERE k LIKE ?", (user_id + "::%",)).fetchall()
        return [r["k"].split("::", 1)[1] for r in rows]

    def put_state(self, state, user_id, provider):
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO oauth_states (state, user_id, provider) VALUES (?,?,?)",
                      (state, user_id, provider))

    def pop_state(self, state):
        with self._conn() as c:
            row = c.execute("SELECT user_id, provider FROM oauth_states WHERE state=?", (state,)).fetchone()
            if row:
                c.execute("DELETE FROM oauth_states WHERE state=?", (state,))
        return {"user_id": row["user_id"], "provider": row["provider"]} if row else None


def get_connection_store(root: Optional[str] = None):
    if root:
        return JSONConnectionStore(root)
    if os.environ.get("DEALLENS_DB"):
        return SQLiteConnectionStore(os.environ["DEALLENS_DB"])
    return JSONConnectionStore(default_root())
