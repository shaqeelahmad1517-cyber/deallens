"""Embeddable primitive interface for DealLens document understanding."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from . import llm
from .engine import ENGINE_NAME, ENGINE_VERSION, understand

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensUnderstandingInput",
    "type": "object",
    "description": "Provide 'text' (document text) or 'path' (a file to read).",
    "properties": {
        "text": {"type": "string"},
        "path": {"type": "string", "description": "Path to a .pdf/.docx/.txt/.csv/.xlsx"},
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensUnderstandingEnvelope",
    "type": "object",
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}, "result": {"type": "object"}, "error": {"type": "object"}},
}

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "primitive",
    "summary": "Reads a real-world business document (annual report, 10-K, memo) and "
               "returns structured financials plus diligence findings. Uses an LLM "
               "when configured; falls back to a deterministic keyword scan otherwise.",
    "deterministic": False,   # LLM path varies; keyword fallback is deterministic
    "side_effects": True,     # may call an external LLM API
    "uses_llm": llm.available(),
    "llm_provider": llm.provider() if llm.available() else None,
    "entrypoint": "understanding.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "capabilities": ["financial_extraction", "risk_finding_extraction",
                     "keyword_fallback", "diligence_signal_hints"],
    "feeds": ["deallens.workspace", "deallens.diligence", "deallens.valuation"],
}


def invoke(payload: Dict[str, Any],
           transport: Optional[Callable[[str], Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Understand a document. Never raises; returns an envelope."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        return {"ok": True, "result": understand(payload, transport=transport)}
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    # Recompute the live LLM flags each call (env may change at runtime).
    m = dict(MANIFEST)
    m["uses_llm"] = llm.available()
    m["llm_provider"] = llm.provider() if llm.available() else None
    return m
