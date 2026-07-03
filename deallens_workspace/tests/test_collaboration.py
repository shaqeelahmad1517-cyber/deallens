"""Tests for deal ownership, sharing, and comments (multi-user)."""
import pytest

from workspace import invoke


def _root(tmp_path):
    return str(tmp_path / "deals")


def _mk(root, owner, name="Deal"):
    return invoke({"action": "create", "deal": {"target_name": name}, "user_id": owner,
                   "store_root": root})["result"]["id"]


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------
def test_owner_set_on_create(tmp_path):
    root = _root(tmp_path)
    d = invoke({"action": "create", "deal": {"target_name": "A"}, "user_id": "u-1", "store_root": root})
    assert d["result"]["owner_id"] == "u-1"


def test_list_scoped_to_user(tmp_path):
    root = _root(tmp_path)
    _mk(root, "u-1", "Mine")
    _mk(root, "u-2", "Theirs")
    mine = invoke({"action": "list", "user_id": "u-1", "store_root": root})["result"]["deals"]
    assert [d["target_name"] for d in mine] == ["Mine"]


def test_other_user_cannot_get(tmp_path):
    root = _root(tmp_path)
    did = _mk(root, "u-1")
    env = invoke({"action": "get", "id": did, "user_id": "u-2", "store_root": root})
    assert env["ok"] is False
    assert env["error"]["type"] == "PermissionError"


def test_other_user_cannot_delete(tmp_path):
    root = _root(tmp_path)
    did = _mk(root, "u-1")
    env = invoke({"action": "delete", "id": did, "user_id": "u-2", "store_root": root})
    assert env["ok"] is False and env["error"]["type"] == "PermissionError"


# ---------------------------------------------------------------------------
# Sharing
# ---------------------------------------------------------------------------
def test_share_grants_view(tmp_path):
    root = _root(tmp_path)
    did = _mk(root, "u-1")
    invoke({"action": "share", "id": did, "target_user_id": "u-2", "target_email": "b@x.com",
            "role": "viewer", "user_id": "u-1", "store_root": root})
    got = invoke({"action": "get", "id": did, "user_id": "u-2", "store_root": root})
    assert got["ok"] and got["result"]["my_role"] == "viewer"
    # now appears in u-2's list
    lst = invoke({"action": "list", "user_id": "u-2", "store_root": root})["result"]["deals"]
    assert any(d["id"] == did for d in lst)


def test_viewer_cannot_edit(tmp_path):
    root = _root(tmp_path)
    did = _mk(root, "u-1")
    invoke({"action": "share", "id": did, "target_user_id": "u-2", "target_email": "b@x.com",
            "role": "viewer", "user_id": "u-1", "store_root": root})
    env = invoke({"action": "update", "id": did, "deal": {"notes": "x"}, "user_id": "u-2", "store_root": root})
    assert env["ok"] is False and env["error"]["type"] == "PermissionError"


def test_editor_can_edit_not_delete(tmp_path):
    root = _root(tmp_path)
    did = _mk(root, "u-1")
    invoke({"action": "share", "id": did, "target_user_id": "u-2", "target_email": "b@x.com",
            "role": "editor", "user_id": "u-1", "store_root": root})
    assert invoke({"action": "update", "id": did, "deal": {"notes": "x"}, "user_id": "u-2",
                   "store_root": root})["ok"]
    assert invoke({"action": "delete", "id": did, "user_id": "u-2", "store_root": root})["ok"] is False


def test_only_owner_can_share(tmp_path):
    root = _root(tmp_path)
    did = _mk(root, "u-1")
    invoke({"action": "share", "id": did, "target_user_id": "u-2", "target_email": "b@x.com",
            "role": "editor", "user_id": "u-1", "store_root": root})
    # editor u-2 tries to share onward -> denied
    env = invoke({"action": "share", "id": did, "target_user_id": "u-3", "target_email": "c@x.com",
                  "role": "viewer", "user_id": "u-2", "store_root": root})
    assert env["ok"] is False and env["error"]["type"] == "PermissionError"


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
def test_comment_by_collaborator(tmp_path):
    root = _root(tmp_path)
    did = _mk(root, "u-1")
    invoke({"action": "share", "id": did, "target_user_id": "u-2", "target_email": "b@x.com",
            "role": "viewer", "user_id": "u-1", "store_root": root})
    c = invoke({"action": "comment", "id": did, "text": "Looks risky", "user_id": "u-2",
                "author": "b@x.com", "store_root": root})
    assert c["ok"] and c["result"]["text"] == "Looks risky"
    got = invoke({"action": "get", "id": did, "user_id": "u-1", "store_root": root})["result"]
    assert len(got["comments"]) == 1


def test_stranger_cannot_comment(tmp_path):
    root = _root(tmp_path)
    did = _mk(root, "u-1")
    env = invoke({"action": "comment", "id": did, "text": "hi", "user_id": "u-9", "store_root": root})
    assert env["ok"] is False and env["error"]["type"] == "PermissionError"


def test_local_mode_no_user_id_full_access(tmp_path):
    # Back-compat: without user_id, everything is permitted (local CLI use).
    root = _root(tmp_path)
    did = invoke({"action": "create", "deal": {"target_name": "Local"}, "store_root": root})["result"]["id"]
    assert invoke({"action": "get", "id": did, "store_root": root})["ok"]
    assert invoke({"action": "update", "id": did, "deal": {"notes": "ok"}, "store_root": root})["ok"]
