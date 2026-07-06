"""Zero-dependency local web app for DealLens.

Serves a single-page UI and a small JSON API backed by the workspace primitive.
Uses only the Python standard library (http.server) so there's nothing to install.

The API dispatch lives in ``handle_api`` (a pure-ish function) so it can be unit
tested without binding a socket.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

from . import _deps  # noqa: F401  (side effect: siblings on path)

import workspace  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")


def data_root() -> str:
    """Shared store location (same as the workspace CLI uses)."""
    return os.environ.get("DEALLENS_DATA") or workspace.default_root()


def _meta() -> Dict[str, Any]:
    try:
        import comparables
        sectors = comparables.available_sectors()
    except Exception:
        sectors = ["general", "logistics", "saas", "retail"]
    try:
        import banking
        bank_types = list(banking.BANK_TYPES.keys())
    except Exception:
        bank_types = ["universal_bank", "regional_bank", "investment_bank", "insurance", "general_financial"]
    return {
        "sectors": sectors,
        "business_types": ["general", "smb", "saas", "retail"],
        "metrics": ["sde", "ebitda", "revenue"],
        "stages": list(workspace.STAGES),
        "bank_types": bank_types,
    }


def _ws(payload: Dict[str, Any], store_root: Optional[str], user_id: Optional[str] = None) -> Dict[str, Any]:
    p = dict(payload)
    # Only pin store_root when we actually have one; otherwise let the workspace
    # pick its backend (DEALLENS_DB -> SQLite, else JSON default).
    if store_root:
        p["store_root"] = store_root
    if user_id:
        p["user_id"] = user_id
    return workspace.invoke(p)


# --- auth helpers ----------------------------------------------------------
def verify_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return the public user for a valid session token, else None."""
    if not token:
        return None
    try:
        import accounts
        return accounts.verify(accounts.get_accounts_store(), token)
    except Exception:
        return None


def _handle_auth(method: str, rest, body: Dict[str, Any]) -> Tuple[int, Any, str]:
    import accounts
    store = accounts.get_accounts_store()
    if rest == ["signup"] and method == "POST":
        env = accounts.invoke({"action": "signup", "email": body.get("email", ""),
                               "password": body.get("password", ""), "name": body.get("name", "")})
        if not env["ok"]:
            return 400, env, "application/json"
        login = accounts.invoke({"action": "login", "email": body.get("email", ""),
                                 "password": body.get("password", "")})
        return (200 if login["ok"] else 400), login, "application/json"
    if rest == ["login"] and method == "POST":
        env = accounts.invoke({"action": "login", "email": body.get("email", ""),
                               "password": body.get("password", "")})
        return (200 if env["ok"] else 401), env, "application/json"
    if rest == ["logout"] and method == "POST":
        accounts.invoke({"action": "logout", "token": body.get("token", "")})
        return 200, {"ok": True, "result": {"logged_out": True}}, "application/json"
    if rest == ["me"] and method == "GET":
        user = verify_token(body.get("_token"))
        return 200, {"ok": True, "result": {"user": user}}, "application/json"
    return 404, {"ok": False, "error": {"type": "NotFound", "message": "auth route"}}, "application/json"


def _manifests() -> Dict[str, Any]:
    """Collect each primitive's manifest for service discovery."""
    out = {}
    for mod in ("valuation_engine", "diligence_engine", "comparables", "orchestrator",
                "report", "workspace", "quickscreen", "documents", "assist", "accounts",
                "integrations", "banking", "sotp"):
        try:
            out[mod] = __import__(mod).manifest()
        except Exception as exc:  # pragma: no cover
            out[mod] = {"error": str(exc)}
    return out


def _wrap(env: Dict[str, Any]) -> Tuple[int, Any, str]:
    if env.get("ok"):
        return 200, env, "application/json"
    status = 403 if env.get("error", {}).get("type") == "PermissionError" else 400
    return status, env, "application/json"


def _err(exc) -> Tuple[int, Any, str]:
    return 400, {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}, "application/json"


