"""Suggest normalization add-backs from flagged line items — for human approval.

Rule-based and transparent: each suggestion carries a plain-English rationale and
a confidence level. It proposes; the human disposes. (The rule table is the seam
where an LLM could later be substituted.)
"""
from __future__ import annotations

from typing import Any, Dict, List

# Ordered rationale rules: (keywords, rationale, confidence).
_RULES = [
    (["one-time", "one time", "one-off", "one off", "non-recurring", "nonrecurring",
      "extraordinary", "settlement", "lawsuit", "legal"],
     "Non-recurring item — add back, as it is unlikely to repeat under new ownership.",
     "high"),
    (["owner", "personal", "vehicle", "car", "travel", "entertainment", "draw", "spouse", "family"],
     "Discretionary owner-related expense — typically added back to reflect earnings "
     "available to a new owner.",
     "high"),
    (["consulting", "related party", "related-party", "above market", "above-market", "rent"],
     "Possible related-party or above-market cost — review and normalize to market terms.",
     "medium"),
    (["donation", "charity", "bonus"],
     "Potentially discretionary — confirm whether it continues post-sale.",
     "medium"),
]

_DEFAULT = ("Potential normalization item — review whether it is discretionary or non-recurring.", "low")


def _rationale(label: str):
    low = (label or "").lower()
    for keywords, rationale, confidence in _RULES:
        if any(k in low for k in keywords):
            return rationale, confidence
    return _DEFAULT


def suggest_adjustments(candidates: List[Dict[str, Any]],
                        financials: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Turn flagged candidate lines into suggested add-backs with rationale.

    ``candidates`` are typically ``adjustment_candidates`` from the documents
    primitive (each {label, amount, type}).
    """
    suggestions: List[Dict[str, Any]] = []
    seen = set()
    for c in candidates or []:
        label = c.get("label", "")
        key = label.lower().strip()
        if not label or key in seen:
            continue
        seen.add(key)
        amount = c.get("amount")
        rationale, confidence = _rationale(label)
        suggestions.append({
            "label": label,
            "amount": amount,
            "type": "add_back",
            "rationale": rationale,
            "confidence": confidence,
            "status": "suggested",          # requires human approval
            "source": c.get("source", "document"),
        })

    notes: List[str] = []
    fin = financials or {}
    if fin.get("owner_compensation"):
        notes.append(
            f"Owner compensation of {fin['owner_compensation']:,.0f} is added back in SDE. "
            "If valuing on EBITDA, deduct a market-rate replacement salary instead."
        )
    if "depreciation" in fin and "amortization" not in fin:
        notes.append("Amortization not found — confirm whether it should be separated from depreciation.")

    return {
        "suggestions": suggestions,
        "notes": notes,
        "count": len(suggestions),
        "disclaimer": "Suggestions for review only — approve, edit, or reject each before use.",
    }
