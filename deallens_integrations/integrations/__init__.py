"""DealLens accounting integrations — QuickBooks / Xero OAuth + import."""
from .engine import ENGINE_NAME, ENGINE_VERSION
from .primitive import MANIFEST, invoke, manifest
from .providers import PROVIDERS, is_configured
from .store import get_connection_store

__version__ = ENGINE_VERSION
__all__ = [
    "invoke", "manifest", "MANIFEST", "ENGINE_NAME", "ENGINE_VERSION",
    "PROVIDERS", "is_configured", "get_connection_store",
]
