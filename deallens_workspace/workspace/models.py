"""Workspace data model: a persistent Deal record.

A Deal ties together everything about one target — its inputs (financials,
checklist, comparables query), its latest evaluation, generated report paths,
stage, and a history log — under one id.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

STAGES = ["sourced", "screening", "diligence", "valuation", "decision", "closed"]


@dataclass
class Deal:
    id: str
    target_name: str = ""
    stage: str = "sourced"
    created_at: str = ""
    updated_at: str = ""
    # Inputs consumed by the orchestrator.
    financials: Dict[str, Any] = field(default_factory=dict)
    adjustments: List[Dict[str, Any]] = field(default_factory=list)
    checklist: Dict[str, Any] = field(default_factory=dict)
    comparables: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)   # income/weights/market overrides
    # Ownership & collaboration.
    owner_id: str = ""
    shared_with: List[Dict[str, str]] = field(default_factory=list)  # [{user_id, email, role}]
    comments: List[Dict[str, str]] = field(default_factory=list)     # [{id, user_id, author, text, at}]
    # Outputs / state.
    last_evaluation: Optional[Dict[str, Any]] = None
    reports: List[Dict[str, str]] = field(default_factory=list)  # [{format, path, at}]
    notes: str = ""
    history: List[Dict[str, str]] = field(default_factory=list)  # [{event, at}]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Deal":
        d = dict(d or {})
        known = {f for f in Deal.__dataclass_fields__}  # type: ignore[attr-defined]
        return Deal(**{k: v for k, v in d.items() if k in known})

    def summary(self) -> Dict[str, Any]:
        rec = None
        if self.last_evaluation:
            rec = self.last_evaluation.get("recommendation", {}).get("range")
        return {
            "id": self.id,
            "target_name": self.target_name,
            "stage": self.stage,
            "updated_at": self.updated_at,
            "evaluated": self.last_evaluation is not None,
            "recommended_range": rec,
            "reports": len(self.reports),
            "owner_id": self.owner_id,
            "shared_user_ids": [s.get("user_id") for s in self.shared_with],
            "comments": len(self.comments),
        }
