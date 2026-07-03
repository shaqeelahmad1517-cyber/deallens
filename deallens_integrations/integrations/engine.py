"""Integrations engine: connect -> callback -> import for accounting providers."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from . import client, oauth, providers
from .store import get_connection_store

ENGINE_NAME = "deallens.integrations"
ENGINE_VERSION = "1.0.0"


def list_providers(store, user_id: str) -> Dict[str, Any]:
    connected = set(store.list_for_user(user_id)) if user_id else set()
    out = []
    for key, p in providers.PROVIDERS.items():
        out.append({
            "provider": key,
            "name": p["name"],
            "configured": providers.is_configured(key),
            "connected": key in connected,
        })
    return {"providers": out}


def start_connect(store, user_id: str, provider_key: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    providers.get_provider(provider_key)
    if not providers.is_configured(provider_key):
        raise ValueError(f"{provider_key} is not configured on the server "
                         f"(set its client id/secret env vars)")
    state = oauth.make_state()
    store.put_state(state, user_id, provider_key)
    url = oauth.authorize_url(provider_key, providers.redirect_uri(provider_key, base_url), state)
    return {"authorize_url": url, "state": state}


def handle_callback(store, provider_key: str, code: str, state: str,
                    realm_id: str = "", base_url: Optional[str] = None,
                    transport: Callable = oauth.urllib_transport) -> Dict[str, Any]:
    saved = store.pop_state(state)
    if not saved or saved.get("provider") != provider_key:
        raise PermissionError("invalid or expired OAuth state")
    user_id = saved["user_id"]
    tokens = oauth.exchange_code(provider_key, code, providers.redirect_uri(provider_key, base_url), transport)
    if realm_id and not tokens.get("realm_id"):
        tokens["realm_id"] = realm_id
    store.put(user_id, provider_key, tokens)
    return {"user_id": user_id, "provider": provider_key, "connected": True}


def import_financials(store, user_id: str, provider_key: str,
                      transport: Callable = oauth.urllib_transport) -> Dict[str, Any]:
    conn = store.get(user_id, provider_key)
    if not conn:
        raise ValueError(f"{provider_key} is not connected for this user")
    financials = client.fetch_financials(provider_key, conn, transport)
    return {
        "provider": provider_key,
        "financials": financials,
        "source": f"{providers.get_provider(provider_key)['name']} import",
        "disclaimer": "Imported figures — review before use; report layouts vary by account.",
    }


def disconnect(store, user_id: str, provider_key: str) -> Dict[str, Any]:
    store.delete(user_id, provider_key)
    return {"provider": provider_key, "connected": False}
