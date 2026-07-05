"""Tests for the sum-of-the-parts primitive (composes comparables)."""
from sotp import invoke, value_sotp
import pytest

pytest.importorskip("comparables")


def _two_segments():
    return {
        "segments": [
            {"name": "Cloud", "sector": "saas", "metric": "ebitda", "tier": "public", "earnings": 100},
            {"name": "Retail", "sector": "retail", "metric": "ebitda", "tier": "public", "earnings": 200},
        ],
    }


def test_sums_segments():
    out = value_sotp(_two_segments())
    # saas public ebitda 15-35, retail public ebitda 6-10
    # cloud: 100*15..35 = 1500..3500 ; retail: 200*6..10 = 1200..2000
    assert out["gross_enterprise_range"]["low"] == 1500 + 1200
    assert out["gross_enterprise_range"]["high"] == 3500 + 2000
    assert len(out["segments"]) == 2


def test_conglomerate_discount_and_net_debt():
    payload = dict(_two_segments(), conglomerate_discount=0.10, net_debt=500)
    out = value_sotp(payload)
    gl, gh = 2700, 5500
    assert out["equity_range"]["low"] == pytest.approx(gl * 0.9 - 500)
    assert out["equity_range"]["high"] == pytest.approx(gh * 0.9 - 500)


def test_net_cash_increases_value():
    payload = dict(_two_segments(), net_debt=-1000)   # net cash
    out = value_sotp(payload)
    assert out["equity_range"]["low"] == 2700 + 1000


def test_per_segment_breakdown():
    out = value_sotp(_two_segments())
    names = {s["name"] for s in out["segments"]}
    assert names == {"Cloud", "Retail"}
    assert all("multiple" in s and "value_range" in s for s in out["segments"])


def test_requires_segments():
    env = invoke({"segments": []})
    assert env["ok"] is False and env["error"]["type"] == "ValueError"


def test_bad_segment_sector_errors():
    env = invoke({"segments": [{"name": "X", "sector": "atlantis", "earnings": 100}]})
    assert env["ok"] is False


def test_discount_out_of_range():
    env = invoke({"segments": [{"name": "X", "sector": "retail", "earnings": 100}],
                  "conglomerate_discount": 1.5})
    assert env["ok"] is False


def test_invoke_ok():
    env = invoke(_two_segments())
    assert env["ok"] and env["result"]["equity_range"]["mid"] > 0
    assert env["result"]["mode"] == "multiple"


# ---------------------------------------------------------------------------
# Deep mode: full valuation engine per segment
# ---------------------------------------------------------------------------
def _deep_payload():
    return {
        "mode": "deep",
        "segments": [
            {"name": "Cloud",
             "financials": {"net_income": 30_000_000_000, "depreciation": 8_000_000_000,
                            "total_assets": 90_000_000_000, "total_liabilities": 20_000_000_000},
             "comparables": {"sector": "saas", "metric": "ebitda", "tier": "public"}},
            {"name": "Retail",
             "financials": {"net_income": 10_000_000_000, "depreciation": 20_000_000_000,
                            "total_assets": 250_000_000_000, "total_liabilities": 150_000_000_000},
             "comparables": {"sector": "ecommerce", "metric": "ebitda", "tier": "public"}},
        ],
        "conglomerate_discount": 0.10,
    }


def test_deep_mode_runs_full_engine():
    pytest.importorskip("orchestrator")
    out = value_sotp(_deep_payload())
    assert out["mode"] == "deep"
    # each segment reports the approaches the full engine used
    for s in out["segments"]:
        assert s["method"].startswith("deep")
        assert "income" in s["approaches"] or "market" in s["approaches"]
        assert s["value_range"]["low"] <= s["value_range"]["high"]
    assert out["equity_range"]["mid"] > 0


def test_deep_mode_requires_financials():
    pytest.importorskip("orchestrator")
    env = invoke({"mode": "deep", "segments": [{"name": "X", "comparables": {"sector": "saas"}}]})
    assert env["ok"] is False
    assert "financials" in env["error"]["message"]


def test_unknown_mode_errors():
    env = invoke(dict(_two_segments(), mode="quantum"))
    assert env["ok"] is False and env["error"]["type"] == "ValueError"
