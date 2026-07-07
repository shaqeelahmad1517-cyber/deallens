"""Workspace engine — stateful deal lifecycle over the stateless primitives.

Actions: create, get, list, update, delete, evaluate, report. ``evaluate`` runs
the orchestrator on the deal's stored inputs; ``report`` renders the latest
evaluation to a file. State is persisted via the store between calls.
"""
from __future__ import annotations

import datetime
import os
import uuid
from typing import Any, Dict, List, Optional

from . import _deps  # noqa: F401  (side effect: sibling engines on sys.path)
from .models import STAGES, Deal
from .store import JSONFileStore

ENGINE_NAME = "deallens.workspace"
ENGINE_VERSION = "1.0.0"

# Fields a user may set on create/update.
_INPUT_FIELDS = ("target_name", "stage", "financials", "adjustments",
                 "checklist", "comparables", "options", "notes")


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _new_id(target_name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in (target_name or "deal")).strip("-")
    slug = "-".join(filter(None, slug.split("-")))[:32] or "deal"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


def _log(deal: Deal, event: str) -> None:
    deal.history.append({"event": event, "at": _now()})


# ---------------------------------------------------------------------------
# Access control. user_id=None means "local mode" (no enforcement); a real
# user_id (passed by the authenticated gateway) enforces owner/editor/viewer.
# ---------------------------------------------------------------------------
def _role(deal: Deal, user_id: Optional[str]) -> Optional[str]:
    if user_id is None:
        return "owner"                       # local / unauthenticated CLI use
    if not deal.owner_id or deal.owner_id == user_id:
        return "owner"                       # owner (or legacy ownerless deal)
    for s in deal.shared_with:
        if s.get("user_id") == user_id:
            return s.get("role", "viewer")
    return None


