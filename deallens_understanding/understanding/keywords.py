"""Keyword fallback: understand a document with no LLM.

Deterministic, zero-dependency. Scans plain text for known risk phrases and reuses
the `documents` extractor for financial figures. Deliberately crude — it exists so
an upload still produces *something* when no API key is configured (or the LLM call
fails), not to replace real comprehension.
"""
from __future__ import annotations

from typing import Any, Dict, List

# (phrases, category, finding text, severity, optional signal to set True)
_RULES = [
    (["going concern", "substantial doubt"], "Financial",
     "'Going concern' / substantial-doubt language present — investigate solvency.",
     "high", ("clean_books", False)),
    (["material weakness", "significant deficiency"], "Financial",
     "Material weakness in internal controls mentioned — books may be unreliable.",
     "high", ("clean_books", False)),
    (["lawsuit", "litigation", "legal proceeding", "pending claim", "arbitration"],
     "Legal", "Litigation or legal-proceeding language present — verify exposure.",
     "medium", ("litigation_pending", True)),
    (["customer concentration", "one customer", "single customer", "largest customer",
      "significant customer", "one client", "major customer"], "Customers",
     "Customer-concentration language present — confirm the top-customer percentage.",
     "medium", None),
    (["single supplier", "sole supplier", "one supplier", "sole source",
      "single source", "key supplier"], "Suppliers",
     "Supplier-concentration language present — confirm sourcing alternatives.",
     "medium", None),
    (["key person", "key employee", "founder", "reliant on the owner",
      "dependent on the owner", "owner-operator"], "People",
     "Key-person / owner dependence language present — verify transferability.",
     "medium", ("owner_dependent", True)),
    (["related party", "related-party", "affiliate transaction"], "Governance",
     "Related-party transactions mentioned — verify they are arm's-length.",
     "medium", None),
    (["covenant", "default", "breach of covenant"], "Debt",
     "Debt-covenant language present — check covenant headroom and defaults.",
     "medium", None),
    (["restructuring", "impairment", "write-down", "write off", "goodwill impairment"],
     "Financial", "Restructuring / impairment charges mentioned — verify recurrence.",
     "low", None),
    (["decline", "decreased", "lower than", "fell"], "Financial",
     "Possible declining-performance language — confirm the revenue/margin trend.",
     "low", None),
]


def scan(text: str) -> Dict[str, Any]:
    low = (text or "").lower()
    signals: Dict[str, Any] = {}
    findings: List[Dict[str, Any]] = []
    for phrases, category, finding, severity, signal in _RULES:
        if any(p in low for p in phrases):
            findings.append({"category": category, "finding": finding, "severity": severity})
            if signal:
                signals.setdefault(signal[0], signal[1])

    financials: Dict[str, Any] = {}
    try:
        import documents  # sibling; on path via _deps
        financials = documents.extract_from_text(text).get("financials", {}) or {}
    except Exception:
        financials = {}

    return {"financials": financials, "signals": signals, "findings": findings}
