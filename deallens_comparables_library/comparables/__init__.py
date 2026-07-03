"""DealLens comparables library — embeddable multiple-lookup primitive."""
from .dataset import load_dataset
from .engine import (
    ENGINE_NAME, ENGINE_VERSION, ComparablesEngine, available_sectors,
    lookup, to_valuation_market,
)
from .models import CompQuery
from .primitive import MANIFEST, invoke, manifest

__version__ = ENGINE_VERSION
__all__ = [
    "lookup", "ComparablesEngine", "to_valuation_market", "available_sectors",
    "load_dataset", "CompQuery", "ENGINE_NAME", "ENGINE_VERSION",
    "invoke", "manifest", "MANIFEST",
]
