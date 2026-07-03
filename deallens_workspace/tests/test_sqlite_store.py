"""Tests for the SQLite store and env-driven backend selection."""
import os

import pytest

from workspace import Deal, SQLiteStore, get_store, invoke
from workspace.store import JSONFileStore


def test_sqlite_crud(tmp_path):
    db = str(tmp_path / "deals.db")
    s = SQLiteStore(db)
    d = Deal(id="acme-1", target_name="Acme", updated_at="2026-01-01")
    assert not s.exists("acme-1")
    s.save(d)
    assert s.exists("acme-1")
    assert s.load("acme-1").target_name == "Acme"
    assert any(x["id"] == "acme-1" for x in s.list())
    s.delete("acme-1")
    assert not s.exists("acme-1")


def test_sqlite_persists_across_instances(tmp_path):
    db = str(tmp_path / "deals.db")
    SQLiteStore(db).save(Deal(id="p1", target_name="Persist"))
    assert SQLiteStore(db).exists("p1")          # a fresh handle sees it


def test_sqlite_load_missing_raises(tmp_path):
    with pytest.raises(KeyError):
        SQLiteStore(str(tmp_path / "d.db")).load("nope")


def test_get_store_selection(tmp_path, monkeypatch):
    # explicit root -> JSON
    assert isinstance(get_store(str(tmp_path / "j")), JSONFileStore)
    # env DEALLENS_DB -> SQLite
    monkeypatch.setenv("DEALLENS_DB", str(tmp_path / "sel.db"))
    assert isinstance(get_store(None), SQLiteStore)
    # explicit root still wins over env (test isolation)
    assert isinstance(get_store(str(tmp_path / "j2")), JSONFileStore)


def test_invoke_uses_sqlite_when_env_set(tmp_path, monkeypatch):
    monkeypatch.setenv("DEALLENS_DB", str(tmp_path / "wf.db"))
    env = invoke({"action": "create", "deal": {"target_name": "DBDeal"}})
    assert env["ok"]
    did = env["result"]["id"]
    # visible via a direct SQLite handle at the same path
    assert SQLiteStore(str(tmp_path / "wf.db")).exists(did)
    # and via list through the primitive
    lst = invoke({"action": "list"})
    assert any(d["id"] == did for d in lst["result"]["deals"])
