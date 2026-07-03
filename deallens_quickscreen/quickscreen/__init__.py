"""DealLens quick-screen — fast indicative valuation primitive."""
from .engine import ENGINE_NAME, ENGINE_VERSION, run
from .primitive import MANIFEST, invoke, manifest

__version__ = ENGINE_VERSION
__all__ = ["run", "invoke", "manifest", "MANIFEST", "ENGINE_NAME", "ENGINE_VERSION"]
