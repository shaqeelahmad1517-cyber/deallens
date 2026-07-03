"""Tests for the DealLens quick-screen primitive (needs comparables library)."""
import pytest

# Importing quickscreen puts the sibling comparables library on sys.path.
from quickscreen import invoke, run
pytest.importorskip("comparables")


def test_basic_range():
    out = run({"earnings": 1_000_000, "metric": "sde", "sector": "logistics"})
    r = out["range"]
    assert r["low"] < r["mid"] < r["high"]
    assert r["low"] > 0


def test_requires_earnings():
    env = invoke({"sector": "logistics"})
    assert env["ok"] is False
    assert env["error"]["type"] == "ValueError"


def test_bad_sector_errors():
    env = invoke({"earnings": 500_000, "sector": "atlantis"})
    assert env["ok"] is False


def test_risk_haircut_lowers_value():
    clean = run({"earnings": 1_000_000, "sector": "logistics"})
    risky = run({"earnings": 1_000_000, "sector": "logistics",
                 "top_customer_pct": 40, "owner_dependent": True})
    assert risky["risk_haircut"] > 0
    assert risky["range"]["high"] < clean["range"]["high"]
    # two high flags => 0.24 haircut
    assert risky["risk_haircut"] == pytest.approx(0.24)


def test_haircut_capped():
    flags = [{"label": f"r{i}", "severity": "high"} for i in range(10)]
    out = run({"earnings": 1_000_000, "sector": "logistics", "risk_flags": flags})
    assert out["risk_haircut"] == 0.40


def test_asking_price_below_range():
    out = run({"earnings": 1_000_000, "sector": "logistics", "asking_price": 100_000})
    assert out["verdict"] == "below_range"


def test_asking_price_above_range():
    out = run({"earnings": 1_000_000, "sector": "logistics", "asking_price": 99_000_000})
    assert out["verdict"] == "above_range"


def test_asking_price_within_range():
    out = run({"earnings": 1_000_000, "sector": "logistics"})
    mid = out["range"]["mid"]
    out2 = run({"earnings": 1_000_000, "sector": "logistics", "asking_price": mid})
    assert out2["verdict"] == "within_range"
    assert out2["vs_midpoint_pct"] == pytest.approx(0.0, abs=0.5)


def test_determinism():
    p = {"earnings": 830000, "sector": "saas", "metric": "ebitda", "growth": "high"}
    assert invoke(p) == invoke(p)


def test_invoke_ok_shape():
    env = invoke({"earnings": 1_010_000, "sector": "logistics", "metric": "sde"})
    assert env["ok"] is True
    assert "range" in env["result"] and "multiple_band_adjusted" in env["result"]


def test_negative_earnings_rejected():
    env = invoke({"earnings": -500_000, "sector": "logistics"})
    assert env["ok"] is False
    assert env["error"]["type"] == "ValueError"
    assert "loss-making" in env["error"]["message"]


def test_zero_earnings_rejected():
    env = invoke({"earnings": 0, "sector": "logistics"})
    assert env["ok"] is False
