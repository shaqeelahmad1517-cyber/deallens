"""Embeddable primitive interface for DealLens sum-of-the-parts valuation."""
from __future__ import annotations

from typing import Any, Dict

from .engine import ENGINE_NAME, ENGINE_VERSION, value_sotp

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensSOTPInput",
    "type": "object",
    "required": ["segments"],
    "properties": {
        "mode": {"enum": ["multiple", "deep"],
                 "description": "multiple = 1 comp per segment; deep = full valuation engine per segment (needs per-segment 'financials')"},
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "sector", "earnings"],
                "properties": {
                    "name": {"type": "string"},
                    "sector": {"type": "string"},
                    "metric": {"enum": ["sde", "ebitda", "revenue"]},
                    "tier": {"enum": ["smb", "public"]},
                    "growth": {"enum": ["", "high", "growing", "flat", "declining"]},
                    "earnings": {"type": "number"},
                },
            },
        },
        "net_debt": {"type": "number", "description": "Debt minus cash (subtracted from EV)"},
        "conglomerate_discount": {"type": "number", "description": "0..1 holdco discount"},
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensSOTPEnvelope",
    "type": "object",
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}, "result": {"type": "object"}, "error": {"type": "object"}},
}

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "primitive",
    "summary": "Sum-of-the-parts valuation for conglomerates: value each segment "
               "on its own sector comp, sum, apply holdco discount and net debt.",
    "deterministic": True,
    "side_effects": False,
    "entrypoint": "sotp.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "capabilities": ["per_segment_valuation", "conglomerate_discount", "net_debt_bridge"],
    "consumes": ["deallens.comparables"],
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run a sum-of-the-parts valuation. Never raises; returns an envelope."""
    try:
        return {"ok": True, "result": value_sotp(payload)}
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
