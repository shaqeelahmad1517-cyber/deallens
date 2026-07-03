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
_MAX_MULTIPLE_DISCOUNT = 0.40
_MAX_RATE_PREMIUM = 0.10


def assess(flags: List[RiskFlag]) -> Dict[str, object]:
    """Aggregate flags into cumulative multiple discount and rate premium."""
    md = 0.0
    rp = 0.0
    detail = []
    for flag in flags or []:
        f_md = flag.multiple_discount if flag.multiple_discount is not None else _MULTIPLE_DISCOUNT[flag.severity]
        f_rp = flag.discount_rate_premium if flag.discount_rate_premium is not None else _DISCOUNT_RATE_PREMIUM[flag.severity]
        md += f_md
        rp += f_rp
        detail.append({
            "label": flag.label,
            "severity": flag.severity.value,
            "category": flag.category,
            "multiple_discount": round(f_md, 4),
            "discount_rate_premium": round(f_rp, 4),
        })

    md = min(md, _MAX_MULTIPLE_DISCOUNT)
    rp = min(rp, _MAX_RATE_PREMIUM)
    return {
        "multiple_discount": round(md, 4),
        "discount_rate_premium": round(rp, 4),
        "multiple_retention": round(1.0 - md, 4),
        "flags": detail,
        "flag_count": len(detail),
    }
