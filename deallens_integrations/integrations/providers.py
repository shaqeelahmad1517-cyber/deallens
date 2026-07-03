"""Accounting-provider configurations (QuickBooks, Xero) + a mock for testing.

Credentials come from environment variables (never hard-coded). A provider is
"configured" only when its client id/secret env vars are set — otherwise the
gateway reports it as unavailable and the mock can be used for demos/tests.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "quickbooks": {
        "name": "QuickBooks",
        "authorize_url": "https://appcenter.intuit.com/connect/oauth2",
        "token_url": "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
        "scope": "com.intuit.quickbooks.accounting",
        # Sandbox base is https://sandbox-quickbooks.api.intuit.com
        "api_base_env": "QB_API_BASE",
        "api_base_default": "https://sandbox-quickbooks.api.intuit.com",
        "client_id_env": "QB_CLIENT_ID",
        "client_secret_env": "QB_CLIENT_SECRET",
    },
    "xero": {
        "name": "Xero",
        "authorize_url": "https://login.xero.com/identity/connect/authorize",
        "token_url": "https://identity.xero.com/connect/token",
        "scope": "accounting.reports.read accounting.settings.read offline_access",
        "api_base_env": "XERO_API_BASE",
        "api_base_default": "https://api.xero.com",
        "client_id_env": "XERO_CLIENT_ID",
        "client_secret_env": "XERO_CLIENT_SECRET",
    },
    # A fully local provider so the whole flow is testable/demoable with no
    # accounts. Its "OAuth" and "API" are simulated by the mock transport.
    "mock": {
        "name": "Demo (mock)",
        "authorize_url": "https://mock.local/authorize",
        "token_url": "https://mock.local/token",
        "scope": "read",
        "api_base_env": "MOCK_API_BASE",
        "api_base_default": "https://mock.local",
        "client_id_env": "MOCK_CLIENT_ID",
        "client_secret_env": "MOCK_CLIENT_SECRET",
    },
}


def get_provider(key: str) -> Dict[str, Any]:
    key = (key or "").lower()
    if key not in PROVIDERS:
        raise ValueError(f"unknown provider {key!r}; use one of {list(PROVIDERS)}")
    return PROVIDERS[key]


def client_id(key: str) -> Optional[str]:
    return os.environ.get(get_provider(key)["client_id_env"])


def client_secret(key: str) -> Optional[str]:
    return os.environ.get(get_provider(key)["client_secret_env"])


def api_base(key: str) -> str:
    p = get_provider(key)
    return os.environ.get(p["api_base_env"], p["api_base_default"])


def is_configured(key: str) -> bool:
    """The mock is always 'configured'; real providers need their env creds."""
    if key == "mock":
        return True
    return bool(client_id(key) and client_secret(key))


def redirect_uri(key: str, base_url: Optional[str] = None) -> str:
    base = (base_url or os.environ.get("DEALLENS_BASE_URL", "http://localhost:8765")).rstrip("/")
    return f"{base}/api/integrations/{key}/callback"
