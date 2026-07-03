"""Embeddable primitive interface for DealLens accounting integrations.

Actions: list, connect, callback, import, disconnect. Stateful (stores tokens),
security-sensitive (OAuth). Transport is injectable for tests.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from . import engine
from .oauth import urllib_transport
from .store import get_connection_store

ENGINE_NAME = engine.ENGINE_NAME
ENGINE_VERSION = engine.ENGINE_VERSION

_ACTIONS = ("list", "connect", "callback", "import", "disconnect")

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "stateful_primitive",
    "summary": "Accounting integrations (QuickBooks, Xero): OAuth connect and "
               "import of financials into a deal. Mock provider for local demos.",
    "deterministic": False,
    "side_effects": True,
    "entrypoint": "integrations.primitive:invoke",
    "actions": list(_ACTIONS),
    "providers": ["quickbooks", "xero", "mock"],
    "config_env": ["QB_CLIENT_ID", "QB_CLIENT_SECRET", "XERO_CLIENT_ID",
                   "XERO_CLIENT_SECRET", "DEALLENS_BASE_URL"],
    "feeds": ["deallens.workspace", "deallens.valuation"],
}


def _store(payload: Dict[str, Any]):
    return get_connection_store(payload.get("store_root"))


def invoke(payload: Dict[str, Any], transport: Callable = urllib_transport) -> Dict[str, Any]:
    """Dispatch an integrations action. Never raises; returns an envelope."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        action = payload.get("action")
        if action not in _ACTIONS:
            raise ValueError(f"unknown action {action!r}; use one of {list(_ACTIONS)}")
        store = _store(payload)
        uid = payload.get("user_id")
        base_url = payload.get("base_url")

        if action == "list":
            return {"ok": True, "result": engine.list_providers(store, uid)}
        provider = payload.get("provider")
        if not provider:
            raise ValueError(f"action {action!r} requires 'provider'")
        if action == "connect":
            return {"ok": True, "result": engine.start_connect(store, uid, provider, base_url)}
        if action == "callback":
            return {"ok": True, "result": engine.handle_callback(
                store, provider, payload.get("code", ""), payload.get("state", ""),
                payload.get("realm_id", ""), base_url, transport)}
        if action == "import":
            return {"ok": True, "result": engine.import_financials(store, uid, provider, transport)}
        if action == "disconnect":
            return {"ok": True, "result": engine.disconnect(store, uid, provider)}
        raise ValueError(f"unhandled action {action!r}")
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
