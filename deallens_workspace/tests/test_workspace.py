"""Tests for the DealLens workspace primitive (uses a temp store)."""
import pytest

from workspace import invoke
from workspace.store import JSONFileStore


def _root(tmp_path):
    return str(tmp_path / "deals")


def _deal_fields():
    return {
        "target_name": "Northwind Logistics",
        "financials": {"revenue": 4200000, "net_income": 520000, "interest": 40000,
                       "taxes": 110000, "depreciation": 90000, "amortization": 20000,
                       "owner_compensation": 180000, "total_assets": 1900000,
                       "total_liabilities": 700000},
        "adjustments": [{"label": "Owner perks", "amount": 35000, "type": "add_back"}],
        "checklist": {"business_type": "smb",
                      "items": [{"id": "cust_concentration", "status": "flagged", "risk_rating": "high"}],
                      "signals": {"top_customer_pct": 38, "owner_dependent": True, "revenue_trend": "growing"}},
        "comparables": {"sector": "logistics", "metric": "sde"},
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
def test_create_and_get(tmp_path):
    root = _root(tmp_path)
    env = invoke({"action": "create", "deal": _deal_fields(), "store_root": root})
    assert env["ok"]
    did = env["result"]["id"]
    assert did and env["result"]["stage"] == "sourced"

    got = invoke({"action": "get", "id": did, "store_root": root})
    assert got["ok"]
    assert got["result"]["target_name"] == "Northwind Logistics"


def test_list_reflects_created(tmp_path):
    root = _root(tmp_path)
    invoke({"action": "create", "deal": {"target_name": "A"}, "store_root": root})
    invoke({"action": "create", "deal": {"target_name": "B"}, "store_root": root})
    env = invoke({"action": "list", "store_root": root})
    assert env["ok"]
    assert len(env["result"]["deals"]) == 2


def test_update_changes_fields_and_stage(tmp_path):
    root = _root(tmp_path)
    did = invoke({"action": "create", "deal": {"target_name": "A"}, "store_root": root})["result"]["id"]
    env = invoke({"action": "update", "id": did, "deal": {"stage": "diligence", "notes": "hot"}, "store_root": root})
    assert env["ok"]
    assert env["result"]["stage"] == "diligence"
    assert env["result"]["notes"] == "hot"


def test_invalid_stage_rejected(tmp_path):
    root = _root(tmp_path)
    env = invoke({"action": "create", "deal": {"target_name": "A", "stage": "banana"}, "store_root": root})
    assert env["ok"] is False
    assert env["error"]["type"] == "ValueError"


def test_delete(tmp_path):
    root = _root(tmp_path)
    did = invoke({"action": "create", "deal": {"target_name": "A"}, "store_root": root})["result"]["id"]
    env = invoke({"action": "delete", "id": did, "store_root": root})
    assert env["ok"] and env["result"]["deleted"] is True
    assert invoke({"action": "get", "id": did, "store_root": root})["ok"] is False


def test_persistence_across_store_instances(tmp_path):
    root = _root(tmp_path)
    did = invoke({"action": "create", "deal": {"target_name": "Persist"}, "store_root": root})["result"]["id"]
    # A brand-new store pointed at the same root should see it.
    assert JSONFileStore(root).exists(did)


# ---------------------------------------------------------------------------
# Errors / dispatch
# ---------------------------------------------------------------------------
def test_unknown_action(tmp_path):
    env = invoke({"action": "frobnicate", "store_root": _root(tmp_path)})
    assert env["ok"] is False and env["error"]["type"] == "ValueError"


def test_action_requires_id(tmp_path):
    env = invoke({"action": "evaluate", "store_root": _root(tmp_path)})
    assert env["ok"] is False
    assert "requires 'id'" in env["error"]["message"]


def test_get_missing_deal(tmp_path):
    env = invoke({"action": "get", "id": "nope-00000000", "store_root": _root(tmp_path)})
    assert env["ok"] is False
    assert env["error"]["type"] == "KeyError"


# ---------------------------------------------------------------------------
# Evaluate + report (need sibling engines)
# ---------------------------------------------------------------------------
def test_evaluate_persists_result(tmp_path):
    pytest.importorskip("orchestrator")
    root = _root(tmp_path)
    did = invoke({"action": "create", "deal": _deal_fields(), "store_root": root})["result"]["id"]
    env = invoke({"action": "evaluate", "id": did, "store_root": root})
    assert env["ok"]
    rr = env["result"]["recommendation"]["range"]
    assert rr["low"] <= rr["mid"] <= rr["high"]
    # Stored on the deal and stage advanced.
    got = invoke({"action": "get", "id": did, "store_root": root})["result"]
    assert got["last_evaluation"] is not None
    assert got["stage"] == "valuation"


def test_report_generates_file(tmp_path):
    pytest.importorskip("orchestrator")
    pytest.importorskip("report")
    root = _root(tmp_path)
    did = invoke({"action": "create", "deal": _deal_fields(), "store_root": root})["result"]["id"]
    env = invoke({"action": "report", "id": did, "format": "html", "store_root": root})
    assert env["ok"]
    import os
    assert os.path.isfile(env["result"]["path"])
    # report auto-evaluated first since none existed
    got = invoke({"action": "get", "id": did, "store_root": root})["result"]
    assert len(got["reports"]) == 1
