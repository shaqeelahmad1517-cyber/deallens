"""Embeddable primitive interface for DealLens quick-screen."""
from __future__ import annotations

from typing import Any, Dict

from .engine import ENGINE_NAME, ENGINE_VERSION, run

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensQuickScreenInput",
    "type": "object",
    "required": ["earnings", "sector"],
    "properties": {
        "earnings": {"type": "number", "description": "Metric value (e.g. SDE or EBITDA)"},
        "metric": {"enum": ["sde", "ebitda", "revenue"], "default": "sde"},
        "sector": {"type": "string"},
        "growth": {"enum": ["", "high", "growing", "flat", "declining"]},
        "size_ebitda": {"type": ["number", "null"]},
        "top_customer_pct": {"type": ["number", "null"]},
        "owner_dependent": {"type": "boolean"},
        "risk_flags": {"type": "array", "items": {"type": "object"}},
        "asking_price": {"type": ["number", "null"], "description": "Optional — triggers a go/no-go verdict"},
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensQuickScreenEnvelope",
    "type": "object",
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}, "result": {"type": "object"}, "error": {"type": "object"}},
}

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "primitive",
    "summary": "Fast indicative valuation for deal triage: earnings × sector "
               "comparable multiple, light risk haircut, optional asking-price verdict.",
    "deterministic": True,
    "side_effects": False,
    "entrypoint": "quickscreen.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "capabilities": ["indicative_valuation", "risk_haircut", "asking_price_verdict"],
    "consumes": ["deallens.comparables"],
    "note": "Triage only — run deallens.orchestrator for a full evaluation.",
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run a quick screen. Never raises; returns an envelope."""
    try:
        return {"ok": True, "result": run(payload)}
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
