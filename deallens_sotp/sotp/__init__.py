"""DealLens sum-of-the-parts — value conglomerates by segment, then combine."""
from .engine import ENGINE_NAME, ENGINE_VERSION, value_sotp
from .primitive import MANIFEST, invoke, manifest

__version__ = ENGINE_VERSION
__all__ = ["value_sotp", "invoke", "manifest", "MANIFEST", "ENGINE_NAME", "ENGINE_VERSION"]
