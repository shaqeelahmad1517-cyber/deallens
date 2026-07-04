"""Embeddable primitive interface for DealLens banking valuation."""
from __future__ import annotations

from typing import Any, Dict

from .engine import BANK_TYPES, ENGINE_NAME, ENGINE_VERSION, value_bank

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensBankingInput",
    "type": "object",
    "properties": {
        "bank_type": {"type": "string", "description": "universal_bank | regional_bank | investment_bank | insurance | general_financial (or alias)"},
        "net_income": {"type": ["number", "null"]},
        "book_value": {"type": ["number", "null"], "description": "Shareholders' equity; else derived from assets - liabilities"},
        "total_assets": {"type": ["number", "null"]},
        "total_liabilities": {"type": ["number", "null"]},
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensBankingEnvelope",
    "type": "object",
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}, "result": {"type": "object"}, "error": {"type": "object"}},
}

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "primitive",
    "summary": "Bank / financial-institution valuation on price-to-book and "
               "price-to-earnings (NOT EBITDA) — the correct method for banks.",
    "deterministic": True,
    "side_effects": False,
    "entrypoint": "banking.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "bank_types": list(BANK_TYPES.keys()),
    "capabilities": ["price_to_book", "price_to_earnings", "roe"],
    "note": "Distinct methodology because interest is a bank's revenue, not a cost.",
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Value a financial institution. Never raises; returns an envelope."""
    try:
        return {"ok": True, "result": value_bank(payload)}
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
