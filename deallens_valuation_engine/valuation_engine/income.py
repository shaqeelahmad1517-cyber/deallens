"""Income approach: discounted cash flow and capitalization of earnings."""
from __future__ import annotations

from typing import Dict, List


def discounted_cash_flow(
    base_fcf: float,
    discount_rate: float,
    growth_rate: float,
    projection_years: int,
    terminal_growth: float,
) -> Dict[str, object]:
    """Multi-stage DCF with a Gordon-growth terminal value.

    base_fcf is year-0 free cash flow; year-t FCF = base_fcf*(1+g)^t.
    Returns the enterprise value plus a per-year schedule for audit.
    """
    if discount_rate <= terminal_growth:
        raise ValueError("discount_rate must exceed terminal_growth for a finite terminal value")
    if projection_years < 1:
        raise ValueError("projection_years must be >= 1")

    schedule: List[Dict[str, float]] = []
    pv_explicit = 0.0
    last_fcf = base_fcf
    for t in range(1, projection_years + 1):
        fcf_t = base_fcf * (1.0 + growth_rate) ** t
        discount_factor = 1.0 / (1.0 + discount_rate) ** t
        pv_t = fcf_t * discount_factor
        pv_explicit += pv_t
        last_fcf = fcf_t
        schedule.append({
            "year": t,
            "fcf": round(fcf_t, 2),
            "discount_factor": round(discount_factor, 6),
            "pv": round(pv_t, 2),
        })

    terminal_fcf = last_fcf * (1.0 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1.0 + discount_rate) ** projection_years
    enterprise_value = pv_explicit + pv_terminal

    return {
        "method": "dcf",
        "value": round(enterprise_value, 2),
        "pv_explicit": round(pv_explicit, 2),
        "terminal_value": round(terminal_value, 2),
        "pv_terminal": round(pv_terminal, 2),
        "schedule": schedule,
    }


def capitalization_of_earnings(
    earnings: float,
    discount_rate: float,
    long_term_growth: float,
) -> Dict[str, object]:
    """Single-period capitalization: value = earnings / (r - g)."""
    cap_rate = discount_rate - long_term_growth
    if cap_rate <= 0:
        raise ValueError("capitalization rate (discount_rate - long_term_growth) must be positive")
    value = earnings / cap_rate
    return {
        "method": "capitalization_of_earnings",
        "value": round(value, 2),
        "cap_rate": round(cap_rate, 6),
        "earnings": round(earnings, 2),
    }