def _authorize(deal: Deal, user_id: Optional[str], need: str = "view") -> str:
    role = _role(deal, user_id)
    if role is None:
        raise PermissionError("you do not have access to this deal")
    if need == "own" and role != "owner":
        raise PermissionError("only the deal owner can do that")
    if need == "edit" and role == "viewer":
        raise PermissionError("you have view-only access to this deal")
    return role


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
def create(store, data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    data = dict(data or {})
    deal_id = data.get("id") or _new_id(data.get("target_name", ""))
    if store.exists(deal_id):
        raise ValueError(f"deal already exists: {deal_id}")
    stage = data.get("stage", "sourced")
    if stage not in STAGES:
        raise ValueError(f"invalid stage {stage!r}; use one of {STAGES}")
    now = _now()
    deal = Deal(id=deal_id, created_at=now, updated_at=now)
    deal.owner_id = data.get("owner_id") or (user_id or "")
    for f in _INPUT_FIELDS:
        if f in data:
            setattr(deal, f, data[f])
    _log(deal, "created")
    store.save(deal)
    return deal.to_dict()


def get(store, deal_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    deal = store.load(deal_id)
    role = _authorize(deal, user_id, "view")
    out = deal.to_dict()
    out["my_role"] = role
    return out


def list_deals(store, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    deals = store.list()
    if user_id is None:
        return deals
    return [d for d in deals
            if not d.get("owner_id") or d.get("owner_id") == user_id
            or user_id in (d.get("shared_user_ids") or [])]


def update(store, deal_id: str, data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    deal = store.load(deal_id)
    _authorize(deal, user_id, "edit")
    data = dict(data or {})
    if "stage" in data and data["stage"] not in STAGES:
        raise ValueError(f"invalid stage {data['stage']!r}; use one of {STAGES}")
    changed = []
    for f in _INPUT_FIELDS:
        if f in data:
            setattr(deal, f, data[f])
            changed.append(f)
    deal.updated_at = _now()
    _log(deal, f"updated: {', '.join(changed)}" if changed else "updated")
    store.save(deal)
    return deal.to_dict()


def delete(store, deal_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    if store.exists(deal_id):
        _authorize(store.load(deal_id), user_id, "own")   # only owner deletes
    existed = store.exists(deal_id)
    store.delete(deal_id)
    return {"deleted": existed, "id": deal_id}


# ---------------------------------------------------------------------------
# Collaboration
# ---------------------------------------------------------------------------
def share(store, deal_id: str, target_user_id: str, target_email: str,
          role: str = "viewer", user_id: Optional[str] = None) -> Dict[str, Any]:
    if role not in ("viewer", "editor"):
        raise ValueError("role must be 'viewer' or 'editor'")
    if not target_user_id:
        raise ValueError("no such user to share with")
    deal = store.load(deal_id)
    _authorize(deal, user_id, "own")
    deal.shared_with = [s for s in deal.shared_with if s.get("user_id") != target_user_id]
    deal.shared_with.append({"user_id": target_user_id, "email": target_email, "role": role})
    deal.updated_at = _now()
    _log(deal, f"shared with {target_email} ({role})")
    store.save(deal)
    return deal.to_dict()


def unshare(store, deal_id: str, target_user_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    deal = store.load(deal_id)
    _authorize(deal, user_id, "own")
    deal.shared_with = [s for s in deal.shared_with if s.get("user_id") != target_user_id]
    deal.updated_at = _now()
    _log(deal, "unshared")
    store.save(deal)
    return deal.to_dict()


def comment(store, deal_id: str, text: str, user_id: Optional[str] = None,
            author: str = "") -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("comment text is required")
    deal = store.load(deal_id)
    _authorize(deal, user_id, "view")     # any collaborator can comment
    entry = {"id": uuid.uuid4().hex[:8], "user_id": user_id or "", "author": author,
             "text": text, "at": _now()}
    deal.comments.append(entry)
    deal.updated_at = _now()
    _log(deal, "comment added")
    store.save(deal)
    return entry


# ---------------------------------------------------------------------------
# Evaluate / report (compose the other primitives)
# ---------------------------------------------------------------------------
def _orchestrator_payload(deal: Deal) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "target_name": deal.target_name,
        "financials": deal.financials,
    }
    if deal.adjustments:
        payload["adjustments"] = deal.adjustments
    if deal.checklist:
        payload["checklist"] = deal.checklist
    if deal.comparables:
        payload["comparables"] = deal.comparables
    for k in ("income", "weights", "market", "enabled_approaches"):
        if deal.options.get(k) is not None:
            payload[k] = deal.options[k]
    return payload


def evaluate(store, deal_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    import orchestrator
    deal = store.load(deal_id)
    _authorize(deal, user_id, "edit")
    env = orchestrator.invoke(_orchestrator_payload(deal))
    if not env["ok"]:
        raise RuntimeError(f"evaluation failed: {env['error']['message']}")
    result = env["result"]
    # Carry the AI-extracted findings (kept on the checklist) into the result so
    # the report can render a comprehensive due-diligence section, not just the
    # signal-derived red flags.
    ai_findings = (deal.checklist or {}).get("ai_findings")
    if ai_findings and isinstance(result.get("diligence"), dict):
        result["diligence"]["ai_findings"] = ai_findings
    deal.last_evaluation = result
    deal.updated_at = _now()
    if deal.stage in ("sourced", "screening"):
        deal.stage = "valuation"
    _log(deal, "evaluated")
    store.save(deal)
    return env["result"]


def report(store, deal_id: str, fmt: str = "html", out_dir: Optional[str] = None,
           options: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    import report as report_pkg
    deal = store.load(deal_id)
    _authorize(deal, user_id, "edit")
    if deal.last_evaluation is None:
        evaluate(store, deal_id, user_id=None)   # already authorized above
        deal = store.load(deal_id)

    fmt = (fmt or "html").lower()
    ext = {"html": "html", "markdown": "md", "md": "md", "docx": "docx"}.get(fmt, "html")
    out_dir = out_dir or os.path.join(store.root, "reports")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{deal.id}.{ext}")

    if fmt == "docx":
        if not report_pkg.docx_available():
            raise RuntimeError("python-docx not installed; pip install python-docx")
        report_pkg.write_docx(deal.last_evaluation, path, options)
    else:
        content = report_pkg.render(deal.last_evaluation, fmt, options)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    entry = {"format": fmt, "path": path, "at": _now()}
    deal.reports.append(entry)
    deal.updated_at = _now()
    _log(deal, f"report:{fmt}")
    store.save(deal)
    return entry
