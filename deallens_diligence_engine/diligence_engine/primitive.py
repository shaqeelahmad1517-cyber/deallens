"""Embeddable primitive interface for the DealLens diligence engine.

    from diligence_engine.primitive import MANIFEST, invoke
    envelope = invoke(payload_dict)      # JSON in -> JSON out, never raises

Same contract as the valuation primitive: pure, deterministic, returns an
{"ok": ...} envelope. Its ``red_flags`` output plugs straight into the
valuation engine's ``risk_flags`` input.
"""
from __future__ import annotations

from typing import Any, Dict

from .engine import ENGINE_NAME, ENGINE_VERSION, run, to_valuation_risk_flags
from .models import Checklist
from .templates import available_templates

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensDiligenceInput",
    "type": "object",
    "properties": {
        "target_name": {"type": "string"},
        "business_type": {"enum": ["general", "smb", "saas", "retail"]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "status": {"enum": ["not_started", "in_progress", "complete", "flagged", "na"]},
                    "risk_rating": {"enum": ["none", "low", "medium", "high"]},
                    "notes": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "signals": {
            "type": "object",
            "description": "Structured facts that drive automatic red-flag detection",
            "properties": {
                "top_customer_pct": {"type": "number"},
                "top_supplier_pct": {"type": "number"},
                "owner_dependent": {"type": "boolean"},
                "management_team_in_place": {"type": "boolean"},
                "revenue_trend": {"enum": ["growing", "flat", "declining"]},
                "margin_trend": {"enum": ["improving", "flat", "declining"]},
                "clean_books": {"type": "boolean"},
                "customer_retention_pct": {"type": "number"},
                "litigation_pending": {"type": "boolean"},
                "contracts_assignable": {"type": "boolean"},
                "lease_assignable": {"type": "boolean"},
                "taxes_current": {"type": "boolean"},
            },
        },
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensDiligenceEnvelope",
    "type": "object",
    "required": ["ok"],
    "properties": {
        "ok": {"type": "boolean"},
        "result": {"type": "object"},
        "error": {"type": "object"},
    },
}

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "primitive",
    "summary": "Structured due-diligence checklist engine: templates by business "
               "type, completion + risk roll-up, and automatic red-flag detection.",
    "deterministic": True,
    "side_effects": False,
    "entrypoint": "diligence_engine.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "business_types": available_templates(),
    "capabilities": [
        "checklist_templates",
        "completion_tracking",
        "risk_rollup",
        "red_flag_detection",
        "valuation_flag_adapter",
    ],
    "interlocks_with": {
        "primitive": "deallens.valuation",
        "via": "result.red_flags -> valuation input.risk_flags",
    },
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run the diligence engine. Never raises; returns an envelope."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        checklist = Checklist.from_dict(payload)
        result = run(checklist)
        # Convenience: include the valuation-ready flags inline.
        result["valuation_risk_flags"] = to_valuation_risk_flags(result)
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
