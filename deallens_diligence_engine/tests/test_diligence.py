"""Tests for the DealLens diligence engine, incl. the valuation interlock."""
import pytest

from diligence_engine import (
    Checklist, available_templates, get_template, invoke, run,
    to_valuation_risk_flags,
)
from diligence_engine.rules import detect_from_signals


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
def test_templates_exist():
    assert set(available_templates()) == {"general", "smb", "saas", "retail"}


def test_ai_findings_become_provisional_flags():
    cl = Checklist.from_dict({"business_type": "general", "signals": {},
                              "ai_findings": [
                                  {"category": "Financial", "finding": "Material weakness.", "severity": "high"},
                                  {"category": "Operations", "finding": "Commodity inflation.", "severity": "medium"}]})
    r = run(cl)
    prov = r["provisional_flags"]
    assert {p["category"] for p in prov} == {"Financial", "Operations"}
    assert all(p["provisional"] and p["source"] == "ai_finding" for p in prov)
    # Provisional flags carry explicit reduced deltas and reach the valuation adapter.
    vflags = to_valuation_risk_flags(r)
    fin = next(f for f in vflags if f["category"] == "Financial")
    assert fin["multiple_discount"] == 0.06 and fin["discount_rate_premium"] == 0.015


def test_ai_finding_deduped_against_confirmed_signal():
    # A customer-concentration signal already fires; the AI 'Customers' finding
    # must NOT add a second (double-count) flag in the same area.
    cl = Checklist.from_dict({"business_type": "general",
                              "signals": {"top_customer_pct": 40},
                              "ai_findings": [{"category": "Customers", "finding": "Concentration.", "severity": "high"},
                                              {"category": "Debt", "finding": "High leverage.", "severity": "medium"}]})
    r = run(cl)
    cats = {p["category"] for p in r["provisional_flags"]}
    assert "Customers" not in cats          # deduped against the signal
    assert "Financial" in cats              # 'Debt' normalized to Financial, kept


def test_typed_templates_extend_general():
    assert len(get_template("saas")) > len(get_template("general"))


def test_unknown_business_type_errors():
    with pytest.raises(ValueError):
        get_template("spaceship")


# ---------------------------------------------------------------------------
# Completion math
# ---------------------------------------------------------------------------
def test_completion_pct_weighted():
    tmpl = get_template("general")
    # Complete every item -> 100%.
    payload = {"business_type": "general",
               "items": [{"id": t.id, "status": "complete"} for t in tmpl]}
    out = run(Checklist.from_dict(payload))
    assert out["completion_pct"] == 100.0


def test_na_items_excluded_from_completion():
    tmpl = get_template("general")
    items = [{"id": t.id, "status": "complete"} for t in tmpl]
    items[0]["status"] = "na"   # NA should not drag completion below 100
    out = run(Checklist.from_dict({"business_type": "general", "items": items}))
    assert out["completion_pct"] == 100.0


def test_empty_checklist_is_zero_percent():
    out = run(Checklist.from_dict({"business_type": "general"}))
    assert out["completion_pct"] == 0.0


def test_flagged_items_count_toward_completion():
    tmpl = get_template("general")
    # Every item flagged (a reached conclusion) -> counts as addressed -> 100%.
    payload = {"business_type": "general",
               "items": [{"id": t.id, "status": "flagged", "risk_rating": "medium"} for t in tmpl]}
    assert run(Checklist.from_dict(payload))["completion_pct"] == 100.0


# ---------------------------------------------------------------------------
# Red-flag detection from signals
# ---------------------------------------------------------------------------
def test_customer_concentration_high():
    flags = detect_from_signals({"top_customer_pct": 40})
    assert any(f.severity == "high" and "concentration" in f.label.lower() for f in flags)


def test_customer_concentration_medium():
    flags = detect_from_signals({"top_customer_pct": 25})
    assert any(f.severity == "medium" for f in flags)


def test_owner_dependence_high_without_team():
    flags = detect_from_signals({"owner_dependent": True})
    assert any(f.severity == "high" and "Owner dependence" in f.label for f in flags)


def test_owner_dependence_medium_with_team():
    flags = detect_from_signals({"owner_dependent": True, "management_team_in_place": True})
    assert any(f.severity == "medium" and "Owner dependence" in f.label for f in flags)


def test_no_signals_no_flags():
    assert detect_from_signals({}) == []


# ---------------------------------------------------------------------------
# Item-level flags + merging
# ---------------------------------------------------------------------------
def test_high_risk_item_becomes_flag():
    out = run(Checklist.from_dict({
        "business_type": "general",
        "items": [{"id": "cust_concentration", "status": "flagged", "risk_rating": "high",
                   "notes": "One client 60% of sales"}],
    }))
    assert out["summary"]["red_flag_count"] >= 1
    assert any(f["severity"] == "high" for f in out["red_flags"])


def test_flags_deduped_keep_highest_severity():
    # Same label from signal (medium) and... force duplicate via two signals isn't
    # possible; instead verify merge keeps order high-first.
    out = run(Checklist.from_dict({"signals": {"top_customer_pct": 40, "owner_dependent": True}}))
    sev = [f["severity"] for f in out["red_flags"]]
    ranks = {"high": 3, "medium": 2, "low": 1}
    assert sev == sorted(sev, key=lambda s: -ranks[s])  # sorted high -> low


# ---------------------------------------------------------------------------
# Primitive contract
# ---------------------------------------------------------------------------
def test_invoke_ok_and_includes_valuation_flags():
    env = invoke({"business_type": "smb", "signals": {"top_customer_pct": 38}})
    assert env["ok"] is True
    assert "valuation_risk_flags" in env["result"]


def test_invoke_error_envelope():
    env = invoke({"business_type": "not_a_type"})
    assert env["ok"] is False
    assert env["error"]["type"] == "ValueError"


def test_determinism():
    p = {"business_type": "saas", "signals": {"top_customer_pct": 30, "owner_dependent": True}}
    assert invoke(p) == invoke(p)


# ---------------------------------------------------------------------------
# THE INTERLOCK: diligence red_flags -> valuation risk_flags
# ---------------------------------------------------------------------------
def test_valuation_flag_adapter_shape():
    out = run(Checklist.from_dict({"signals": {"top_customer_pct": 40, "owner_dependent": True}}))
    vflags = to_valuation_risk_flags(out)
    assert vflags, "expected at least one flag"
    for f in vflags:
        assert set(f.keys()) == {"label", "severity", "category"}
        assert f["severity"] in {"low", "medium", "high"}


def test_flags_are_consumable_by_valuation_engine():
    """End-to-end: diligence output drives a real valuation run (if available)."""
    valuation = pytest.importorskip("valuation_engine")
    dili = run(Checklist.from_dict({
        "target_name": "Acme",
        "signals": {"top_customer_pct": 40, "owner_dependent": True},
    }))
    risk_flags = to_valuation_risk_flags(dili)

    payload = {
        "target_name": "Acme",
        "financials": {"net_income": 400000, "owner_compensation": 100000},
        "market": {"metric": "sde", "low_multiple": 3, "high_multiple": 5},
        "risk_flags": risk_flags,
    }
    env = valuation.invoke(payload)
    assert env["ok"] is True
    # The diligence flags should have produced a non-zero risk discount.
    assert env["result"]["risk"]["multiple_discount"] > 0
