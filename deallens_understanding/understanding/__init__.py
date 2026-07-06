"""DealLens understanding — read real-world documents into financials + findings."""
from . import keywords, llm
from .engine import ENGINE_NAME, ENGINE_VERSION, understand
from .primitive import MANIFEST, invoke, manifest

__version__ = ENGINE_VERSION
__all__ = [
    "understand", "invoke", "manifest", "MANIFEST",
    "ENGINE_NAME", "ENGINE_VERSION", "llm", "keywords",
]
