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


_SCALE = {"units": 1.0, "unit": 1.0, "dollars": 1.0, "actual": 1.0,
          "thousands": 1e3, "thousand": 1e3,
          "millions": 1e6, "million": 1e6, "mn": 1e6,
          "billions": 1e9, "billion": 1e9, "bn": 1e9}
_IMPLAUSIBLE = 1e13  # > $10 trillion for a single figure => almost certainly a units error


def _scale_factor(raw_scale: Any) -> float:
    """Map the model's reported unit to a multiplier (default: units)."""
    if isinstance(raw_scale, str):
        return _SCALE.get(raw_scale.strip().lower(), 1.0)
    return 1.0


def _clean_financials(raw: Any, factor: float = 1.0) -> Dict[str, float]:
    """Clean + apply the reporting-scale multiplier deterministically.

    The model returns figures AS PRINTED; we scale here so the LLM never has to
    do (error-prone) arithmetic like 20,094.2 x 1,000,000.
    """
    out: Dict[str, float] = {}
    if isinstance(raw, dict):
        for f in _FIN_FIELDS:
            v = raw.get(f)
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                out[f] = float(v) * factor
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
    # Keyword-fallback financials come pre-scaled by the documents extractor;
    # only the LLM path returns raw figures + a reporting_scale to apply here.
    warnings = list(warnings)
    factor = _scale_factor(data.get("reporting_scale")) if source == "llm" else 1.0
    raw = _clean_financials(data.get("financials"), 1.0)   # figures exactly as returned
    scaled = {k: v * factor for k, v in raw.items()}

    # Robustness: the model is asked to return figures "as printed" plus a unit,
    # but it sometimes returns already-absolute dollars while STILL reporting a
    # scale — which would double-multiply into nonsense (the "quadrillion" bug).
    # No single company's revenue/assets exceed a few trillion, so if scaling
    # blows past that ceiling while the unscaled figures are sane, the model must
    # have already given absolute dollars — so we DROP the scale.
    def _peak(d):
        return max((abs(v) for v in d.values()), default=0.0)

    if source == "llm" and factor != 1.0 and _peak(scaled) > _IMPLAUSIBLE and _peak(raw) <= _IMPLAUSIBLE:
        financials = raw
        warnings.append(f"Ignored a reported scale of x{int(factor):,}: the figures "
                        f"already look like absolute dollars (auto-corrected to avoid "
                        f"over-scaling).")
    else:
        financials = scaled
        if source == "llm" and factor != 1.0:
            warnings.append(f"Figures read as '{data.get('reporting_scale')}' — scaled "
                            f"by {int(factor):,}. Verify against the statement header.")

    bad = [k for k, v in financials.items() if abs(v) > _IMPLAUSIBLE]
    if bad:
        warnings.append("Some figures still look implausibly large (" + ", ".join(bad) +
                        ") — check the statement's units before trusting the valuation.")

    def _str_or_none(v):
        return v.strip() if isinstance(v, str) and v.strip() else None

    return {
        "company_name": _str_or_none(data.get("company_name")),
        "sector": _str_or_none(data.get("sector")).lower() if _str_or_none(data.get("sector")) else None,
        "financials": financials,
        "reporting_scale": data.get("reporting_scale") if source == "llm" else None,
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
