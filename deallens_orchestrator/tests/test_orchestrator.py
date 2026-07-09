"""Tests for the DealLens orchestrator (requires the three sibling engines)."""
import pytest

# Skip the whole module cleanly if the sibling engines aren't importable.
orchestrator = pytest.importorskip("orchestrator")
pytest.importorskip("valuation_engine")
pytest.importorskip("diligence_engine")
pytest.importorskip("comparables")


def _full_payload(**overrides):
    p = {
        "target_name": "Acme",
        "financials": {"revenue": 4200000, "net_income": 520000, "interest": 40000,
                       "taxes": 110000, "depreciation": 90000, "amortization": 20000,
                       "owner_compensation": 180000, "total_assets": 1900000,
                       "total_liabilities": 700000},
        "adjustments": [{"label": "Owner perks", "amount": 35000, "type": "add_back"}],
        "checklist": {
            "business_type": "smb",
            "items": [{"id": "cust_concentration", "status": "flagged", "risk_rating": "high"}],
            "signals": {"top_customer_pct": 38, "owner_dependent": True, "revenue_trend": "growing"},
        },
        "comparables": {"sector": "logistics", "metric": "sde"},
    }
    p.update(overrides)
    return p


def test_public_tier_uses_low_cost_of_capital():
    # Same financials, public tier -> ~8% discount rate and a much higher DCF than SMB.
    fin = {"revenue": 20094e6, "net_income": 2594e6, "interest": 382e6,
           "taxes": 612e6, "depreciation": 547e6}
    base = {"target_name": "Mega", "financials": fin, "checklist": {"business_type": "general"}}
    smb = orchestrator.invoke(dict(base, comparables={"sector": "consumer_staples", "metric": "ebitda", "tier": "smb"}))["result"]
    pub = orchestrator.invoke(dict(base, comparables={"sector": "consumer_staples", "metric": "ebitda", "tier": "public"}))["result"]
    assert pub["assumptions"]["cost_of_capital"]["discount_rate"] == 0.08
    assert smb["assumptions"]["cost_of_capital"]["discount_rate"] == 0.20
    # Lower discount rate -> higher DCF.
    assert pub["valuation"]["approaches"]["income"]["dcf"]["value"] > \
           smb["valuation"]["approaches"]["income"]["dcf"]["value"] * 2


def test_explicit_income_overrides_tier_default():
    fin = {"revenue": 20094e6, "net_income": 2594e6, "depreciation": 547e6}
    env = orchestrator.invoke({"target_name": "Mega", "financials": fin,
                               "comparables": {"sector": "consumer_staples", "metric": "ebitda", "tier": "public"},
                               "income": {"discount_rate": 0.11}})
    assert env["result"]["assumptions"]["cost_of_capital"]["discount_rate"] == 0.11


def test_full_pipeline_ok():
    env = orchestrator.invoke(_full_payload())
    assert env["ok"] is True
    r = env["result"]
    assert r["steps"]["diligence"]["ok"]
    assert r["steps"]["comparables"]["ok"]
    assert r["steps"]["valuation"]["ok"]
    rr = r["recommendation"]["range"]
    assert rr["low"] <= rr["mid"] <= rr["high"]


def test_diligence_flags_reach_valuation():
    env = orchestrator.invoke(_full_payload())
    r = env["result"]
    # The high customer-concentration flag should produce a non-zero risk cut.
    assert r["recommendation"]["risk_multiple_discount"] > 0
    assert any("concentration" in k.lower() for k in r["recommendation"]["key_risks"])


def test_comparables_drive_market_multiple():
    env = orchestrator.invoke(_full_payload())
    r = env["result"]
    comp_low = r["comparables"]["low_multiple"]
    mkt_low = r["valuation"]["approaches"]["market"]["low_multiple"]
    # Valuation may further discount the multiple for risk, so market <= comps.
    assert mkt_low <= comp_low + 1e-6
    assert mkt_low > 0


def test_size_auto_derived_from_financials():
    # No size_ebitda supplied; orchestrator should infer it and pick a size band.
    env = orchestrator.invoke(_full_payload())
    assert env["result"]["comparables"]["modifiers"]["size_band"] != "unspecified"


def test_growth_auto_derived_from_signal():
    env = orchestrator.invoke(_full_payload())
    assert env["result"]["comparables"]["modifiers"]["growth"] == "growing"


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------
def test_bad_sector_degrades_but_still_values():
    payload = _full_payload(comparables={"sector": "atlantis", "metric": "sde"})
    env = orchestrator.invoke(payload)
    assert env["ok"] is True                      # overall still succeeds
    r = env["result"]
    assert r["steps"]["comparables"]["ok"] is False
    assert any("comparables failed" in w for w in r["warnings"])
    assert r["steps"]["valuation"]["ok"]          # valuation still ran (engine default market)


def test_no_checklist_means_no_flags_but_ok():
    payload = _full_payload()
    del payload["checklist"]
    env = orchestrator.invoke(payload)
    assert env["ok"] is True
    assert env["result"]["steps"]["diligence"].get("skipped")
    assert env["result"]["recommendation"]["risk_multiple_discount"] == 0


def test_explicit_market_used_when_comparables_omitted():
    payload = _full_payload()
    del payload["comparables"]
    payload["market"] = {"metric": "sde", "low_multiple": 3.0, "high_multiple": 4.0}
    env = orchestrator.invoke(payload)
    assert env["ok"] is True
    assert env["result"]["valuation"]["approaches"]["market"]["high_multiple"] <= 4.0 + 1e-6


def test_invoke_error_envelope_on_bad_input():
    env = orchestrator.invoke("not a dict")
    assert env["ok"] is False
    assert env["error"]["type"] == "TypeError"


def test_determinism():
    p = _full_payload()
    assert orchestrator.invoke(p) == orchestrator.invoke(p)
