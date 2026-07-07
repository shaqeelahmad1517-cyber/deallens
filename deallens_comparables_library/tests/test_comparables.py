"""Tests for the DealLens comparables library, incl. valuation interlock."""
import pytest

from comparables import (
    CompQuery, available_sectors, invoke, lookup, to_valuation_market,
)


# ---------------------------------------------------------------------------
# Dataset / sectors
# ---------------------------------------------------------------------------
def test_sectors_present():
    s = available_sectors()
    assert "general" in s and "saas" in s and "logistics" in s


def test_alias_resolves():
    out = lookup(CompQuery(sector="trucking", metric="sde"))
    assert out["sector_matched"] == "logistics"


def test_unknown_sector_errors():
    with pytest.raises(ValueError):
        lookup(CompQuery(sector="time_travel"))


def test_new_sectors_present():
    s = available_sectors()
    for k in ("consumer_staples", "beverages", "energy", "utilities", "pharmaceuticals",
              "real_estate", "telecom", "media_entertainment"):
        assert k in s


def test_packaged_food_maps_to_consumer_staples():
    from comparables import resolve_sector, sector_alias_map
    assert resolve_sector("packaged food") == "consumer_staples"
    assert resolve_sector("Food") == "consumer_staples"
    assert resolve_sector("consumer staples") == "consumer_staples"
    assert resolve_sector("oil and gas") == "energy"
    assert resolve_sector("nonsense-xyz") is None
    m = sector_alias_map()
    assert m["reit"] == "real_estate" and m["pharma"] == "pharmaceuticals"


def test_consumer_staples_public_band_is_richer_than_manufacturing():
    cs = lookup(CompQuery(sector="consumer_staples", metric="ebitda", tier="public"))
    mf = lookup(CompQuery(sector="manufacturing", metric="ebitda", tier="public"))
    # A branded-food public multiple should exceed a generic manufacturer's.
    assert cs["low_multiple"] > mf["low_multiple"]


def test_unknown_metric_errors():
    with pytest.raises(ValueError):
        lookup(CompQuery(sector="general", metric="vibes"))


# ---------------------------------------------------------------------------
# Base band & modifiers
# ---------------------------------------------------------------------------
def test_base_band_unmodified_when_no_size_or_growth():
    out = lookup(CompQuery(sector="general", metric="sde"))
    assert out["base_band"] == [2.0, 3.0]
    assert out["low_multiple"] == 2.0 and out["high_multiple"] == 3.0


def test_size_premium_applies():
    small = lookup(CompQuery(sector="general", metric="ebitda", size_ebitda=100_000))
    big = lookup(CompQuery(sector="general", metric="ebitda", size_ebitda=8_000_000))
    assert big["low_multiple"] > small["low_multiple"]
    assert small["modifiers"]["size_factor"] == 0.85
    assert big["modifiers"]["size_factor"] == 1.30


def test_growth_factor_applies():
    declining = lookup(CompQuery(sector="general", metric="sde", growth="declining"))
    high = lookup(CompQuery(sector="general", metric="sde", growth="high"))
    assert declining["high_multiple"] < 3.0 < high["high_multiple"]


def test_combined_factor_is_product():
    out = lookup(CompQuery(sector="general", metric="ebitda",
                           size_ebitda=2_000_000, growth="growing"))
    m = out["modifiers"]
    assert m["combined_factor"] == pytest.approx(m["size_factor"] * m["growth_factor"])


def test_unknown_growth_errors():
    with pytest.raises(ValueError):
        lookup(CompQuery(sector="general", growth="explosive"))


# ---------------------------------------------------------------------------
# Primitive contract
# ---------------------------------------------------------------------------
def test_invoke_ok():
    env = invoke({"sector": "saas", "metric": "revenue"})
    assert env["ok"] is True
    assert env["result"]["sector_matched"] == "saas"


def test_invoke_error_envelope():
    env = invoke({"sector": "nope"})
    assert env["ok"] is False
    assert env["error"]["type"] == "ValueError"


def test_determinism():
    p = {"sector": "manufacturing", "metric": "ebitda", "size_ebitda": 1_500_000, "growth": "growing"}
    assert invoke(p) == invoke(p)


# ---------------------------------------------------------------------------
# THE INTERLOCK: comparables -> valuation market block
# ---------------------------------------------------------------------------
def test_valuation_market_adapter_shape():
    out = lookup(CompQuery(sector="logistics", metric="sde"))
    market = to_valuation_market(out)
    assert set(market.keys()) == {"metric", "low_multiple", "high_multiple"}


def test_public_tier_uses_higher_bands():
    smb = lookup(CompQuery(sector="logistics", metric="ebitda"))
    pub = lookup(CompQuery(sector="logistics", metric="ebitda", tier="public"))
    assert pub["base_band"] == [10.0, 16.0]
    assert pub["low_multiple"] > smb["high_multiple"]   # public >> smb
    assert pub["tier"] == "public"


def test_public_tier_skips_size_discount():
    # A large public firm shouldn't get the small-size discount.
    pub = lookup(CompQuery(sector="logistics", metric="ebitda", tier="public", size_ebitda=100_000))
    assert pub["modifiers"]["size_factor"] == 1.0


def test_public_tier_requires_public_band():
    with pytest.raises(ValueError):
        lookup(CompQuery(sector="logistics", metric="sde", tier="public"))  # no sde_public


def test_unknown_tier_errors():
    with pytest.raises(ValueError):
        lookup(CompQuery(sector="logistics", metric="ebitda", tier="mega"))


def test_market_feeds_valuation_engine():
    valuation = pytest.importorskip("valuation_engine")
    comps = lookup(CompQuery(sector="logistics", metric="sde",
                             size_ebitda=830_000, growth="growing"))
    market = to_valuation_market(comps)
    payload = {
        "financials": {"net_income": 400_000, "owner_compensation": 120_000},
        "market": market,                # <-- comps drive the multiples
        "enabled_approaches": ["market"],
        "weights": {"income": 0, "market": 1, "asset": 0},
    }
    env = valuation.invoke(payload)
    assert env["ok"] is True
    mkt = env["result"]["approaches"]["market"]
    assert mkt["low_multiple"] == pytest.approx(market["low_multiple"], rel=1e-6)
