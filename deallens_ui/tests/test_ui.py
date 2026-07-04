"""Tests for the DealLens UI/gateway API dispatch (no socket needed)."""
import pytest

from ui.server import handle_api

U = "u-test"  # a stand-in authenticated user id


def _root(tmp_path):
    return str(tmp_path / "deals")


# ---------------------------------------------------------------------------
# Public routes (no auth)
# ---------------------------------------------------------------------------
def test_meta_lists_options(tmp_path):
    status, payload, ctype = handle_api("GET", "/api/meta", None, _root(tmp_path))
    assert status == 200
    assert "sectors" in payload and "stages" in payload
    assert "smb" in payload["business_types"]


def test_health_endpoint(tmp_path):
    status, payload, _ = handle_api("GET", "/api/health", None, _root(tmp_path))
    assert status == 200 and payload["ok"] is True
    assert payload["status"] == "healthy"


def test_manifests_endpoint(tmp_path):
    status, payload, _ = handle_api("GET", "/api/manifests", None, _root(tmp_path))
    assert status == 200 and payload["ok"] is True
    m = payload["manifests"]
    assert m["valuation_engine"]["name"] == "deallens.valuation"
    assert "orchestrator" in m and "documents" in m and "accounts" in m


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------
def test_protected_route_requires_login(tmp_path):
    status, payload, _ = handle_api("GET", "/api/deals", None, _root(tmp_path))  # no user_id
    assert status == 401
    assert payload["error"]["type"] == "Unauthorized"


def test_unknown_route_404_when_authed(tmp_path):
    status, payload, _ = handle_api("GET", "/api/nope", None, _root(tmp_path), user_id=U)
    assert status == 404
    assert payload["ok"] is False


# ---------------------------------------------------------------------------
# Authenticated CRUD
# ---------------------------------------------------------------------------
def test_create_list_get_delete(tmp_path):
    root = _root(tmp_path)
    s, env, _ = handle_api("POST", "/api/deals", {"target_name": "Acme"}, root, user_id=U)
    assert s == 200 and env["ok"]
    did = env["result"]["id"]
    s, env, _ = handle_api("GET", "/api/deals", None, root, user_id=U)
    assert any(d["id"] == did for d in env["result"]["deals"])
    s, env, _ = handle_api("GET", f"/api/deals/{did}", None, root, user_id=U)
    assert env["result"]["target_name"] == "Acme"
    s, env, _ = handle_api("DELETE", f"/api/deals/{did}", None, root, user_id=U)
    assert env["result"]["deleted"] is True


def test_update_stage(tmp_path):
    root = _root(tmp_path)
    _, env, _ = handle_api("POST", "/api/deals", {"target_name": "Acme"}, root, user_id=U)
    did = env["result"]["id"]
    _, env, _ = handle_api("PATCH", f"/api/deals/{did}", {"stage": "diligence"}, root, user_id=U)
    assert env["result"]["stage"] == "diligence"


def test_bad_create_returns_400(tmp_path):
    status, env, _ = handle_api("POST", "/api/deals",
                                {"target_name": "X", "stage": "banana"}, _root(tmp_path), user_id=U)
    assert status == 400 and env["ok"] is False


def test_deals_are_isolated_by_user(tmp_path):
    root = _root(tmp_path)
    handle_api("POST", "/api/deals", {"target_name": "Mine"}, root, user_id="u-1")
    _, env, _ = handle_api("GET", "/api/deals", None, root, user_id="u-2")
    assert env["result"]["deals"] == []          # u-2 sees none of u-1's deals


# ---------------------------------------------------------------------------
# Auth flow via the gateway
# ---------------------------------------------------------------------------
def test_banking_route(tmp_path):
    s, env, _ = handle_api("POST", "/api/banking",
                           {"bank_type": "universal_bank", "net_income": 12e9, "book_value": 205e9},
                           _root(tmp_path), user_id=U)
    assert s == 200 and env["ok"]
    assert env["result"]["recommended_range"]["low"] > 0


