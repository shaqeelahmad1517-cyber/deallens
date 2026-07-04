"""DealLens quick-screen — fast indicative valuation for deal triage.

A stripped-down path: take an earnings figure and a sector, pull a comparable
multiple band, apply a light risk haircut, and return an indicative range in
seconds. Optionally compare an asking price to the range for a go/no-go read.

Deterministic and pure. Depends only on the comparables library.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import _deps  # noqa: F401

ENGINE_NAME = "deallens.quickscreen"
ENGINE_VERSION = "1.0.0"

# Risk haircut per severity — matches the valuation engine's defaults.
_SEV_HAIRCUT = {"low": 0.02, "medium": 0.05, "high": 0.12}
_MAX_HAIRCUT = 0.40


def _build_flags(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """Collect risk flags from explicit list + convenience signals."""
    flags: List[Dict[str, str]] = []
    for f in payload.get("risk_flags", []) or []:
        sev = str(f.get("severity", "medium")).lower()
        if sev in _SEV_HAIRCUT:
            flags.append({"label": f.get("label", "Risk"), "severity": sev})

    # Convenience signals.
    tc = payload.get("top_customer_pct")
    if tc is not None:
        try:
            tc = float(tc)
            if tc >= 35:
                flags.append({"label": f"Customer concentration {tc:.0f}%", "severity": "high"})
            elif tc >= 20:
                flags.append({"label": f"Customer concentration {tc:.0f}%", "severity": "medium"})
        except (TypeError, ValueError):
            pass
    if payload.get("owner_dependent") is True:
        flags.append({"label": "Owner dependence", "severity": "high"})
    return flags


def _haircut(flags: List[Dict[str, str]]) -> float:
    return min(sum(_SEV_HAIRCUT[f["severity"]] for f in flags), _MAX_HAIRCUT)


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object (dict)")

    earnings = payload.get("earnings")
    if earnings is None:
        raise ValueError("'earnings' is required (the metric value, e.g. SDE or EBITDA)")
    earnings = float(earnings)
    if earnings <= 0:
        raise ValueError(
            "quick-screen needs positive earnings (SDE/EBITDA). The target appears "
            "loss-making — a multiple-based screen isn't meaningful; run the full pipeline."
        )
    metric = (payload.get("metric") or "sde").lower()
    sector = payload.get("sector") or "general"
    growth = payload.get("growth", "")
    tier = (payload.get("tier") or "smb").lower()

    import comparables
    comp_env = comparables.invoke({
        "sector": sector,
        "metric": metric,
        "size_ebitda": payload.get("size_ebitda", earnings if metric in ("sde", "ebitda") else None),
        "growth": growth,
        "tier": tier,
    })
    if not comp_env["ok"]:
        raise ValueError(f"comparables lookup failed: {comp_env['error']['message']}")
    comp = comp_env["result"]
    low_m, high_m = comp["low_multiple"], comp["high_multiple"]

    flags = _build_flags(payload)
    haircut = _haircut(flags)
    retain = 1.0 - haircut

    low = earnings * low_m * retain
    high = earnings * high_m * retain
    mid = (low + high) / 2.0

    result: Dict[str, Any] = {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "earnings": round(earnings, 2),
        "metric": metric,
        "sector": comp["sector_matched"],
        "multiple_band_adjusted": [round(low_m * retain, 3), round(high_m * retain, 3)],
        "risk_haircut": round(haircut, 3),
        "risk_flags": flags,
        "range": {"low": round(low, 2), "high": round(high, 2), "mid": round(mid, 2)},
        "comparables": {
            "base_band": comp["base_band"],
            "modifiers": comp["modifiers"],
            "source": comp.get("source", ""),
        },
        "disclaimer": "Indicative triage estimate only — a quick screen, not a full "
                      "valuation or advice. Run the full pipeline before deciding.",
    }

    asking = payload.get("asking_price")
    if asking is not None:
        asking = float(asking)
        if asking < low:
            verdict, note = "below_range", "Asking price is below the indicative range — potentially attractive."
        elif asking > high:
            verdict, note = "above_range", "Asking price is above the indicative range — looks expensive."
        else:
            verdict, note = "within_range", "Asking price sits within the indicative range — broadly fair."
        # crude premium/discount vs midpoint
        delta = (asking - mid) / mid if mid else 0.0
        result["asking_price"] = round(asking, 2)
        result["verdict"] = verdict
        result["verdict_note"] = note
        result["vs_midpoint_pct"] = round(delta * 100, 1)

    return result
