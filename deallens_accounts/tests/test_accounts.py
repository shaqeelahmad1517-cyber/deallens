"""Tests for the DealLens accounts primitive."""
import pytest

from accounts import invoke
from accounts.store import JSONAccountsStore, get_accounts_store
import accounts.engine as engine


def store(tmp_path):
    return JSONAccountsStore(str(tmp_path / "acc"))


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------
def test_signup_returns_public_user_only(tmp_path):
    s = store(tmp_path)
    u = engine.signup(s, "a@b.com", "password123", "Ann")
    assert u["email"] == "a@b.com" and u["name"] == "Ann" and u["id"]
    assert "pw_hash" not in u and "salt" not in u


def test_signup_rejects_bad_email(tmp_path):
    with pytest.raises(ValueError):
        engine.signup(store(tmp_path), "not-an-email", "password123")


def test_signup_rejects_short_password(tmp_path):
    with pytest.raises(ValueError):
        engine.signup(store(tmp_path), "a@b.com", "short")


def test_signup_duplicate_email(tmp_path):
    s = store(tmp_path)
    engine.signup(s, "a@b.com", "password123")
    with pytest.raises(ValueError):
        engine.signup(s, "A@B.com", "password123")   # case-insensitive


# ---------------------------------------------------------------------------
# Login / sessions
# ---------------------------------------------------------------------------
def test_login_success_issues_session(tmp_path):
    s = store(tmp_path)
    engine.signup(s, "a@b.com", "password123")
    res = engine.login(s, "a@b.com", "password123")
    assert res["token"]
    assert res["user"]["email"] == "a@b.com"


def test_login_wrong_password(tmp_path):
    s = store(tmp_path)
    engine.signup(s, "a@b.com", "password123")
    with pytest.raises(ValueError):
        engine.login(s, "a@b.com", "wrongpass1")


def test_login_unknown_user(tmp_path):
    with pytest.raises(ValueError):
        engine.login(store(tmp_path), "ghost@b.com", "password123")


def test_verify_valid_and_after_logout(tmp_path):
    s = store(tmp_path)
    engine.signup(s, "a@b.com", "password123")
    token = engine.login(s, "a@b.com", "password123")["token"]
    assert engine.verify(s, token)["email"] == "a@b.com"
    engine.logout(s, token)
    assert engine.verify(s, token) is None


def test_verify_bad_token(tmp_path):
    assert engine.verify(store(tmp_path), "garbage") is None
    assert engine.verify(store(tmp_path), "") is None


def test_password_not_recoverable_from_store(tmp_path):
    s = store(tmp_path)
    engine.signup(s, "a@b.com", "password123")
    raw = s.get_user_by_email("a@b.com")
    assert raw["pw_hash"] != "password123"
    assert "password123" not in str(raw)


# ---------------------------------------------------------------------------
# Primitive contract
# ---------------------------------------------------------------------------
def test_invoke_signup_login_verify(tmp_path):
    root = str(tmp_path / "acc")
    assert invoke({"action": "signup", "email": "a@b.com", "password": "password123",
                   "store_root": root})["ok"]
    login = invoke({"action": "login", "email": "a@b.com", "password": "password123",
                    "store_root": root})
    assert login["ok"]
    token = login["result"]["token"]
    v = invoke({"action": "verify", "token": token, "store_root": root})
    assert v["result"]["valid"] is True


def test_invoke_login_failure_envelope(tmp_path):
    root = str(tmp_path / "acc")
    invoke({"action": "signup", "email": "a@b.com", "password": "password123", "store_root": root})
    env = invoke({"action": "login", "email": "a@b.com", "password": "nope", "store_root": root})
    assert env["ok"] is False
    assert env["error"]["type"] == "ValueError"


def test_sqlite_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("DEALLENS_DB", str(tmp_path / "acc.db"))
    from accounts.store import SQLiteAccountsStore
    assert isinstance(get_accounts_store(None), SQLiteAccountsStore)
    assert invoke({"action": "signup", "email": "a@b.com", "password": "password123"})["ok"]
    assert invoke({"action": "login", "email": "a@b.com", "password": "password123"})["ok"]
