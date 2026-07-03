"""Data models for the DealLens valuation engine.

All models are plain dataclasses that are trivially JSON-serializable via
``to_dict`` / ``from_dict`` so the engine can be embedded as a primitive and
exchange data with an external orchestrator ("spine") over JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class AdjustmentType(str, Enum):
    """Direction of a normalization adjustment."""
    ADD_BACK = "add_back"    # increases earnings (owner perks, one-off costs)
    DEDUCTION = "deduction"  # decreases earnings (one-off gains, non-recurring revenue)


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Adjustment:
    """A single normalization adjustment to reported earnings."""
    label: str
    amount: float
    type: AdjustmentType = AdjustmentType.ADD_BACK
    rationale: str = ""

    def signed_amount(self) -> float:
        return self.amount if self.type == AdjustmentType.ADD_BACK else -self.amount


@dataclass
class Financials:
    """A single normalized snapshot of the target's financials.

    Earnings are built up from components so EBITDA is auditable.
    """
    revenue: float = 0.0
    net_income: float = 0.0
    interest: float = 0.0
    taxes: float = 0.0
    depreciation: float = 0.0
    amortization: float = 0.0
    # Single working owner's total compensation, added back for SDE.
    owner_compensation: float = 0.0
    # Balance sheet (asset approach).
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    fair_value_adjustment: float = 0.0
    # Cash flow base for DCF. If None, the engine approximates it from
    # normalized EBITDA via ``fcf_conversion``.
    base_free_cash_flow: Optional[float] = None
    period_label: str = ""


@dataclass
class RiskFlag:
    """A diligence red flag that transparently adjusts valuation."""
    label: str
    severity: RiskSeverity = RiskSeverity.MEDIUM
    category: str = ""
    # Optional explicit overrides; if None, engine uses severity defaults.
    multiple_discount: Optional[float] = None      # e.g. 0.10 = -10% on market multiple
    discount_rate_premium: Optional[float] = None   # e.g. 0.02 = +2% on discount rate


@dataclass
class IncomeAssumptions:
    discount_rate: float = 0.20        # required return / WACC
    growth_rate: float = 0.05          # near-term FCF growth
    terminal_growth: float = 0.02      # perpetual growth in terminal value
    projection_years: int = 5
    long_term_growth: float = 0.02     # used by capitalization of earnings
    fcf_conversion: float = 0.65       # EBITDA -> FCF factor when base FCF absent


@dataclass
class MarketAssumptions:
    # Metric the multiples apply to: "sde", "ebitda", or "revenue".
    metric: str = "sde"
    low_multiple: float = 3.0
    high_multiple: float = 5.0


@dataclass
class Weights:
    """Relative weights for triangulating the enabled approaches."""
    income: float = 1.0
    market: float = 1.0
    asset: float = 0.5


@dataclass
class Deal:
    """Full valuation input for one target."""
    target_name: str = ""
    financials: Financials = field(default_factory=Financials)
    adjustments: List[Adjustment] = field(default_factory=list)
    risk_flags: List[RiskFlag] = field(default_factory=list)
    income: IncomeAssumptions = field(default_factory=IncomeAssumptions)
    market: MarketAssumptions = field(default_factory=MarketAssumptions)
    weights: Weights = field(default_factory=Weights)
    enabled_approaches: List[str] = field(
        default_factory=lambda: ["income", "market", "asset"]
    )

    # ---- (de)serialization -------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Deal":
        d = dict(d or {})
        fin = Financials(**(d.get("financials") or {}))
        adj = [
            Adjustment(
                label=a.get("label", ""),
                amount=float(a.get("amount", 0.0)),
                type=AdjustmentType(a.get("type", "add_back")),
                rationale=a.get("rationale", ""),
            )
            for a in (d.get("adjustments") or [])
        ]
        flags = [
            RiskFlag(
                label=r.get("label", ""),
                severity=RiskSeverity(r.get("severity", "medium")),
                category=r.get("category", ""),
                multiple_discount=r.get("multiple_discount"),
                discount_rate_premium=r.get("discount_rate_premium"),
            )
            for r in (d.get("risk_flags") or [])
        ]
        income = IncomeAssumptions(**(d.get("income") or {}))
        market = MarketAssumptions(**(d.get("market") or {}))
        weights = Weights(**(d.get("weights") or {}))
        return Deal(
            target_name=d.get("target_name", ""),
            financials=fin,
            adjustments=adj,
            risk_flags=flags,
            income=income,
            market=market,
            weights=weights,
            enabled_approaches=d.get("enabled_approaches", ["income", "market", "asset"]),
        )


@dataclass
class Range:
    low: float
    high: float

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2.0

    def to_dict(self) -> Dict[str, float]:
        return {"low": round(self.low, 2), "high": round(self.high, 2), "mid": round(self.mid, 2)}
