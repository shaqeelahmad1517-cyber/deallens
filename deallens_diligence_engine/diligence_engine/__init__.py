"""DealLens diligence engine — embeddable due-diligence checklist primitive."""
from .engine import (
    ENGINE_NAME, ENGINE_VERSION, DiligenceEngine, run, to_valuation_risk_flags,
)
from .models import (
    Category, Checklist, ItemState, ItemStatus, RiskRating,
)
from .primitive import MANIFEST, invoke, manifest
from .templates import available_templates, get_template

__version__ = ENGINE_VERSION
__all__ = [
    "run", "DiligenceEngine", "to_valuation_risk_flags",
    "ENGINE_NAME", "ENGINE_VERSION",
    "Checklist", "ItemState", "ItemStatus", "RiskRating", "Category",
    "invoke", "manifest", "MANIFEST",
    "available_templates", "get_template",
]
