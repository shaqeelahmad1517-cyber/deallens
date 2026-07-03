"""DealLens accounts — users and sessions with stdlib password hashing."""
from .engine import (
    ENGINE_NAME, ENGINE_VERSION, find_user_by_email, login, logout, signup, verify,
)
from .primitive import MANIFEST, invoke, manifest
from .store import get_accounts_store

__version__ = ENGINE_VERSION
__all__ = [
    "signup", "login", "logout", "verify", "find_user_by_email", "get_accounts_store",
    "invoke", "manifest", "MANIFEST", "ENGINE_NAME", "ENGINE_VERSION",
]
