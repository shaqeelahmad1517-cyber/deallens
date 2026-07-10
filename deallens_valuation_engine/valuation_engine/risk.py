"""Diligence risk -> transparent valuation adjustments.

Red flags from due diligence reduce the market multiple and raise the
discount rate. Defaults are derived from severity; explicit per-flag
overrides take precedence. All applied deltas are reported back so the
adjustment is never a black box.
"""
from __future__ import annotations

from typing import Dict, List

from .models import RiskFlag, RiskSeverity

# Severity-based default deltas.
_MULTIPLE_DISCOUNT = {
    RiskSeverity.LOW: 0.02,
    RiskSeverity.MEDIUM: 0.05,
    RiskSeverity.HIGH: 0.12,
}
_DISCOUNT_RATE_PREMIUM = {
    RiskSeverity.LOW: 0.005,
    RiskSeverity.MEDIUM: 0.015,
    RiskSeverity.HIGH: 0.03,
}

# Cap the cumulative effect so a long flag list can't zero out value.
_MAX_MULTIPLE_DISCOUNT = 0.35
_MAX_RATE_PREMIUM = 0.05


def assess(flags: List[RiskFlag]) -> Dict[str, object]:
    """Aggregate flags into a multiple discount and rate premium.

    Uses DIMINISHING (multiplicative) aggregation, not a linear sum: each flag
    reduces what's left rather than adding a fixed amount, so a long list of modest
    risks compounds to a substantial-but-not-catastrophic discount instead of
    linearly slamming into the cap. A single severe flag still bites hard.
    """
    retention = 1.0        # fraction of the multiple that survives
    rate_retention = 1.0   # combine rate premiums with diminishing returns too
    detail = []
    for flag in flags or []:
        f_md = flag.multiple_discount if flag.multiple_discount is not None else _MULTIPLE_DISCOUNT[flag.severity]
        f_rp = flag.discount_rate_premium if flag.discount_rate_premium is not None else _DISCOUNT_RATE_PREMIUM[flag.severity]
        retention *= (1.0 - max(0.0, min(f_md, 0.95)))
        rate_retention *= (1.0 - max(0.0, min(f_rp / _MAX_RATE_PREMIUM, 0.95)))
        detail.append({
            "label": flag.label,
            "severity": flag.severity.value,
            "category": flag.category,
            "multiple_discount": round(f_md, 4),
            "discount_rate_premium": round(f_rp, 4),
        })

    md = min(1.0 - retention, _MAX_MULTIPLE_DISCOUNT)
    rp = min(_MAX_RATE_PREMIUM * (1.0 - rate_retention), _MAX_RATE_PREMIUM)
    return {
        "multiple_discount": round(md, 4),
        "discount_rate_premium": round(rp, 4),
        "multiple_retention": round(1.0 - md, 4),
        "flags": detail,
        "flag_count": len(detail),
    }
