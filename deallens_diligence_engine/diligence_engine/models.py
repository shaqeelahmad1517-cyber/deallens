"""Data models for the DealLens diligence checklist engine.

All models are plain dataclasses, JSON-serializable, so the engine can run as
an embeddable primitive exchanging JSON with an orchestrator ("spine").
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Category(str, Enum):
    FINANCIAL = "Financial"
    COMMERCIAL = "Commercial"
    CUSTOMERS = "Customers"
    OPERATIONS = "Operations"
    PEOPLE = "People"
    LEGAL = "Legal"
    TAX = "Tax"
    DEAL = "Deal"


class ItemStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FLAGGED = "flagged"      # reviewed and a concern was found
    NA = "na"               # not applicable to this target


class RiskRating(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NONE = "none"


# Numeric weight for rolling up risk ratings.
RISK_SCORE = {RiskRating.NONE: 0, RiskRating.LOW: 1, RiskRating.MEDIUM: 2, RiskRating.HIGH: 3}


@dataclass
class ChecklistItemTemplate:
    """A question/requirement in a diligence template."""
    id: str
    category: Category
    prompt: str
    weight: float = 1.0          # importance for completion weighting
    critical: bool = False       # if flagged/high, always becomes a red flag
    concern: str = ""            # shared key to dedupe against signal-based flags


@dataclass
class ItemState:
    """The reviewer's state for one checklist item."""
    id: str
    status: ItemStatus = ItemStatus.NOT_STARTED
    risk_rating: RiskRating = RiskRating.NONE
    notes: str = ""
    evidence: List[str] = field(default_factory=list)   # document refs/ids


@dataclass
class Checklist:
    """Full diligence input for one target."""
    target_name: str = ""
    business_type: str = "general"            # general | smb | saas | retail
    items: List[ItemState] = field(default_factory=list)
    # Structured facts that drive automatic red-flag detection.
    signals: Dict[str, Any] = field(default_factory=dict)
    # AI-extracted narrative findings (category/finding/severity); applied to the
    # valuation at a provisional (reduced) weight until a human confirms them.
    ai_findings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Checklist":
        d = dict(d or {})
        items = [
            ItemState(
                id=i.get("id", ""),
                status=ItemStatus(i.get("status", "not_started")),
                risk_rating=RiskRating(i.get("risk_rating", "none")),
                notes=i.get("notes", ""),
                evidence=list(i.get("evidence", []) or []),
            )
            for i in (d.get("items") or [])
        ]
        return Checklist(
            target_name=d.get("target_name", ""),
            business_type=d.get("business_type", "general"),
            items=items,
            signals=dict(d.get("signals") or {}),
            ai_findings=list(d.get("ai_findings") or []),
        )
