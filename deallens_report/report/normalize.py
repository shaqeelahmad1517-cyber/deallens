"""Normalize either an orchestrator result or a bare valuation result.

The report renderer accepts both shapes so it can sit at the end of the spine
(orchestrator output) or be used on a standalone valuation run.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get_valuation(result: Dict[str, Any]) -> Dict[str, Any]:
    if "valuation" in result and isinstance(result["valuation"], dict):
        return result["valuation"]
    if "recommended_range" in result and "approaches" in result:
        return result
    raise ValueError("input is neither an orchestrator result nor a valuation result")


def extract(result: Dict[str, Any]) -> Dict[str, Any]:
    """Pull a flat, render-ready view out of either result shape."""
    if not isinstance(result, dict):
        raise TypeError("result must be a dict")

    val = _get_valuation(result)
    is_orch = "valuation" in result

    rec_range = (
        result.get("recommendation", {}).get("range")
        if is_orch else None
    ) or val.get("recommended_range")
    if not rec_range:
        raise ValueError("could not locate a recommended range in the result")

    approaches = val.get("approaches", {})
    norm = val.get("normalization", {})
    risk = val.get("risk", {})

    # Diligence + comparables only present on orchestrator results.
    diligence = result.get("diligence") if is_orch else None
    comparables = result.get("comparables") if is_orch else None
    cost_of_capital = (result.get("assumptions") or {}).get("cost_of_capital") if is_orch else None

    red_flags: List[Dict[str, Any]] = []
    completion: Optional[float] = None
    overall_risk: Optional[str] = None
    if diligence:
        red_flags = diligence.get("red_flags", [])
        completion = diligence.get("completion_pct")
        overall_risk = diligence.get("summary", {}).get("overall_risk_level")
    else:
        # fall back to the valuation's own embedded risk flags, if any
        red_flags = [
            {"label": f.get("label"), "severity": f.get("severity"), "category": f.get("category")}
            for f in risk.get("flags", [])
        ]

    return {
        "target_name": val.get("target_name") or result.get("target_name") or "Target Company",
        "recommended_range": rec_range,
        "normalization": norm,
        "effective_discount_rate": val.get("effective_discount_rate"),
        "base_free_cash_flow": val.get("base_free_cash_flow"),
        "risk": risk,
        "approaches": approaches,
        "triangulation": val.get("triangulation", {}),
        "sensitivity": val.get("sensitivity", {}),
        "diligence": {
            "completion_pct": completion,
            "overall_risk_level": overall_risk,
            "risk_profile": (diligence or {}).get("risk_profile", []),
            "ai_findings": (diligence or {}).get("ai_findings", []),
        },
        "red_flags": red_flags,
        "comparables": comparables,
        "cost_of_capital": cost_of_capital,
        "disclaimer": val.get("disclaimer") or result.get("disclaimer", ""),
    }
