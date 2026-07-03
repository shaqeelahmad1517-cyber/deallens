"""Data models for the DealLens comparables library."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CompQuery:
    """A request for a multiple band."""
    sector: str = "general"
    metric: str = "sde"               # sde | ebitda | revenue
    size_ebitda: Optional[float] = None   # used to gauge size premium/discount
    growth: str = ""                  # high | growing | flat | declining (or "")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CompQuery":
        d = dict(d or {})
        size = d.get("size_ebitda")
        return CompQuery(
            sector=d.get("sector", "general") or "general",
            metric=(d.get("metric", "sde") or "sde").lower(),
            size_ebitda=float(size) if size is not None else None,
            growth=(d.get("growth", "") or "").lower(),
        )
