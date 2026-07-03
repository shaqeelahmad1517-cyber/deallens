"""Persistence for users and sessions — SQLite (deployed) or JSON (local).

Same backend-selection rule as the workspace: DEALLENS_DB -> SQLite, else a JSON
directory. Passwords are never stored in the clear (see engine.py for hashing).
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Dict, List, Optional


def default_root() -> str:
    env = os.environ.get("DEALLENS_ACCOUNTS")
    if env:
        return env
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(pkg_root, "data")


class JSONAccountsStore:
    def __init__(self, root: Optional[str] = None):
        self.root = root or default_root()
        os.makedirs(self.root, exist_ok=True)
        self._users = os.path.join(self.root, "users.json")
        self._sessions = os.path.join(self.root, "sessions.json")

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

    # users keyed by id; email index scanned (small scale)
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        for u in self._load(self._users).values():
            if u["email"].lower() == email.lower():
                return u
        return None

    def get_user(self, user_id: str) -> Optional[Dict]:
        return self._load(self._users).get(user_id)

    def put_user(self, user: Dict) -> None:
        users = self._load(self._users)
        users[user["id"]] = user
        self._save(self._users, users)

    def list_users(self) -> List[Dict]:
        return list(self._load(self._users).values())

    def put_session(self, token: str, user_id: str, expires_at: str) -> None:
        s = self._load(self._sessions)
        s[token] = {"user_id": user_id, "expires_at": expires_at}
        self._save(self._sessions, s)

    def get_session(self, token: str) -> Optional[Dict]:
        return self._load(self._sessions).get(token)

    def delete_session(self, token: str) -> None:
        s = self._load(self._sessions)
        s.pop(token, None)
        self._save(self._sessions, s)


class SQLiteAccountsStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = os.path.abspath(db_path or os.environ.get("DEALLENS_DB") or
                                       os.path.join(default_root(), "accounts.db"))
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, "
                      "data TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id TEXT, "
                      "expires_at TEXT)")

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        with self._conn() as c:
            row = c.execute("SELECT data FROM users WHERE lower(email)=lower(?)", (email,)).fetchone()
        return json.loads(row["data"]) if row else None

    def get_user(self, user_id: str) -> Optional[Dict]:
        with self._conn() as c:
            row = c.execute("SELECT data FROM users WHERE id=?", (user_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def put_user(self, user: Dict) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO users (id, email, data) VALUES (?,?,?) "
                      "ON CONFLICT(id) DO UPDATE SET email=excluded.email, data=excluded.data",
                      (user["id"], user["email"], json.dumps(user)))

    def list_users(self) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("SELECT data FROM users").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def put_session(self, token: str, user_id: str, expires_at: str) -> None:
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO sessions (token, user_id, expires_at) VALUES (?,?,?)",
                      (token, user_id, expires_at))

    def get_session(self, token: str) -> Optional[Dict]:
        with self._conn() as c:
            row = c.execute("SELECT user_id, expires_at FROM sessions WHERE token=?", (token,)).fetchone()
        return {"user_id": row["user_id"], "expires_at": row["expires_at"]} if row else None

    def delete_session(self, token: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM sessions WHERE token=?", (token,))


def get_accounts_store(root: Optional[str] = None):
    if root:
        return JSONAccountsStore(root)
    if os.environ.get("DEALLENS_DB"):
        return SQLiteAccountsStore(os.environ["DEALLENS_DB"])
    return JSONAccountsStore(default_root())
