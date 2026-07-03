"""Draft a plain-English narrative summary of an evaluation result.

Deterministic and template-driven (no LLM): given the structured numbers it
composes readable prose. Accepts an orchestrator result or a bare valuation
result. The template is the seam where an LLM could later be substituted.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _money(n: Optional[float]) -> str:
    try:
        return f"${float(n):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _view(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        raise TypeError("result must be a dict")
    if "valuation" in result and isinstance(result["valuation"], dict):
        val, is_orch = result["valuation"], True
    elif "recommended_range" in result and "approaches" in result:
        val, is_orch = result, False
    else:
        raise ValueError("input is neither an orchestrator nor a valuation result")

    rr = (result.get("recommendation", {}) or {}).get("range") if is_orch else None
    rr = rr or val.get("recommended_range")
    diligence = result.get("diligence") if is_orch else None
    comparables = result.get("comparables") if is_orch else None
    flags = (diligence or {}).get("red_flags") if diligence else val.get("risk", {}).get("flags", [])
    return {
        "target": val.get("target_name") or result.get("target_name") or "The target",
        "range": rr,
        "norm": val.get("normalization", {}),
        "risk": val.get("risk", {}),
        "approaches": val.get("approaches", {}),
        "flags": flags or [],
        "comparables": comparables,
        "completion": (diligence or {}).get("completion_pct"),
    }


def draft_narrative(result: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    o = options or {}
    v = _view(result)
    rr = v["range"]
    if not rr:
        raise ValueError("no recommended range found in result")

    paras: List[str] = []

    # 1. Headline.
    paras.append(
        f"{v['target']} is estimated to be worth an indicative {_money(rr.get('low'))} to "
        f"{_money(rr.get('high'))}, with a midpoint of {_money(rr.get('mid'))}."
    )

    # 2. What drives it.
    ap = v["approaches"]
    used = []
    if "income" in ap:
        used.append("a discounted-cash-flow and capitalization analysis")
    if "market" in ap:
        mk = ap["market"]
        used.append(f"comparable {str(mk.get('metric','')).upper()} multiples of "
                    f"{mk.get('low_multiple')}–{mk.get('high_multiple')}×")
    if "asset" in ap:
        used.append("a net-asset-value floor")
    norm = v["norm"]
    base = ""
    if norm.get("sde") or norm.get("normalized_ebitda"):
        base = (f" The estimate is anchored on normalized earnings of "
                f"{_money(norm.get('normalized_ebitda'))} EBITDA / {_money(norm.get('sde'))} SDE.")
    if used:
        paras.append("The range blends " + ", ".join(used) + "." + base)

    # 3. Comparables basis (orchestrator only).
    if v["comparables"]:
        c = v["comparables"]
        m = c.get("modifiers", {})
        paras.append(
            f"Market multiples are drawn from the {c.get('sector_matched')} sector "
            f"(base {c.get('base_band')}), adjusted for size (×{m.get('size_factor')}) and "
            f"growth (×{m.get('growth_factor')})."
        )

    # 4. Risk.
    disc = v["risk"].get("multiple_discount")
    flags = v["flags"]
    if flags:
        top = "; ".join(f.get("label", "") for f in flags[:3])
        risk_sent = f"Diligence surfaced {len(flags)} key risk(s): {top}."
        if disc:
            risk_sent += f" These reduced the valuation multiple by {disc*100:.0f}%."
        paras.append(risk_sent)
    elif disc:
        paras.append(f"A risk adjustment of {disc*100:.0f}% was applied to the multiple.")

    if v["completion"] is not None:
        paras.append(f"Diligence is {v['completion']}% complete; the estimate will firm up as "
                     "remaining items are closed.")

    # 5. Caveat.
    paras.append(
        "This is a decision-support estimate based on the inputs provided and standard "
        "methodologies — not financial, legal, or valuation advice. Price is ultimately "
        "set by negotiation and deal structure."
    )

    fmt = (o.get("format") or "markdown").lower()
    if fmt in ("markdown", "md"):
        body = "## Valuation summary — " + v["target"] + "\n\n" + "\n\n".join(paras)
    else:
        body = "\n\n".join(paras)

    return {"narrative": body, "format": fmt, "paragraphs": len(paras),
            "disclaimer": "Auto-drafted summary — review and edit before sharing."}