def test_sotp_route(tmp_path):
    s, env, _ = handle_api("POST", "/api/sotp",
                           {"segments": [{"name": "Cloud", "sector": "saas", "metric": "ebitda",
                                          "tier": "public", "earnings": 100}]},
                           _root(tmp_path), user_id=U)
    assert s == 200 and env["ok"]
    assert env["result"]["equity_range"]["mid"] > 0


def test_meta_has_bank_types(tmp_path):
    _, payload, _ = handle_api("GET", "/api/meta", None, _root(tmp_path))
    assert "universal_bank" in payload["bank_types"]


def test_auth_signup_login_me(tmp_path, monkeypatch):
    monkeypatch.setenv("DEALLENS_ACCOUNTS", str(tmp_path / "acc"))
    s, env, _ = handle_api("POST", "/api/auth/signup",
                           {"email": "a@b.com", "password": "password123", "name": "Ann"}, None)
    assert s == 200 and env["ok"]
    token = env["result"]["token"]
    # login
    s, env, _ = handle_api("POST", "/api/auth/login", {"email": "a@b.com", "password": "password123"}, None)
    assert s == 200 and env["ok"] and env["result"]["token"]
    # me (raw token passed through _token)
    s, env, _ = handle_api("GET", "/api/auth/me", {"_token": token}, None)
    assert env["result"]["user"]["email"] == "a@b.com"


def test_ingest_file_upload_base64(tmp_path):
    # a tiny .docx uploaded as base64 should extract financials
    import base64
    import io
    import zipfile
    doc = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body><w:tbl>'
           '<w:tr><w:tc><w:p><w:r><w:t>Total Revenue</w:t></w:r></w:p></w:tc>'
           '<w:tc><w:p><w:r><w:t>4,200,000</w:t></w:r></w:p></w:tc></w:tr>'
           '<w:tr><w:tc><w:p><w:r><w:t>Net Income</w:t></w:r></w:p></w:tc>'
           '<w:tc><w:p><w:r><w:t>520,000</w:t></w:r></w:p></w:tc></w:tr>'
           '</w:tbl></w:body></w:document>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", doc)
    b64 = base64.b64encode(buf.getvalue()).decode()
    s, env, _ = handle_api("POST", "/api/ingest",
                           {"filename": "stmt.docx", "content_b64": b64}, _root(tmp_path), user_id=U)
    assert s == 200 and env["ok"]
    assert env["result"]["financials"]["revenue"] == 4_200_000


def test_auth_login_bad_password(tmp_path, monkeypatch):
    monkeypatch.setenv("DEALLENS_ACCOUNTS", str(tmp_path / "acc"))
    handle_api("POST", "/api/auth/signup", {"email": "a@b.com", "password": "password123"}, None)
    s, env, _ = handle_api("POST", "/api/auth/login", {"email": "a@b.com", "password": "nope"}, None)
    assert s == 401 and env["ok"] is False


# ---------------------------------------------------------------------------
# Evaluate + report (needs sibling engines)
# ---------------------------------------------------------------------------
def test_evaluate_and_report_view(tmp_path):
    pytest.importorskip("orchestrator")
    pytest.importorskip("report")
    root = _root(tmp_path)
    deal = {
        "target_name": "Northwind",
        "financials": {"revenue": 4200000, "net_income": 520000, "owner_compensation": 180000},
        "checklist": {"business_type": "smb", "items": [],
                      "signals": {"top_customer_pct": 38, "owner_dependent": True}},
        "comparables": {"sector": "logistics", "metric": "sde"},
    }
    _, env, _ = handle_api("POST", "/api/deals", deal, root, user_id=U)
    did = env["result"]["id"]
    s, env, _ = handle_api("POST", f"/api/deals/{did}/evaluate", {}, root, user_id=U)
    assert s == 200 and env["ok"]
    assert env["result"]["recommendation"]["range"]["low"] > 0
    s, html, ctype = handle_api("GET", f"/api/deals/{did}/report", None, root, user_id=U)
    assert s == 200 and ctype == "text/html"
    assert "Northwind" in html
