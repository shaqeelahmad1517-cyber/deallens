"""Accounts engine: signup, login, session verification — stdlib crypto only.

Passwords are hashed with PBKDF2-HMAC-SHA256 (200k iterations, per-user salt).
Sessions are opaque random tokens with an expiry. No third-party auth library.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import os
import re
import secrets
import uuid
from typing import Any, Dict, Optional

from .store import get_accounts_store

ENGINE_NAME = "deallens.accounts"
ENGINE_VERSION = "1.0.0"

_PBKDF2_ROUNDS = 200_000
_SESSION_DAYS = 30
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS).hex()


def _public(user: Dict[str, Any]) -> Dict[str, Any]:
    """User record safe to return — never the hash or salt."""
    return {"id": user["id"], "email": user["email"], "name": user.get("name", ""),
            "created_at": user.get("created_at", "")}


def signup(store, email: str, password: str, name: str = "") -> Dict[str, Any]:
    email = (email or "").strip()
    if not _EMAIL_RE.match(email):
        raise ValueError("a valid email is required")
    if not password or len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    if store.get_user_by_email(email):
        raise ValueError("an account with that email already exists")
    salt = secrets.token_bytes(16)
    user = {
        "id": f"u-{uuid.uuid4().hex[:12]}",
        "email": email,
        "name": name.strip(),
        "salt": salt.hex(),
        "pw_hash": _hash_password(password, salt),
        "created_at": _now().isoformat(timespec="seconds"),
    }
    store.put_user(user)
    return _public(user)


def _issue_session(store, user_id: str) -> Dict[str, Any]:
    token = secrets.token_urlsafe(32)
    expires = (_now() + datetime.timedelta(days=_SESSION_DAYS)).isoformat(timespec="seconds")
    store.put_session(token, user_id, expires)
    return {"token": token, "expires_at": expires}


def login(store, email: str, password: str) -> Dict[str, Any]:
    user = store.get_user_by_email((email or "").strip())
    # Constant-ish work whether or not the user exists (avoid trivial timing oracle).
    salt = bytes.fromhex(user["salt"]) if user else secrets.token_bytes(16)
    candidate = _hash_password(password or "", salt)
    if not user or not hmac.compare_digest(candidate, user.get("pw_hash", "")):
        raise ValueError("invalid email or password")
    session = _issue_session(store, user["id"])
    return {"user": _public(user), **session}


def logout(store, token: str) -> Dict[str, Any]:
    if token:
        store.delete_session(token)
    return {"logged_out": True}


def verify(store, token: str) -> Optional[Dict[str, Any]]:
    """Return the public user for a valid, unexpired session token, else None."""
    if not token:
        return None
    session = store.get_session(token)
    if not session:
        return None
    try:
        if datetime.datetime.fromisoformat(session["expires_at"]) < _now():
            store.delete_session(token)
            return None
    except (ValueError, KeyError):
        return None
    user = store.get_user(session["user_id"])
    return _public(user) if user else None


def find_user_by_email(store, email: str) -> Optional[Dict[str, Any]]:
    u = store.get_user_by_email((email or "").strip())
    return _public(u) if u else None
