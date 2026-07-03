"""Embeddable primitive interface for the DealLens workspace.

    from workspace.primitive import MANIFEST, invoke
    invoke({"action": "create", "deal": {"target_name": "Acme"}})
    invoke({"action": "evaluate", "id": "acme-1234abcd"})
    invoke({"action": "list"})

Unlike the analytical primitives, the workspace is STATEFUL: it persists deals
to a store (JSON files by default). ``invoke`` dispatches on ``action`` and
returns the usual {"ok": ...} envelope.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import engine
from .store import get_store

ENGINE_NAME = engine.ENGINE_NAME
ENGINE_VERSION = engine.ENGINE_VERSION

_ACTIONS = ("create", "get", "list", "update", "delete", "evaluate", "report",
            "share", "unshare", "comment")

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensWorkspaceInput",
    "type": "object",
    "required": ["action"],
    "properties": {
        "action": {"enum": list(_ACTIONS)},
        "id": {"type": "string", "description": "deal id (get/update/delete/evaluate/report)"},
        "deal": {"type": "object", "description": "deal fields (create/update)"},
        "format": {"enum": ["html", "markdown", "md", "docx"], "description": "report action"},
        "out_dir": {"type": "string", "description": "report output directory"},
        "options": {"type": "object", "description": "report options (as_of, prepared_by)"},
        "store_root": {"type": "string", "description": "override the data directory"},
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensWorkspaceEnvelope",
    "type": "object",
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}, "result": {"type": "object"}, "error": {"type": "object"}},
}

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "stateful_primitive",
    "summary": "Persistent deal workspace: create/list/update deals and run "
               "evaluation + report by composing the DealLens primitives.",
    "deterministic": False,
    "side_effects": True,
    "persistence": "json_file_store",
    "entrypoint": "workspace.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "actions": list(_ACTIONS),
    "composes": ["deallens.orchestrator", "deallens.report"],
    "capabilities": ["deal_persistence", "lifecycle_stages", "evaluate", "report", "history_log"],
}


def _store(payload: Dict[str, Any]):
    # Explicit store_root -> JSON (test isolation); else DEALLENS_DB -> SQLite; else JSON default.
    return get_store(payload.get("store_root"))


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a workspace action. Never raises; returns an envelope."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        action = payload.get("action")
        if action not in _ACTIONS:
            raise ValueError(f"unknown action {action!r}; use one of {list(_ACTIONS)}")
        store = _store(payload)
        uid = payload.get("user_id")   # set by the authenticated gateway; None locally

        if action == "create":
            return {"ok": True, "result": engine.create(store, payload.get("deal", {}), user_id=uid)}
        if action == "list":
            return {"ok": True, "result": {"deals": engine.list_deals(store, user_id=uid)}}

        # actions below require an id
        deal_id = payload.get("id")
        if not deal_id:
            raise ValueError(f"action {action!r} requires 'id'")
        if action == "get":
            return {"ok": True, "result": engine.get(store, deal_id, user_id=uid)}
        if action == "update":
            return {"ok": True, "result": engine.update(store, deal_id, payload.get("deal", {}), user_id=uid)}
        if action == "delete":
            return {"ok": True, "result": engine.delete(store, deal_id, user_id=uid)}
        if action == "evaluate":
            return {"ok": True, "result": engine.evaluate(store, deal_id, user_id=uid)}
        if action == "report":
            return {"ok": True, "result": engine.report(
                store, deal_id, payload.get("format", "html"),
                payload.get("out_dir"), payload.get("options"), user_id=uid)}
        if action == "share":
            return {"ok": True, "result": engine.share(
                store, deal_id, payload.get("target_user_id", ""), payload.get("target_email", ""),
                payload.get("role", "viewer"), user_id=uid)}
        if action == "unshare":
            return {"ok": True, "result": engine.unshare(
                store, deal_id, payload.get("target_user_id", ""), user_id=uid)}
        if action == "comment":
            return {"ok": True, "result": engine.comment(
                store, deal_id, payload.get("text", ""), user_id=uid, author=payload.get("author", ""))}
        raise ValueError(f"unhandled action {action!r}")
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