def handle_api(method: str, path: str, body: Optional[Dict[str, Any]],
               store_root: Optional[str] = None, user_id: Optional[str] = None) -> Tuple[int, Any, str]:
    """Route an API request. Returns (status, payload, content_type).

    ``user_id`` is resolved from the session by the HTTP layer (None if not
    authenticated). Public routes below don't need it; everything else does.
    """
    root = store_root
    if root is None and not os.environ.get("DEALLENS_DB"):
        root = data_root()
    body = body or {}
    import urllib.parse as _uparse
    raw_path, _, query = path.partition("?")
    qs = {k: v[0] for k, v in _uparse.parse_qs(query).items()}
    sub = [p for p in raw_path.split("/") if p][1:]  # strip leading 'api'

    # --- public routes ---
    if sub == ["meta"]:
        return 200, _meta(), "application/json"
    if sub == ["health"]:
        return 200, {"ok": True, "status": "healthy", "service": "deallens"}, "application/json"
    if sub == ["manifests"]:
        return 200, {"ok": True, "manifests": _manifests()}, "application/json"
    if sub and sub[0] == "auth":
        return _handle_auth(method, sub[1:], body)

    # OAuth callback is public — it authenticates via the signed 'state', not the
    # session — and returns a small page that closes the popup.
    if len(sub) == 3 and sub[0] == "integrations" and sub[2] == "callback" and method == "GET":
        try:
            import integrations
            env = integrations.invoke({"action": "callback", "provider": sub[1],
                                       "code": qs.get("code", ""), "state": qs.get("state", ""),
                                       "realm_id": qs.get("realmId", "")})
            ok = env.get("ok")
        except Exception:
            ok = False
        msg = "Connected ✓" if ok else "Connection failed"
        page = (f"<html><body style='font-family:sans-serif;text-align:center;padding-top:60px'>"
                f"<h2>{msg}</h2><p>You can close this window and return to DealLens.</p>"
                f"<script>if(window.opener){{window.opener.postMessage('deallens-connected','*');"
                f"setTimeout(()=>window.close(),900);}}else{{location.href='/';}}</script></body></html>")
        return 200, page, "text/html"

    # --- everything below requires a logged-in user ---
    if user_id is None:
        return 401, {"ok": False, "error": {"type": "Unauthorized", "message": "login required"}}, "application/json"

    if sub == ["quickscreen"] and method == "POST":
        try:
            import quickscreen
            return _wrap(quickscreen.invoke(body))
        except Exception as exc:
            return _err(exc)
    if sub == ["ingest"] and method == "POST":
        try:
            import documents
            # File upload: {filename, content_b64} -> temp file -> ingest by path.
            if body.get("content_b64") and body.get("filename"):
                import base64
                import tempfile
                ext = os.path.splitext(body["filename"])[1] or ".txt"
                raw = base64.b64decode(body["content_b64"])
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
                    tf.write(raw)
                    tmp = tf.name
                try:
                    return _wrap(documents.invoke({"path": tmp}))
                finally:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
            return _wrap(documents.invoke(body))
        except Exception as exc:
            return _err(exc)
    if sub == ["assist"] and method == "POST":
        try:
            import assist
            return _wrap(assist.invoke(body))
        except Exception as exc:
            return _err(exc)

    if sub == ["banking"] and method == "POST":
        try:
            import banking
            return _wrap(banking.invoke(body))
        except Exception as exc:
            return _err(exc)

    if sub == ["sotp"] and method == "POST":
        try:
            import sotp
            return _wrap(sotp.invoke(body))
        except Exception as exc:
            return _err(exc)

    if sub[:2] == ["diligence", "template"] and method == "GET":
        try:
            import diligence_engine
            bt = qs.get("business_type", "general")
            try:
                tmpl = diligence_engine.get_template(bt)
            except ValueError:
                bt = "general"                       # legacy/sector value -> safe default
                tmpl = diligence_engine.get_template(bt)
            items = [{"id": t.id, "category": t.category.value, "prompt": t.prompt,
                      "critical": t.critical} for t in tmpl]
            return 200, {"ok": True, "result": {"business_type": bt, "items": items}}, "application/json"
        except Exception as exc:
            return _err(exc)

    if sub == ["explain"] and method == "POST":
        try:
            import report
            kind = body.get("kind"); res = body.get("result") or {}
            if kind == "bank":
                frag = report.build_investor_bank(res)
            elif kind == "sotp":
                frag = report.build_investor_sotp(res)
            else:
                raise ValueError("kind must be 'bank' or 'sotp'")
            return 200, {"ok": True, "result": {"html": frag}}, "application/json"
        except Exception as exc:
            return _err(exc)

    # --- accounting integrations (QuickBooks / Xero / mock) ---
    if sub == ["integrations"] and method == "GET":
        try:
            import integrations
            return _wrap(integrations.invoke({"action": "list", "user_id": user_id}))
        except Exception as exc:
            return _err(exc)
    if len(sub) == 3 and sub[0] == "integrations" and method == "POST":
        provider, act = sub[1], sub[2]
        if act in ("connect", "import", "disconnect"):
            try:
                import integrations
                return _wrap(integrations.invoke({"action": act, "provider": provider,
                                                  "user_id": user_id}))
            except Exception as exc:
                return _err(exc)

    if sub == ["deals"]:
        if method == "GET":
            return _wrap(_ws({"action": "list"}, root, user_id))
        if method == "POST":
            return _wrap(_ws({"action": "create", "deal": body}, root, user_id))

    if len(sub) >= 2 and sub[0] == "deals":
        did = sub[1]
        if len(sub) == 2:
            if method == "GET":
                return _wrap(_ws({"action": "get", "id": did}, root, user_id))
            if method == "DELETE":
                return _wrap(_ws({"action": "delete", "id": did}, root, user_id))
            if method in ("PATCH", "POST"):
                return _wrap(_ws({"action": "update", "id": did, "deal": body}, root, user_id))
        if len(sub) == 3 and method == "POST":
            act = sub[2]
            if act == "evaluate":
                return _wrap(_ws({"action": "evaluate", "id": did}, root, user_id))
            if act == "comment":
                return _wrap(_ws({"action": "comment", "id": did, "text": body.get("text", ""),
                                  "author": body.get("author", "")}, root, user_id))
            if act == "share":
                # resolve email -> user via accounts, then share
                try:
                    import accounts
                    u = accounts.find_user_by_email(accounts.get_accounts_store(), body.get("email", ""))
                except Exception:
                    u = None
                if not u:
                    return 400, {"ok": False, "error": {"type": "ValueError",
                                 "message": "no DealLens user with that email"}}, "application/json"
                return _wrap(_ws({"action": "share", "id": did, "target_user_id": u["id"],
                                  "target_email": u["email"], "role": body.get("role", "viewer")}, root, user_id))
            if act == "unshare":
                return _wrap(_ws({"action": "unshare", "id": did,
                                  "target_user_id": body.get("target_user_id", "")}, root, user_id))
            if act == "report":
                return _wrap(_ws({"action": "report", "id": did,
                                  "format": body.get("format", "html")}, root, user_id))
        if len(sub) == 3 and sub[2] == "report" and method == "GET":
            opts = {"style": "plain"} if qs.get("style") == "plain" else None
            env = _ws({"action": "report", "id": did, "format": "html", "options": opts}, root, user_id)
            if not env.get("ok"):
                return 400, env, "application/json"
            with open(env["result"]["path"], "r", encoding="utf-8") as fh:
                return 200, fh.read(), "text/html"

    return 404, {"ok": False, "error": {"type": "NotFound", "message": f"{method} {path}"}}, "application/json"


