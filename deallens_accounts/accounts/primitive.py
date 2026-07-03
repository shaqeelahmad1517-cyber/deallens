"""Embeddable primitive interface for DealLens accounts.

Actions: signup, login, logout, verify, find_user. Stateful (persists users and
sessions) and security-sensitive — passwords are hashed, never returned.
"""
from __future__ import annotations

from typing import Any, Dict

from . import engine
from .store import get_accounts_store

ENGINE_NAME = engine.ENGINE_NAME
ENGINE_VERSION = engine.ENGINE_VERSION

_ACTIONS = ("signup", "login", "logout", "verify", "find_user")

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "stateful_primitive",
    "summary": "User accounts and sessions: signup/login/logout/verify with "
               "PBKDF2 password hashing and opaque session tokens (stdlib only).",
    "deterministic": False,
    "side_effects": True,
    "uses_llm": False,
    "entrypoint": "accounts.primitive:invoke",
    "actions": list(_ACTIONS),
    "security": {"password_hash": "pbkdf2_hmac_sha256_200k", "salt": "per_user_16b",
                 "session": "opaque_token_30d"},
    "capabilities": ["signup", "login", "session_verification", "user_lookup"],
}


def _store(payload: Dict[str, Any]):
    return get_accounts_store(payload.get("store_root"))


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch an accounts action. Never raises; returns an envelope."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        action = payload.get("action")
        if action not in _ACTIONS:
            raise ValueError(f"unknown action {action!r}; use one of {list(_ACTIONS)}")
        store = _store(payload)
        if action == "signup":
            return {"ok": True, "result": engine.signup(
                store, payload.get("email", ""), payload.get("password", ""), payload.get("name", ""))}
        if action == "login":
            return {"ok": True, "result": engine.login(
                store, payload.get("email", ""), payload.get("password", ""))}
        if action == "logout":
            return {"ok": True, "result": engine.logout(store, payload.get("token", ""))}
        if action == "verify":
            user = engine.verify(store, payload.get("token", ""))
            return {"ok": True, "result": {"user": user, "valid": user is not None}}
        if action == "find_user":
            return {"ok": True, "result": {"user": engine.find_user_by_email(store, payload.get("email", ""))}}
        raise ValueError(f"unhandled action {action!r}")
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
