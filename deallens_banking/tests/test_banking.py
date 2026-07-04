"""Tests for the banking valuation primitive."""
import pytest

from banking import invoke, value_bank


def test_pb_and_pe_blend():
    out = value_bank({"bank_type": "universal_bank", "net_income": 12_000_000_000,
                      "book_value": 200_000_000_000})
    pb = out["approaches"]["price_to_book"]
    pe = out["approaches"]["price_to_earnings"]
    assert pb["low"] == 200e9 * 0.6 and pb["high"] == 200e9 * 1.2
    assert pe["low"] == 12e9 * 8 and pe["high"] == 12e9 * 13
    rr = out["recommended_range"]
    assert rr["low"] == pytest.approx((pb["low"] + pe["low"]) / 2)
    assert rr["high"] == pytest.approx((pb["high"] + pe["high"]) / 2)


def test_book_from_assets_minus_liabilities():
    out = value_bank({"total_assets": 2_400_000_000_000, "total_liabilities": 2_200_000_000_000,
                      "net_income": 12_000_000_000, "bank_type": "universal_bank"})
    assert out["approaches"]["price_to_book"]["book_value"] == 200_000_000_000


def test_roe_reported():
    out = value_bank({"net_income": 20_000_000_000, "book_value": 200_000_000_000,
                      "bank_type": "universal_bank"})
    assert out["roe"] == pytest.approx(0.10)


def test_aliases_resolve():
    out = value_bank({"bank_type": "citi", "net_income": 1e9, "book_value": 10e9})
    assert out["bank_type"] == "universal_bank"


def test_no_ebitda_addback_language():
    out = value_bank({"net_income": 1e9, "book_value": 10e9})
    assert "EBITDA" in out["method"]  # explicitly a non-EBITDA method


def test_negative_income_uses_pb_only():
    out = value_bank({"bank_type": "universal_bank", "net_income": -5e9, "book_value": 100e9})
    assert "price_to_earnings" not in out["approaches"]
    assert "price_to_book" in out["approaches"]
    assert any("earnings" in w.lower() for w in out["warnings"])


def test_unknown_bank_type():
    env = invoke({"bank_type": "spaceship_bank", "net_income": 1e9, "book_value": 10e9})
    assert env["ok"] is False and env["error"]["type"] == "ValueError"


def test_invoke_ok():
    env = invoke({"bank_type": "regional_bank", "net_income": 5e8, "book_value": 4e9})
    assert env["ok"] and env["result"]["recommended_range"]["low"] > 0
