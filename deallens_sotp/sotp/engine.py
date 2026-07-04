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


def value_sotp(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object (dict)")
    segments = payload.get("segments") or []
    if not segments:
        raise ValueError("provide at least one segment in 'segments'")

    net_debt = float(payload.get("net_debt", 0) or 0)          # +debt, -net cash
    discount = float(payload.get("conglomerate_discount", 0) or 0)
    if not 0 <= discount < 1:
        raise ValueError("conglomerate_discount must be between 0 and 1")

    import comparables

    breakdown: List[Dict[str, Any]] = []
    total_low = 0.0
    total_high = 0.0
    for seg in segments:
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
        lo = earnings * c["low_multiple"]
        hi = earnings * c["high_multiple"]
        total_low += lo
        total_high += hi
        breakdown.append({
            "name": name,
            "sector": c["sector_matched"],
            "metric": c["metric"],
            "tier": c["tier"],
            "earnings": round(earnings, 2),
            "multiple": [c["low_multiple"], c["high_multiple"]],
            "value_range": {"low": round(lo, 2), "high": round(hi, 2)},
        })

    # Enterprise value -> apply conglomerate discount -> subtract net debt.
    disc_low = total_low * (1 - discount)
    disc_high = total_high * (1 - discount)
    eq_low = max(disc_low - net_debt, 0.0)
    eq_high = max(disc_high - net_debt, 0.0)

    return {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
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
