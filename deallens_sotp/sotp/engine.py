"""Sum-of-the-parts (SOTP) valuation for conglomerates.

A conglomerate (Amazon = ecommerce + AWS + ads; a holding company; etc.) is
worth more than any single-sector multiple can capture, because each division
earns different margins and deserves a different multiple. SOTP values each
segment on its OWN sector comp, sums them, then applies a conglomerate/holdco
discount and subtracts net debt.

Composes the comparables primitive (one lookup per segment).
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _deps  # noqa: F401

ENGINE_NAME = "deallens.sotp"
ENGINE_VERSION = "1.0.0"


def _segment_multiple(seg: Dict[str, Any]) -> Dict[str, Any]:
    """Light path: earnings x a single sector multiple."""
    import comparables
    name = seg.get("name", "segment")
    earnings = float(seg.get("earnings", 0) or 0)
    env = comparables.invoke({
        "sector": seg.get("sector", "general"),
        "metric": seg.get("metric", "ebitda"),
        "tier": seg.get("tier", "smb"),
        "growth": seg.get("growth", ""),
    })
    if not env["ok"]:
        raise ValueError(f"segment {name!r}: {env['error']['message']}")
    c = env["result"]
    lo, hi = earnings * c["low_multiple"], earnings * c["high_multiple"]
    return {
        "name": name, "method": "single multiple",
        "sector": c["sector_matched"], "metric": c["metric"], "tier": c["tier"],
        "earnings": round(earnings, 2), "multiple": [c["low_multiple"], c["high_multiple"]],
        "value_range": {"low": round(lo, 2), "high": round(hi, 2)},
    }


def _segment_deep(seg: Dict[str, Any]) -> Dict[str, Any]:
    """Deep path: run the FULL valuation pipeline (DCF + multiples + NAV + risk +
    triangulation) on the segment's own financials, via the orchestrator."""
    import orchestrator
    name = seg.get("name", "segment")
    if not seg.get("financials"):
        raise ValueError(f"segment {name!r}: deep mode needs a 'financials' block")
    payload = {"target_name": name, "financials": seg["financials"]}
    for k in ("adjustments", "checklist", "comparables", "income", "weights",
              "market", "enabled_approaches"):
        if seg.get(k) is not None:
            payload[k] = seg[k]
    env = orchestrator.invoke(payload)
    if not env["ok"]:
        raise ValueError(f"segment {name!r}: {env['error']['message']}")
    r = env["result"]
    rng = r["recommendation"]["range"]
    if rng is None:
        raise ValueError(f"segment {name!r}: no valuation range (loss-making with no assets)")
    return {
        "name": name, "method": "deep (full valuation engine)",
        "normalized": r["valuation"].get("normalization", {}),
        "approaches": list(r["valuation"].get("approaches", {}).keys()),
        "risk_multiple_discount": r["valuation"].get("risk", {}).get("multiple_discount", 0),
        "value_range": {"low": rng["low"], "high": rng["high"]},
    }


def value_sotp(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object (dict)")
    segments = payload.get("segments") or []
    if not segments:
        raise ValueError("provide at least one segment in 'segments'")

    mode = (payload.get("mode") or "multiple").lower()
    if mode not in ("multiple", "deep"):
        raise ValueError("mode must be 'multiple' or 'deep'")

    net_debt = float(payload.get("net_debt", 0) or 0)          # +debt, -net cash
    discount = float(payload.get("conglomerate_discount", 0) or 0)
    if not 0 <= discount < 1:
        raise ValueError("conglomerate_discount must be between 0 and 1")

    breakdown: List[Dict[str, Any]] = []
    total_low = 0.0
    total_high = 0.0
    for seg in segments:
        b = _segment_deep(seg) if mode == "deep" else _segment_multiple(seg)
        total_low += b["value_range"]["low"]
        total_high += b["value_range"]["high"]
        breakdown.append(b)

    # Enterprise value -> apply conglomerate discount -> subtract net debt.
    disc_low = total_low * (1 - discount)
    disc_high = total_high * (1 - discount)
    eq_low = max(disc_low - net_debt, 0.0)
    eq_high = max(disc_high - net_debt, 0.0)

    return {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "mode": mode,
        "segments": breakdown,
        "gross_enterprise_range": {"low": round(total_low, 2), "high": round(total_high, 2)},
        "conglomerate_discount": discount,
        "net_debt": net_debt,
        "equity_range": {"low": round(eq_low, 2), "high": round(eq_high, 2),
                          "mid": round((eq_low + eq_high) / 2, 2)},
        "method": "Sum-of-the-parts: each segment on its own sector comp, then "
                  "conglomerate discount and net debt.",
        "disclaimer": "Illustrative; decision-support only, not financial advice.",
    }
