"""Tests for the DealLens valuation engine — known-value and contract checks."""
import math

import pytest

from valuation_engine import (
    Adjustment, AdjustmentType, Deal, Financials, IncomeAssumptions,
    MarketAssumptions, RiskFlag, RiskSeverity, Weights, invoke, run,
)
from valuation_engine import income, market, asset, normalization
from valuation_engine.models import Range
from valuation_engine.triangulation import triangulate


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
def test_reported_ebitda_from_components():
    f = Financials(net_income=100, interest=10, taxes=20, depreciation=15, amortization=5)
    assert normalization.reported_ebitda(f) == 150


def test_normalized_ebitda_and_sde():
    f = Financials(net_income=300_000, owner_compensation=120_000)
    adj = [
        Adjustment("Owner car", 20_000, AdjustmentType.ADD_BACK),
        Adjustment("One-off gain", 30_000, AdjustmentType.DEDUCTION),
    ]
    norm = normalization.normalize(f, adj)
    # 300k + 20k - 30k = 290k normalized EBITDA; SDE adds owner comp.
    assert norm["normalized_ebitda"] == 290_000
    assert norm["sde"] == 410_000


# ---------------------------------------------------------------------------
# Income approach
# ---------------------------------------------------------------------------
def test_capitalization_of_earnings_known_value():
    out = income.capitalization_of_earnings(400_000, discount_rate=0.20, long_term_growth=0.0)
    assert out["value"] == pytest.approx(2_000_000)


def test_dcf_matches_manual_present_value():
    # No growth, flat FCF: value should equal sum of discounted flows + PV(TV).
    base = 100.0
    r = 0.10
    out = income.discounted_cash_flow(base, discount_rate=r, growth_rate=0.0,
                                      projection_years=3, terminal_growth=0.0)
    # Manual: FCF=100 each year for 3 yrs.
    pv_explicit = sum(100 / (1 + r) ** t for t in range(1, 4))
    tv = 100 / (r - 0.0)            # terminal_growth 0 -> 100/0.10 = 1000
    pv_tv = tv / (1 + r) ** 3
    expected = pv_explicit + pv_tv
    assert out["value"] == pytest.approx(expected, rel=1e-6)


def test_dcf_rejects_rate_le_terminal_growth():
    with pytest.raises(ValueError):
        income.discounted_cash_flow(100, discount_rate=0.02, growth_rate=0.0,
                                    projection_years=5, terminal_growth=0.02)


# ---------------------------------------------------------------------------
# Market & asset
# ---------------------------------------------------------------------------
def test_market_multiple_range():
    out = market.multiple_valuation(400_000, 3.0, 4.0, "sde")
    assert out["low"] == 1_200_000
    assert out["high"] == 1_600_000
    assert out["mid"] == 1_400_000


def test_net_asset_value():
    out = asset.net_asset_value(900_000, 350_000, fair_value_adjustment=50_000)
    assert out["value"] == 600_000


# ---------------------------------------------------------------------------
# Triangulation
# ---------------------------------------------------------------------------
def test_triangulation_weighted():
    ranges = {"market": Range(1_200_000, 1_600_000), "asset": Range(600_000, 600_000)}
    tri = triangulate(ranges, {"market": 1.0, "asset": 1.0})
    # Equal weights: low = (1.2M + 0.6M)/2 = 0.9M, high = (1.6M + 0.6M)/2 = 1.1M
    assert tri["weighted_range"]["low"] == 900_000
    assert tri["weighted_range"]["high"] == 1_100_000
    assert tri["floor"] == 600_000
    assert tri["ceiling"] == 1_600_000


def test_triangulation_requires_a_weighted_approach():
    with pytest.raises(ValueError):
        triangulate({"market": Range(1, 2)}, {"market": 0.0})


# ---------------------------------------------------------------------------
# Risk adjustment
# ---------------------------------------------------------------------------
def test_high_risk_flag_lowers_market_value():
    f = Financials(net_income=400_000, owner_compensation=0)
    base = Deal(financials=f, market=MarketAssumptions("ebitda", 4.0, 4.0),
                enabled_approaches=["market"], weights=Weights(0, 1, 0))
    clean = run(base)
    flagged_deal = Deal(financials=f, market=MarketAssumptions("ebitda", 4.0, 4.0),
                        enabled_approaches=["market"], weights=Weights(0, 1, 0),
                        risk_flags=[RiskFlag("Customer concentration", RiskSeverity.HIGH)])
    flagged = run(flagged_deal)
    assert flagged["approaches"]["market"]["mid"] < clean["approaches"]["market"]["mid"]
    # HIGH default discount is 12%.
    assert flagged["risk"]["multiple_discount"] == pytest.approx(0.12)


