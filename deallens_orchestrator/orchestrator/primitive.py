"""Embeddable primitive interface for the DealLens orchestrator.

    from orchestrator.primitive import MANIFEST, invoke
    envelope = invoke(payload_dict)      # one call -> full deal evaluation

Chains diligence + comparables + valuation behind a single, stable envelope.
"""
from __future__ import annotations

from typing import Any, Dict

from .engine import ENGINE_NAME, ENGINE_VERSION, run

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensOrchestratorInput",
    "type": "object",
    "properties": {
        "target_name": {"type": "string"},
        "financials": {"type": "object", "description": "Valuation financials block"},
        "adjustments": {"type": "array", "items": {"type": "object"}},
        "checklist": {"type": "object", "description": "Diligence input (business_type, items, signals)"},
        "comparables": {"type": "object", "description": "Comparables query (sector, metric, ...)"},
        "market": {"type": "object", "description": "Explicit market block; used if comparables omitted/fails"},
        "income": {"type": "object"},
        "weights": {"type": "object"},
        "enabled_approaches": {"type": "array", "items": {"type": "string"}},
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensOrchestratorEnvelope",
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
    "kind": "orchestrator",
    "summary": "Single-call deal evaluation: chains diligence -> comparables -> "
               "valuation and returns a unified result with recommendation.",
    "deterministic": True,
    "side_effects": False,
    "entrypoint": "orchestrator.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "composes": ["deallens.diligence", "deallens.comparables", "deallens.valuation"],
    "capabilities": [
        "pipeline_orchestration",
        "graceful_degradation",
        "size_growth_auto_derivation",
        "unified_recommendation",
    ],
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full pipeline. Never raises; returns an envelope."""
    try:
        return {"ok": True, "result": run(payload)}
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