class Handler(BaseHTTPRequestHandler):
    server_version = "DealLensUI/1.0"

    def log_message(self, *args):  # quiet
        pass

    def _send(self, status: int, payload: Any, content_type: str, extra_headers: Optional[Dict[str, str]] = None):
        if content_type == "application/json":
            data = json.dumps(payload).encode("utf-8")
        else:
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, path: str):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        full = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not full.startswith(STATIC_DIR) or not os.path.isfile(full):
            self._send(404, "Not found", "text/plain")
            return
        ctype = "text/html" if full.endswith(".html") else "text/plain"
        with open(full, "rb") as fh:
            self._send(200, fh.read().decode("utf-8") if ctype.startswith("text") else fh.read(), ctype)

    def _read_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return {}

    def _token(self) -> Optional[str]:
        # Prefer the session cookie; fall back to Authorization: Bearer.
        cookie = self.headers.get("Cookie", "") or ""
        for part in cookie.split(";"):
            if part.strip().startswith("deallens_session="):
                return part.strip().split("=", 1)[1]
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return None

    def _dispatch(self, method: str, body: Optional[Dict[str, Any]]):
        token = self._token()
        user = verify_token(token)
        uid = user["id"] if user else None
        # /auth/me needs the raw token to report the current user.
        if self.path.rstrip("/").endswith("/api/auth/me"):
            body = dict(body or {}, _token=token)
        status, payload, ctype = handle_api(method, self.path, body, user_id=uid)
        extra_headers = {}
        # Set/clear the session cookie on login/signup/logout.
        p = self.path.rstrip("/")
        if isinstance(payload, dict) and payload.get("ok") and p.endswith(("/auth/login", "/auth/signup")):
            tok = payload.get("result", {}).get("token")
            if tok:
                extra_headers["Set-Cookie"] = (
                    f"deallens_session={tok}; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000")
        elif p.endswith("/auth/logout"):
            extra_headers["Set-Cookie"] = "deallens_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
        self._send(status, payload, ctype, extra_headers)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._dispatch("GET", None)
        else:
            self._serve_static(self.path)

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._dispatch("POST", self._read_body())
        else:
            self._send(404, "Not found", "text/plain")

    def do_PATCH(self):
        self._dispatch("PATCH", self._read_body())

    def do_DELETE(self):
        self._dispatch("DELETE", None)


def _storage_desc() -> str:
    db = os.environ.get("DEALLENS_DB")
    return f"SQLite: {db}" if db else f"JSON files: {data_root()}"


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"DealLens running at  http://{host}:{port}")
    print(f"Storage:             {_storage_desc()}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        httpd.server_close()
