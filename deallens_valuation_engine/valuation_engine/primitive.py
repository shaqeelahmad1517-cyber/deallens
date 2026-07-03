"""Embeddable primitive interface for the DealLens valuation engine.

This is the single contract an AIOS "spine" needs:

    from valuation_engine.primitive import MANIFEST, invoke

    result = invoke(payload_dict)        # JSON-in -> JSON-out, never raises
    schema = MANIFEST["input_schema"]    # declared I/O contract

``invoke`` is pure, deterministic, and side-effect free. It always returns an
envelope of the form {"ok": bool, "result"|"error": ...} so the host can route
on a stable shape rather than catching exceptions across a process boundary.
"""
from __future__ import annotations

from typing import Any, Dict

from .engine import ENGINE_NAME, ENGINE_VERSION, run
from .models import Deal

# ---------------------------------------------------------------------------
# I/O contract (JSON Schema, draft-07 subset). Kept inline so the primitive is
# self-describing with zero external files.
# ---------------------------------------------------------------------------
INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensValuationInput",
    "type": "object",
    "properties": {
        "target_name": {"type": "string"},
        "financials": {
            "type": "object",
            "properties": {
                "revenue": {"type": "number"},
                "net_income": {"type": "number"},
                "interest": {"type": "number"},
                "taxes": {"type": "number"},
                "depreciation": {"type": "number"},
                "amortization": {"type": "number"},
                "owner_compensation": {"type": "number"},
                "total_assets": {"type": "number"},
                "total_liabilities": {"type": "number"},
                "fair_value_adjustment": {"type": "number"},
                "base_free_cash_flow": {"type": ["number", "null"]},
            },
        },
        "adjustments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label", "amount"],
                "properties": {
                    "label": {"type": "string"},
                    "amount": {"type": "number"},
                    "type": {"enum": ["add_back", "deduction"]},
                    "rationale": {"type": "string"},
                },
            },
        },
        "risk_flags": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label"],
                "properties": {
                    "label": {"type": "string"},
                    "severity": {"enum": ["low", "medium", "high"]},
                    "category": {"type": "string"},
                    "multiple_discount": {"type": ["number", "null"]},
                    "discount_rate_premium": {"type": ["number", "null"]},
                },
            },
        },
        "income": {
            "type": "object",
            "properties": {
                "discount_rate": {"type": "number"},
                "growth_rate": {"type": "number"},
                "terminal_growth": {"type": "number"},
                "projection_years": {"type": "integer", "minimum": 1},
                "long_term_growth": {"type": "number"},
                "fcf_conversion": {"type": "number"},
            },
        },
        "market": {
            "type": "object",
            "properties": {
                "metric": {"enum": ["sde", "ebitda", "revenue"]},
                "low_multiple": {"type": "number"},
                "high_multiple": {"type": "number"},
            },
        },
        "weights": {
            "type": "object",
            "properties": {
                "income": {"type": "number"},
                "market": {"type": "number"},
                "asset": {"type": "number"},
            },
        },
        "enabled_approaches": {
            "type": "array",
            "items": {"enum": ["income", "market", "asset"]},
        },
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensValuationEnvelope",
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
    "summary": "Deterministic business-valuation engine: normalization, DCF, "
               "capitalization, market multiples, NAV, risk-adjusted triangulation.",
    "deterministic": True,
    "side_effects": False,
    "entrypoint": "valuation_engine.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "capabilities": [
        "earnings_normalization",
        "discounted_cash_flow",
        "capitalization_of_earnings",
        "market_multiple",
        "net_asset_value",
        "risk_adjustment",
        "triangulation",
        "sensitivity_analysis",
    ],
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run the engine on a JSON-like dict. Never raises; returns an envelope."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        deal = Deal.from_dict(payload)
        result = run(deal)
        return {"ok": True, "result": result}
    except Exception as exc:  # deliberate catch-all: stable contract for the spine
        return {
            "ok": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }


def manifest() -> Dict[str, Any]:
    """Return the primitive manifest (for registration with the spine)."""
    return MANIFEST
