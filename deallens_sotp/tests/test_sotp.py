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
    # saas public ebitda 20-40, retail public ebitda 6-10
    # cloud: 100*20..40 = 2000..4000 ; retail: 200*6..10 = 1200..2000
    assert out["gross_enterprise_range"]["low"] == 2000 + 1200
    assert out["gross_enterprise_range"]["high"] == 4000 + 2000
    assert len(out["segments"]) == 2


def test_conglomerate_discount_and_net_debt():
    payload = dict(_two_segments(), conglomerate_discount=0.10, net_debt=500)
    out = value_sotp(payload)
    gl, gh = 3200, 6000
    assert out["equity_range"]["low"] == pytest.approx(gl * 0.9 - 500)
    assert out["equity_range"]["high"] == pytest.approx(gh * 0.9 - 500)


def test_net_cash_increases_value():
    payload = dict(_two_segments(), net_debt=-1000)   # net cash
    out = value_sotp(payload)
    assert out["equity_range"]["low"] == 3200 + 1000


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
