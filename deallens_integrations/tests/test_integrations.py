"""Tests for the integrations primitive — mock OAuth flow + provider mappers.

No real network: a fake transport captures token/exchange calls and returns
canned responses shaped like the real providers'.
"""
import pytest

from integrations import invoke, is_configured
from integrations.store import JSONConnectionStore
from integrations.client import _qb_rows, _xero_rows, _match_rows, fetch_financials
from integrations import oauth, providers


def _root(tmp_path):
    return str(tmp_path / "int")


def fake_transport(method, url, headers, data):
    # Token endpoints return a token bundle; anything else returns {}.
    if "token" in url:
        return {"access_token": "at-123", "refresh_token": "rt-456",
                "expires_in": 3600, "token_type": "Bearer", "realmId": "R1"}
    return {}


# ---------------------------------------------------------------------------
# Provider config
# ---------------------------------------------------------------------------
def test_mock_always_configured():
    assert is_configured("mock") is True


def test_real_providers_need_env(monkeypatch):
    monkeypatch.delenv("QB_CLIENT_ID", raising=False)
    monkeypatch.delenv("QB_CLIENT_SECRET", raising=False)
    assert is_configured("quickbooks") is False
    monkeypatch.setenv("QB_CLIENT_ID", "x")
    monkeypatch.setenv("QB_CLIENT_SECRET", "y")
    assert is_configured("quickbooks") is True


def test_authorize_url_contains_params():
    url = oauth.authorize_url("mock", "http://localhost/cb", "state123")
    assert "response_type=code" in url and "state=state123" in url


# ---------------------------------------------------------------------------
# Full mock OAuth + import flow via invoke()
# ---------------------------------------------------------------------------
def test_list_shows_providers(tmp_path):
    env = invoke({"action": "list", "user_id": "u-1", "store_root": _root(tmp_path)})
    assert env["ok"]
    names = {p["provider"] for p in env["result"]["providers"]}
    assert {"quickbooks", "xero", "mock"} <= names


def test_connect_callback_import_disconnect(tmp_path):
    root = _root(tmp_path)
    # connect -> get an authorize url + state
    c = invoke({"action": "connect", "provider": "mock", "user_id": "u-1", "store_root": root})
    assert c["ok"]
    state = c["result"]["state"]
    # callback -> exchanges code (fake transport), stores tokens
    cb = invoke({"action": "callback", "provider": "mock", "code": "abc", "state": state,
                 "store_root": root}, transport=fake_transport)
    assert cb["ok"] and cb["result"]["connected"] is True
    # now listed as connected
    lst = invoke({"action": "list", "user_id": "u-1", "store_root": root})["result"]["providers"]
    assert any(p["provider"] == "mock" and p["connected"] for p in lst)
    # import -> financials
    imp = invoke({"action": "import", "provider": "mock", "user_id": "u-1", "store_root": root},
                 transport=fake_transport)
    assert imp["ok"]
    assert imp["result"]["financials"]["revenue"] == 4_200_000
    # disconnect
    d = invoke({"action": "disconnect", "provider": "mock", "user_id": "u-1", "store_root": root})
    assert d["ok"] and d["result"]["connected"] is False


def test_callback_rejects_bad_state(tmp_path):
    env = invoke({"action": "callback", "provider": "mock", "code": "abc", "state": "forged",
                  "store_root": _root(tmp_path)}, transport=fake_transport)
    assert env["ok"] is False
    assert env["error"]["type"] == "PermissionError"


def test_import_without_connection_errors(tmp_path):
    env = invoke({"action": "import", "provider": "mock", "user_id": "u-x", "store_root": _root(tmp_path)})
    assert env["ok"] is False


def test_connect_unconfigured_real_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("XERO_CLIENT_ID", raising=False)
    monkeypatch.delenv("XERO_CLIENT_SECRET", raising=False)
    env = invoke({"action": "connect", "provider": "xero", "user_id": "u-1", "store_root": _root(tmp_path)})
    assert env["ok"] is False
    assert "not configured" in env["error"]["message"]


# ---------------------------------------------------------------------------
# Token obfuscation at rest
# ---------------------------------------------------------------------------
def test_tokens_obfuscated_at_rest(tmp_path, monkeypatch):
    monkeypatch.setenv("DEALLENS_SECRET", "supersecretkey")
    s = JSONConnectionStore(_root(tmp_path))
    s.put("u-1", "mock", {"access_token": "at-123", "refresh_token": "rt-456"})
    import json
    raw = open(s._path).read()
    assert "at-123" not in raw and "rt-456" not in raw   # not in the clear
    assert s.get("u-1", "mock")["access_token"] == "at-123"   # round-trips


# ---------------------------------------------------------------------------
# Provider mappers (fixture-based, shaped like the real report JSON)
# ---------------------------------------------------------------------------
def test_quickbooks_mapper():
    pl = {"Rows": {"Row": [
        {"Summary": {"ColData": [{"value": "Total Income"}, {"value": "4200000"}]}},
        {"Summary": {"ColData": [{"value": "Net Income"}, {"value": "520000"}]}},
    ]}}
    fin = _match_rows(_qb_rows(pl))
    assert fin.get("revenue") == 4_200_000
    assert fin.get("net_income") == 520_000


def test_quickbooks_group_based_mapping():
    """Real QB reports tag totals with a 'group' attribute; use it, and don't get
    fooled by detail lines (e.g. an account literally named 'Depreciation')."""
    from integrations.client import fetch_quickbooks
    pl = {"Rows": {"Row": [
        {"group": "Income", "Summary": {"ColData": [{"value": "Total Income"}, {"value": "4200000"}]}},
        {"ColData": [{"value": "Sales of Product Income"}, {"value": "999"}]},   # decoy detail
        {"group": "NetIncome", "Summary": {"ColData": [{"value": "Net Income"}, {"value": "520000"}]}},
    ]}}
    bs = {"Rows": {"Row": [
        {"group": "TotalAssets", "Summary": {"ColData": [{"value": "TOTAL ASSETS"}, {"value": "1900000"}]}},
        {"group": "TotalLiabilities", "Summary": {"ColData": [{"value": "Total Liabilities"}, {"value": "700000"}]}},
    ]}}
    fin = fetch_quickbooks({"realm_id": "1"},
                           transport=lambda m, u, h, d: pl if "ProfitAndLoss" in u else bs)
    assert fin["revenue"] == 4_200_000
    assert fin["net_income"] == 520_000
    assert fin["total_assets"] == 1_900_000
    assert fin["total_liabilities"] == 700_000        # assets > liabilities, sane


def test_xero_mapper():
    rep = {"Reports": [{"Rows": [
        {"Rows": [{"Cells": [{"Value": "Total Income"}, {"Value": "4200000"}]},
                  {"Cells": [{"Value": "Net Profit"}, {"Value": "520000"}]}]},
    ]}]}
    fin = _match_rows(_xero_rows(rep))
    assert fin.get("revenue") == 4_200_000
    assert fin.get("net_income") == 520_000
