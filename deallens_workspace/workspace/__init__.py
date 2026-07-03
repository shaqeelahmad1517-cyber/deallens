"""DealLens workspace — persistent deal lifecycle over the DealLens primitives."""
from .engine import ENGINE_NAME, ENGINE_VERSION
from .models import STAGES, Deal
from .primitive import MANIFEST, invoke, manifest
from .store import JSONFileStore, SQLiteStore, default_root, get_store

__version__ = ENGINE_VERSION
__all__ = [
    "invoke", "manifest", "MANIFEST", "ENGINE_NAME", "ENGINE_VERSION",
    "Deal", "STAGES", "JSONFileStore", "SQLiteStore", "get_store", "default_root",
]
