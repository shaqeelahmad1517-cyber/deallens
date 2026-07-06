"""Document-understanding engine: any document text -> structured financials +
diligence findings.

Uses an LLM when one is configured; otherwise (or if the call fails) falls back to
a deterministic keyword scan so an upload always yields *something*. The LLM
transport is injectable so the whole path is testable without a network or key.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from . import _deps  # noqa: F401  (side effect: `documents` on path)
from . import keywords, llm

ENGINE_NAME = "deallens.understanding"
ENGINE_VERSION = "1.0.0"

_FIN_FIELDS = ("revenue", "net_income", "interest", "taxes", "depreciation",
               "amortization", "owner_compensation", "total_assets", "total_liabilities")
_SIGNAL_FIELDS = ("top_customer_pct", "owner_dependent", "revenue_trend",
                  "clean_books", "litigation_pending", "contracts_assignable", "taxes_current")

_DISCLAIMER = (
    "AI/keyword-assisted reading — every figure and finding is a suggestion to "
    "confirm against the source document, not a verified fact."
)


def _get_text(payload: Dict[str, Any]) -> str:
    """Resolve document text from {text} or a file {path}."""
    text = payload.get("text")
    if text:
        return str(text)
    path = payload.get("path")
    if path:
        import documents  # sibling
        kind, data = documents.readers.read_file(path)
        if kind == "text":
            return data
        # rows -> flatten to lines so the model/scanner see labels + values
        return "\n".join("\t".join(str(c) for c in row) for row in data)
    raise ValueError("provide 'text' or 'path'")


def _clean_financials(raw: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if isinstance(raw, dict):
        for f in _FIN_FIELDS:
            v = raw.get(f)
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                out[f] = float(v)
    return out


def _clean_signals(raw: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(raw, dict):
        for f in _SIGNAL_FIELDS:
            if f in raw and raw[f] is not None:
                out[f] = raw[f]
    return out


def _clean_findings(raw: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            finding = str(item.get("finding") or item.get("label") or "").strip()
            if not finding:
                continue
            sev = str(item.get("severity", "medium")).lower()
            if sev not in ("low", "medium", "high"):
                sev = "medium"
            out.append({
                "category": str(item.get("category", "General")).strip() or "General",
                "finding": finding,
                "severity": sev,
            })
    return out


def _shape(data: Dict[str, Any], source: str, warnings: List[str]) -> Dict[str, Any]:
    return {
        "financials": _clean_financials(data.get("financials")),
        "signals": _clean_signals(data.get("signals")),
        "findings": _clean_findings(data.get("findings")),
        "source": source,           # "llm" | "keywords" | "keywords_fallback"
        "model": llm.model_name() if source == "llm" else None,
        "warnings": warnings,
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "disclaimer": _DISCLAIMER,
    }


def understand(payload: Dict[str, Any],
               transport: Optional[Callable[[str], Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Read a document. `transport` (tests) forces the LLM path with a stub.

    Selection: an explicit transport, or a configured LLM, uses the model; on any
    model error it degrades to the keyword scan. With neither, it scans directly.
    """
    text = _get_text(payload)
    if not text or not text.strip():
        raise ValueError("no readable text in document")

    use_llm = transport is not None or llm.available()
    if use_llm:
        call = transport or llm.real_transport
        try:
            data = call(llm.build_prompt(text))
            if not isinstance(data, dict):
                raise ValueError("model did not return a JSON object")
            return _shape(data, "llm", [])
        except Exception as exc:
            warn = f"LLM call failed ({type(exc).__name__}); used keyword fallback."
            return _shape(keywords.scan(text), "keywords_fallback", [warn])

    warn = ("No LLM configured — used a keyword scan. Set an API key for full "
            "document understanding.")
    return _shape(keywords.scan(text), "keywords", [warn])
