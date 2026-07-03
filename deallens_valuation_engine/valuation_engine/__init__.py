"""DealLens valuation engine — embeddable, deterministic valuation primitive."""
from .engine import ENGINE_NAME, ENGINE_VERSION, ValuationEngine, run
from .models import (
    Adjustment, AdjustmentType, Deal, Financials, IncomeAssumptions,
    MarketAssumptions, Range, RiskFlag, RiskSeverity, Weights,
)
from .primitive import MANIFEST, invoke, manifest

__version__ = ENGINE_VERSION
__all__ = [
    "run", "ValuationEngine", "ENGINE_NAME", "ENGINE_VERSION",
    "Deal", "Financials", "Adjustment", "AdjustmentType", "RiskFlag",
    "RiskSeverity", "IncomeAssumptions", "MarketAssumptions", "Weights", "Range",
    "invoke", "manifest", "MANIFEST",
]
