"""Embeddable primitive interface for the DealLens report renderer.

    from report.primitive import MANIFEST, invoke
    envelope = invoke({"result": <orchestrator_or_valuation_result>, "format": "html"})
    document_string = envelope["result"]["content"]

Rendering is pure (returns the document as a string), so invoke has no side
effects. Writing files (.html/.md/.docx) is done at the edge via the CLI or the
``docx_writer`` helper.
"""
from __future__ import annotations

from typing import Any, Dict

from . import docx_writer
from .render import build_html, build_markdown, render

ENGINE_NAME = "deallens.report"
ENGINE_VERSION = "1.0.0"

INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensReportInput",
    "type": "object",
    "required": ["result"],
    "properties": {
        "result": {"type": "object", "description": "An orchestrator or valuation result"},
        "format": {"enum": ["html", "markdown", "md"], "default": "html"},
        "options": {
            "type": "object",
            "properties": {
                "as_of": {"type": "string"},
                "prepared_by": {"type": "string"},
            },
        },
    },
}

OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DealLensReportEnvelope",
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
    "summary": "Renders an orchestrator/valuation result into a client-ready "
               "report (HTML or Markdown string; optional Word .docx via helper).",
    "deterministic": True,
    "side_effects": False,
    "entrypoint": "report.primitive:invoke",
    "input_schema": INPUT_SCHEMA,
    "output_schema": OUTPUT_SCHEMA,
    "formats": ["html", "markdown"],
    "optional_formats": {"docx": "requires python-docx"},
    "docx_available": docx_writer.available(),
    "capabilities": ["html_report", "markdown_report", "docx_report", "result_shape_normalization"],
    "consumes": ["deallens.orchestrator", "deallens.valuation"],
}


def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render a report. Never raises; returns an envelope with the document string."""
    try:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a JSON object (dict)")
        if "result" not in payload:
            raise ValueError("payload must include a 'result' (orchestrator or valuation result)")
        fmt = payload.get("format", "html")
        content = render(payload["result"], fmt=fmt, options=payload.get("options"))
        return {"ok": True, "result": {"format": fmt, "content": content, "length": len(content)}}
    except Exception as exc:
        return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}


def manifest() -> Dict[str, Any]:
    return MANIFEST
