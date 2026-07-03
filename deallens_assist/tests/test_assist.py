"""Tests for the DealLens assist primitive."""
import pytest

from assist import draft_narrative, invoke, suggest_adjustments

INGESTION = {
    "financials": {"revenue": 4200000, "net_income": 520000, "owner_compensation": 180000},
    "adjustment_candidates": [
        {"label": "Owner's personal vehicle", "amount": 35000, "type": "add_back"},
        {"label": "One-time legal settlement", "amount": 60000, "type": "add_back"},
        {"label": "Mystery expense", "amount": 5000, "type": "add_back"},
    ],
}

ORCH_RESULT = {
    "target_name": "Northwind Logistics",
    "recommendation": {"range": {"low": 1921022, "high": 2618932, "mid": 2269977}},
    "diligence": {"completion_pct": 25.9, "red_flags": [
        {"label": "Customer concentration 38%", "severity": "high", "category": "Customers"},
        {"label": "Owner dependence", "severity": "high", "category": "People"}]},
    "comparables": {"sector_matched": "logistics", "base_band": [2.0, 3.0],
                    "modifiers": {"size_factor": 1.0, "growth_factor": 1.07}},
    "valuation": {
        "target_name": "Northwind Logistics",
        "normalization": {"normalized_ebitda": 830000, "sde": 1010000},
        "risk": {"multiple_discount": 0.24, "flags": []},
        "approaches": {"income": {"dcf": {"value": 2589041}, "capitalization": {"value": 3458333}},
                       "market": {"metric": "sde", "low_multiple": 2.49, "high_multiple": 4.15},
                       "asset": {"value": 1250000}},
        "recommended_range": {"low": 1921022, "high": 2618932, "mid": 2269977},
    },
}

VAL_ONLY = ORCH_RESULT["valuation"]


# ---------------------------------------------------------------------------
# Adjustments
# ---------------------------------------------------------------------------
def test_suggest_adjustments_rationale_and_confidence():
    out = suggest_adjustments(INGESTION["adjustment_candidates"], INGESTION["financials"])
    by_label = {s["label"]: s for s in out["suggestions"]}
    assert by_label["Owner's personal vehicle"]["confidence"] == "high"
    assert by_label["One-time legal settlement"]["confidence"] == "high"
    assert by_label["Mystery expense"]["confidence"] == "low"
    assert all(s["status"] == "suggested" for s in out["suggestions"])


def test_owner_comp_note():
    out = suggest_adjustments([], {"owner_compensation": 180000})
    assert any("Owner compensation" in n for n in out["notes"])


def test_dedup_candidates():
    cands = [{"label": "Owner car", "amount": 1}, {"label": "owner car", "amount": 2}]
    out = suggest_adjustments(cands, {})
    assert out["count"] == 1


def test_invoke_suggest_from_ingestion():
    env = invoke({"action": "suggest_adjustments", "ingestion": INGESTION})
    assert env["ok"]
    assert env["result"]["count"] == 3


# ---------------------------------------------------------------------------
# Narrative
# ---------------------------------------------------------------------------
def test_narrative_from_orchestrator():
    out = draft_narrative(ORCH_RESULT)
    n = out["narrative"]
    assert "Northwind Logistics" in n
    assert "$1,921,022" in n and "$2,618,932" in n
    assert "logistics" in n
    assert "Customer concentration" in n
    assert "24%" in n


def test_narrative_from_valuation_only():
    out = draft_narrative(VAL_ONLY)
    assert "Northwind Logistics" in out["narrative"]
    # no comparables sentence when valuation-only
    assert "sector" not in out["narrative"].lower()


def test_narrative_text_format():
    out = draft_narrative(ORCH_RESULT, {"format": "text"})
    assert not out["narrative"].startswith("##")


def test_narrative_rejects_garbage():
    env = invoke({"action": "draft_narrative", "result": {"nope": 1}})
    assert env["ok"] is False
    assert env["error"]["type"] == "ValueError"


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
def test_unknown_action():
    env = invoke({"action": "sing"})
    assert env["ok"] is False


def test_determinism():
    a = invoke({"action": "draft_narrative", "result": ORCH_RESULT})
    b = invoke({"action": "draft_narrative", "result": ORCH_RESULT})
    assert a == b
