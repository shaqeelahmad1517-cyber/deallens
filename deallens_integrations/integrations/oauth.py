"""OAuth 2.0 authorization-code flow (stdlib only, injectable transport).

The ``transport`` is a callable (method, url, headers, data) -> dict. Production
uses ``urllib_transport``; tests inject a fake so no real network is touched.
"""
from __future__ import annotations

import base64
import json
import secrets
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional

from . import providers

Transport = Callable[[str, str, Dict[str, str], Optional[bytes]], Dict[str, Any]]


def urllib_transport(method: str, url: str, headers: Dict[str, str],
                     data: Optional[bytes]) -> Dict[str, Any]:  # pragma: no cover - network
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def make_state() -> str:
    return secrets.token_urlsafe(24)


def authorize_url(provider_key: str, redirect_uri: str, state: str) -> str:
    p = providers.get_provider(provider_key)
    params = {
        "client_id": providers.client_id(provider_key) or "MOCK_ID",
        "response_type": "code",
        "scope": p["scope"],
        "redirect_uri": redirect_uri,
        "state": state,
    }
    if provider_key == "quickbooks":
        # Intuit requires the accounting scope and returns a realmId on callback.
        pass
    return f"{p['authorize_url']}?{urllib.parse.urlencode(params)}"


def _basic_auth(provider_key: str) -> str:
    cid = providers.client_id(provider_key) or "MOCK_ID"
    sec = providers.client_secret(provider_key) or "MOCK_SECRET"
    return base64.b64encode(f"{cid}:{sec}".encode()).decode()


def exchange_code(provider_key: str, code: str, redirect_uri: str,
                  transport: Transport = urllib_transport) -> Dict[str, Any]:
    """Swap an authorization code for access/refresh tokens."""
    if provider_key == "mock":   # fully offline demo provider
        return _normalize_tokens({"access_token": "mock-at", "refresh_token": "mock-rt",
                                  "expires_in": 3600, "realmId": "mock-realm"})
    p = providers.get_provider(provider_key)
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }).encode()
    headers = {
        "Authorization": f"Basic {_basic_auth(provider_key)}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    tokens = transport("POST", p["token_url"], headers, body)
    return _normalize_tokens(tokens)


def refresh_tokens(provider_key: str, refresh_token: str,
                   transport: Transport = urllib_transport) -> Dict[str, Any]:
    if provider_key == "mock":
        return _normalize_tokens({"access_token": "mock-at2", "refresh_token": "mock-rt2"})
    p = providers.get_provider(provider_key)
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()
    headers = {
        "Authorization": f"Basic {_basic_auth(provider_key)}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    return _normalize_tokens(transport("POST", p["token_url"], headers, body))


def _normalize_tokens(t: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "access_token": t.get("access_token", ""),
        "refresh_token": t.get("refresh_token", ""),
        "expires_in": t.get("expires_in"),
        "token_type": t.get("token_type", "Bearer"),
        # QuickBooks returns realmId; Xero tenant is fetched separately.
        "realm_id": t.get("realmId") or t.get("realm_id", ""),
    }
