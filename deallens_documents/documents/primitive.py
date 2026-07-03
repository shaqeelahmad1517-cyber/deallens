"""Embeddable primitive interface for DealLens document ingestion."""
from __future__ import annotations

from typing import Any, Dict

from .engine import ENGINE_NAME, ENGINE_VERSION, ingest

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensDocumentsInput",
    "type": "object",
    "description": "Provide exactly one of: rows, text, csv_text, or path.",
    "properties": {
        "rows": {"type": "array", "items": {"type": "array"}},
        "text": {"type": "string", "description": "Pasted statement text"},
        "csv_text": {"type": "string", "description": "Raw CSV content"},
        "path": {"type": "string", "description": "Path to a .csv/.xlsx/.pdf/.txt file"},
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensDocumentsEnvelope",
    "type": "object",
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}, "result": {"type": "object"}, "error": {"type": "object"}},
}

MANIFEST: Dict[str, Any] = {
    "name": ENGINE_NAME,
    "version": ENGINE_VERSION,
    "kind": "primitive",
    "summary": "Extracts a financials block from a statement (CSV/Excel/PDF/text) "
               "by matching line-item labels; flags add-back candidates and gaps.",
    "deterministic": True,
    "side_effects": False,
    "entrypoint": "documents.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "formats": {"csv": "stdlib", "xlsx": "stdlib", "txt": "stdlib", "pdf": "optional (pdfplumber/pypdf)"},
    "capabilities": ["number_parsing", "line_item_matching", "adjustment_hints", "gap_warnings"],
    "feeds": ["deallens.workspace", "deallens.quickscreen", "deallens.valuation"],
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest a document. Never raises; returns an envelope."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        result = ingest(
            path=payload.get("path"),
            text=payload.get("text"),
            rows=payload.get("rows"),
            csv_text=payload.get("csv_text"),
        )
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
