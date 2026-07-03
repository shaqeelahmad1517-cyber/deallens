"""Earnings normalization: reported figures -> normalized EBITDA and SDE."""
from __future__ import annotations

from typing import Dict, List

from .models import Adjustment, Financials


def reported_ebitda(f: Financials) -> float:
    """EBITDA from components: NI + interest + taxes + D + A."""
    return f.net_income + f.interest + f.taxes + f.depreciation + f.amortization


def adjustments_total(adjustments: List[Adjustment]) -> float:
    return sum(a.signed_amount() for a in adjustments)


def normalized_ebitda(f: Financials, adjustments: List[Adjustment]) -> float:
    """Reported EBITDA plus signed normalization adjustments."""
    return reported_ebitda(f) + adjustments_total(adjustments)


def sde(f: Financials, adjustments: List[Adjustment]) -> float:
    """Seller's Discretionary Earnings = normalized EBITDA + owner comp."""
    return normalized_ebitda(f, adjustments) + f.owner_compensation


def normalize(f: Financials, adjustments: List[Adjustment]) -> Dict[str, float]:
    """Return the full normalization breakdown for transparency/audit."""
    base = reported_ebitda(f)
    delta = adjustments_total(adjustments)
    n_ebitda = base + delta
    return {
        "reported_ebitda": round(base, 2),
        "adjustments_total": round(delta, 2),
        "normalized_ebitda": round(n_ebitda, 2),
        "sde": round(n_ebitda + f.owner_compensation, 2),
        "revenue": round(f.revenue, 2),
    }
