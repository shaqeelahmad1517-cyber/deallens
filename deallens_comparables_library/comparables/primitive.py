"""Embeddable primitive interface for the DealLens comparables library.

    from comparables.primitive import MANIFEST, invoke
    envelope = invoke(payload_dict)      # JSON in -> JSON out, never raises

Pure, deterministic, returns an {"ok": ...} envelope. Its ``valuation_market``
output plugs straight into the valuation engine's ``market`` block.
"""
from __future__ import annotations

from typing import Any, Dict

from .engine import ENGINE_NAME, ENGINE_VERSION, available_sectors, lookup, to_valuation_market
from .models import CompQuery

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensComparablesInput",
    "type": "object",
    "properties": {
        "sector": {"type": "string", "description": "Sector key or alias"},
        "metric": {"enum": ["sde", "ebitda", "revenue"]},
        "size_ebitda": {"type": ["number", "null"], "description": "EBITDA used to gauge size premium"},
        "growth": {"enum": ["high", "growing", "flat", "declining", ""]},
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensComparablesEnvelope",
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
    "summary": "Comparable-multiple library: sector multiple bands (SDE/EBITDA/"
               "revenue) with transparent size and growth adjustments.",
    "deterministic": True,
    "side_effects": False,
    "entrypoint": "comparables.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "sectors": available_sectors(),
    "capabilities": [
        "sector_multiple_lookup",
        "size_adjustment",
        "growth_adjustment",
        "valuation_market_adapter",
    ],
    "interlocks_with": {
        "primitive": "deallens.valuation",
        "via": "result.valuation_market -> valuation input.market",
    },
    "data_note": "Seed dataset is illustrative; replace with proprietary comps for live use.",
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run a comparables lookup. Never raises; returns an envelope."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        result = lookup(CompQuery.from_dict(payload))
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
