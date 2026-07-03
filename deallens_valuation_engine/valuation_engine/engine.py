"""DealLens valuation engine — deterministic orchestrator.

Pure function of its input ``Deal``: same input always yields the same output,
no I/O, no global state. This is what makes it safe to embed as a primitive.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from . import asset, income, market, normalization, risk, triangulation
from .models import Deal, Range

ENGINE_NAME = "deallens.valuation"
ENGINE_VERSION = "1.0.0"


def _metric_value(metric: str, norm: Dict[str, float]) -> float:
    metric = (metric or "sde").lower()
    if metric == "sde":
        return norm["sde"]
    if metric == "ebitda":
        return norm["normalized_ebitda"]
    if metric == "revenue":
        return norm["revenue"]
    raise ValueError(f"unknown market metric: {metric!r} (use sde, ebitda, or revenue)")


def _dcf_value(base_fcf: float, discount_rate: float, deal: Deal) -> float:
    return income.discounted_cash_flow(
        base_fcf=base_fcf,
        discount_rate=discount_rate,
        growth_rate=deal.income.growth_rate,
        projection_years=deal.income.projection_years,
        terminal_growth=deal.income.terminal_growth,
    )["value"]


def _sensitivity(deal: Deal, base_fcf: float, eff_discount_rate: float,
                 metric_value: float, eff_low_m: float, eff_high_m: float) -> Dict[str, object]:
    """Vary the two dominant drivers: discount rate and market multiple."""
    rate_steps = [-0.02, -0.01, 0.0, 0.01, 0.02]
    discount_table = []
    for d in rate_steps:
        r = round(eff_discount_rate + d, 6)
        try:
            # Skip rows where the rate is invalid (<= terminal growth) instead
            # of emitting None cells that downstream consumers would choke on.
            discount_table.append({"discount_rate": r, "dcf_value": _dcf_value(base_fcf, r, deal)})
        except ValueError:
            continue

    mid_m = (eff_low_m + eff_high_m) / 2.0
    mult_steps = [-1.0, -0.5, 0.0, 0.5, 1.0]
    multiple_table = []
    for d in mult_steps:
        m = round(mid_m + d, 4)
        multiple_table.append({"multiple": m, "value": round(metric_value * m, 2)})

    return {"discount_rate": discount_table, "market_multiple": multiple_table}


def run(deal: Deal) -> Dict[str, object]:
    """Run the full valuation and return a JSON-serializable result."""
    enabled = [a.lower() for a in deal.enabled_approaches]

    # 1. Normalize earnings.
    norm = normalization.normalize(deal.financials, deal.adjustments)

    # 2. Diligence risk -> adjustments.
    risk_assessment = risk.assess(deal.risk_flags)
    multiple_discount = risk_assessment["multiple_discount"]
    rate_premium = risk_assessment["discount_rate_premium"]

    approaches: Dict[str, object] = {}
    approach_ranges: Dict[str, Range] = {}
    warnings: List[str] = []

    # 3. Income approach. Guard the EARNINGS NUMERATOR, not just the rates:
    # DCF and capitalization are economically undefined for a loss-making target.
    base_fcf: Optional[float] = deal.financials.base_free_cash_flow
    if base_fcf is None:
        base_fcf = norm["normalized_ebitda"] * deal.income.fcf_conversion
    eff_discount_rate = deal.income.discount_rate + rate_premium
    if "income" in enabled:
        income_out: Dict[str, object] = {}
        income_vals: List[float] = []
        if base_fcf > 0:
            dcf = income.discounted_cash_flow(
                base_fcf=base_fcf,
                discount_rate=eff_discount_rate,
                growth_rate=deal.income.growth_rate,
                projection_years=deal.income.projection_years,
                terminal_growth=deal.income.terminal_growth,
            )
            income_out["dcf"] = dcf
            income_vals.append(dcf["value"])
        else:
            warnings.append("Income/DCF skipped: free cash flow is non-positive (loss-making target).")
        if norm["normalized_ebitda"] > 0:
            cap = income.capitalization_of_earnings(
                earnings=norm["normalized_ebitda"],
                discount_rate=eff_discount_rate,
                long_term_growth=deal.income.long_term_growth,
            )
            income_out["capitalization"] = cap
            income_vals.append(cap["value"])
        else:
            warnings.append("Capitalization skipped: normalized EBITDA is non-positive.")
        if income_vals:
            lo, hi = min(income_vals), max(income_vals)
            income_out["range"] = Range(lo, hi).to_dict()
            approaches["income"] = income_out
            approach_ranges["income"] = Range(lo, hi)

    # 4. Market approach (risk discount applied to multiples). Skip for a
    # non-positive metric — a multiple of a loss is meaningless.
    eff_low_m = deal.market.low_multiple * (1.0 - multiple_discount)
    eff_high_m = deal.market.high_multiple * (1.0 - multiple_discount)
    metric_value = _metric_value(deal.market.metric, norm)
    if "market" in enabled:
        if metric_value > 0:
            mkt = market.multiple_valuation(metric_value, eff_low_m, eff_high_m, deal.market.metric)
            mkt["risk_multiple_discount"] = multiple_discount
            approaches["market"] = mkt
            approach_ranges["market"] = Range(mkt["low"], mkt["high"])
        else:
            warnings.append(f"Market approach skipped: {deal.market.metric} is non-positive.")

    # 5. Asset approach. Report true NAV, but a negative (insolvent) NAV is
    # floored at 0 as a valuation FLOOR so it can't drag the range below zero.
    if "asset" in enabled:
        nav = asset.net_asset_value(
            deal.financials.total_assets,
            deal.financials.total_liabilities,
            deal.financials.fair_value_adjustment,
        )
        approaches["asset"] = nav
        nav_floor = max(nav["value"], 0.0)
        if nav["value"] < 0:
            warnings.append("Net asset value is negative (liabilities exceed assets); floored at 0 for the range.")
        approach_ranges["asset"] = Range(nav_floor, nav_floor)

    # 6. Triangulate (gracefully handle the no-applicable-approach case).
    weights = {"income": deal.weights.income, "market": deal.weights.market, "asset": deal.weights.asset}
    if approach_ranges:
        tri = triangulation.triangulate(approach_ranges, weights)
        recommended = tri["weighted_range"]
    else:
        tri = None
        recommended = None
        warnings.append("No applicable valuation approach — target appears loss-making with no net assets.")

    # 7. Sensitivity (only meaningful when the income approach actually ran).
    if "income" in approaches and base_fcf > 0:
        sensitivity = _sensitivity(deal, base_fcf, eff_discount_rate, metric_value, eff_low_m, eff_high_m)
    else:
        sensitivity = {"discount_rate": [], "market_multiple": []}

    return {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "target_name": deal.target_name,
        "normalization": norm,
        "base_free_cash_flow": round(base_fcf, 2),
        "effective_discount_rate": round(eff_discount_rate, 6),
        "risk": risk_assessment,
        "approaches": approaches,
        "triangulation": tri,
        "sensitivity": sensitivity,
        "warnings": warnings,
        "recommended_range": recommended,
        "disclaimer": (
            "Decision-support only. Outputs are based on user-supplied data and "
            "standard methodologies; not financial, legal, or valuation advice."
        ),
    }


class ValuationEngine:
    """Thin OO wrapper for hosts that prefer an object handle."""
    name = ENGINE_NAME
    version = ENGINE_VERSION

    def run(self, deal: Deal) -> Dict[str, object]:
        return run(deal)

    def run_dict(self, payload: Dict[str, object]) -> Dict[str, object]:
        return run(Deal.from_dict(payload))