# ---------------------------------------------------------------------------
# Full engine + primitive contract
# ---------------------------------------------------------------------------
def test_full_run_produces_recommended_range():
    deal = Deal(
        target_name="Acme Co",
        financials=Financials(revenue=2_000_000, net_income=350_000,
                              owner_compensation=120_000, total_assets=800_000,
                              total_liabilities=300_000),
        adjustments=[Adjustment("Owner perks", 30_000)],
        income=IncomeAssumptions(discount_rate=0.22, growth_rate=0.05),
        market=MarketAssumptions("sde", 3.0, 5.0),
    )
    out = run(deal)
    rr = out["recommended_range"]
    assert rr["low"] <= rr["mid"] <= rr["high"]
    assert "income" in out["approaches"]
    assert "market" in out["approaches"]
    assert "asset" in out["approaches"]
    assert len(out["sensitivity"]["discount_rate"]) == 5


def test_invoke_envelope_ok():
    env = invoke({"financials": {"net_income": 400_000}, "market": {"metric": "ebitda"}})
    assert env["ok"] is True
    assert "recommended_range" in env["result"]


def test_invoke_envelope_error_is_caught():
    # Bad metric should be caught and returned as an error envelope, not raised.
    env = invoke({"market": {"metric": "banana"}})
    assert env["ok"] is False
    assert env["error"]["type"] in {"ValueError", "KeyError"}


def test_determinism():
    payload = {"financials": {"net_income": 500_000, "owner_compensation": 100_000},
               "market": {"metric": "sde", "low_multiple": 3, "high_multiple": 5}}
    assert invoke(payload) == invoke(payload)


# ---------------------------------------------------------------------------
# Hardening: loss-making / insolvent / degenerate inputs (regression tests)
# ---------------------------------------------------------------------------
def test_loss_making_does_not_produce_negative_range():
    # Negative earnings must not yield a confident negative/inverted valuation.
    out = run(Deal(financials=Financials(net_income=-200_000),
                   market=MarketAssumptions("ebitda", 3, 5)))
    rr = out["recommended_range"]
    if rr is not None:
        assert rr["low"] <= rr["high"]
        assert rr["low"] >= 0
    # income and market should be skipped with warnings
    assert "income" not in out["approaches"]
    assert "market" not in out["approaches"]
    assert any("non-positive" in w or "loss-making" in w for w in out["warnings"])


def test_negative_nav_floored_in_range_but_reported():
    out = run(Deal(financials=Financials(net_income=400_000, owner_compensation=0,
                                         total_assets=100_000, total_liabilities=500_000),
                   market=MarketAssumptions("ebitda", 3, 5)))
    assert out["approaches"]["asset"]["value"] == -400_000      # true NAV reported
    assert out["recommended_range"]["low"] >= 0                  # but floored in the range
    assert any("negative" in w.lower() for w in out["warnings"])


def test_market_range_not_inverted_for_any_input():
    out = market.multiple_valuation(-100_000, 3, 5, "sde")
    assert out["low"] <= out["high"]


def test_no_applicable_approach_is_graceful():
    # Loss-making, no assets, only income+market enabled -> graceful, not a crash.
    out = run(Deal(financials=Financials(net_income=-50_000),
                   market=MarketAssumptions("ebitda", 3, 5),
                   enabled_approaches=["income", "market"]))
    assert out["recommended_range"] is None
    assert any("no applicable" in w.lower() for w in out["warnings"])


def test_sensitivity_has_no_none_cells():
    out = run(Deal(financials=Financials(net_income=400_000),
                   income=IncomeAssumptions(discount_rate=0.03, terminal_growth=0.02),
                   market=MarketAssumptions("ebitda", 3, 5)))
    for row in out["sensitivity"]["discount_rate"]:
        assert row["dcf_value"] is not None
