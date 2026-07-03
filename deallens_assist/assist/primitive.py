"""Embeddable primitive interface for DealLens assist.

Rule-based, deterministic helper. Actions:
  - "suggest_adjustments": flagged lines -> suggested add-backs with rationale
  - "draft_narrative":     an evaluation result -> plain-English summary

It is honest about being deterministic/template-driven, not a large language
model. The rule tables and templates are the seam where an LLM could be added.
"""
from __future__ import annotations

from typing import Any, Dict

from .adjustments import suggest_adjustments
from .narrative import draft_narrative

ENGINE_NAME = "deallens.assist"
ENGINE_VERSION = "1.0.0"

_ACTIONS = ("suggest_adjustments", "draft_narrative")

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensAssistInput",
    "type": "object",
    "required": ["action"],
    "properties": {
        "action": {"enum": list(_ACTIONS)},
        # suggest_adjustments:
        "ingestion": {"type": "object", "description": "A documents-primitive result"},
        "adjustment_candidates": {"type": "array", "items": {"type": "object"}},
        "financials": {"type": "object"},
        # draft_narrative:
        "result": {"type": "object", "description": "An orchestrator or valuation result"},
        "options": {"type": "object", "properties": {"format": {"enum": ["markdown", "md", "text"]}}},
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensAssistEnvelope",
    "type": "object",
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}, "result": {"type": "object"}, "error": {"type": "object"}},
}

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "primitive",
    "summary": "Rule-based assist: suggest normalization add-backs (with rationale) "
               "and auto-draft a plain-English valuation narrative — for human review.",
    "deterministic": True,
    "side_effects": False,
    "uses_llm": False,
    "entrypoint": "assist.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "actions": list(_ACTIONS),
    "capabilities": ["adjustment_suggestions", "narrative_drafting"],
    "consumes": ["deallens.documents", "deallens.orchestrator", "deallens.valuation"],
    "note": "Deterministic/template-driven; rule tables are the seam for an LLM.",
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run an assist action. Never raises; returns an envelope."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        action = payload.get("action")
        if action == "suggest_adjustments":
            ingestion = payload.get("ingestion") or {}
            candidates = payload.get("adjustment_candidates")
            if candidates is None:
                candidates = ingestion.get("adjustment_candidates", [])
            financials = payload.get("financials")
            if financials is None:
                financials = ingestion.get("financials", {})
            return {"ok": True, "result": suggest_adjustments(candidates, financials)}
        if action == "draft_narrative":
            if "result" not in payload:
                raise ValueError("draft_narrative requires 'result'")
            return {"ok": True, "result": draft_narrative(payload["result"], payload.get("options"))}
        raise ValueError(f"unknown action {action!r}; use one of {list(_ACTIONS)}")
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
