"""DealLens comparables engine — deterministic multiple lookup.

Resolves a sector to a base multiple band for the chosen metric, then applies
transparent size and growth modifiers. Emits a band ready to drop into the
valuation engine's ``market`` block.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .dataset import load_dataset
from .models import CompQuery

ENGINE_NAME = "deallens.comparables"
ENGINE_VERSION = "1.0.0"

_VALID_METRICS = ("sde", "ebitda", "revenue")

# Size bands keyed on EBITDA: larger businesses earn a multiple premium.
_SIZE_BANDS: List[Tuple[float, float, str]] = [
    (250_000, 0.85, "micro (<$250k EBITDA)"),
    (1_000_000, 1.00, "small ($250k-$1M EBITDA)"),
    (5_000_000, 1.15, "lower-mid ($1M-$5M EBITDA)"),
    (float("inf"), 1.30, "mid-market (>$5M EBITDA)"),
]

_GROWTH_FACTORS = {
    "high": 1.15,
    "growing": 1.07,
    "flat": 1.00,
    "declining": 0.85,
    "": 1.00,
}


def _build_index(dataset: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for rec in dataset:
        index[rec["sector"].lower()] = rec
        for alias in rec.get("aliases", []):
            index[alias.lower()] = rec
    return index


def available_sectors(dataset: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    ds = dataset if dataset is not None else load_dataset()
    return sorted(r["sector"] for r in ds)


def _size_factor(size_ebitda: Optional[float]) -> Tuple[float, str]:
    if size_ebitda is None:
        return 1.0, "unspecified"
    for threshold, factor, label in _SIZE_BANDS:
        if size_ebitda < threshold:
            return factor, label
    return 1.0, "unspecified"


def lookup(query: CompQuery, dataset: Optional[List[Dict[str, Any]]] = None) -> Dict[str, object]:
    if query.metric not in _VALID_METRICS:
        raise ValueError(f"unknown metric {query.metric!r}; use one of {_VALID_METRICS}")

    ds = dataset if dataset is not None else load_dataset()
    index = _build_index(ds)
    key = (query.sector or "general").lower()
    if key not in index:
        raise ValueError(
            f"unknown sector {query.sector!r}; available: {available_sectors(ds)}"
        )
    rec = index[key]

    band = rec.get(query.metric)
    if not band:
        raise ValueError(
            f"sector {rec['sector']!r} has no {query.metric!r} multiple; "
            f"try a different metric"
        )
    base_low, base_high = float(band[0]), float(band[1])

    size_factor, size_label = _size_factor(query.size_ebitda)
    if query.growth and query.growth not in _GROWTH_FACTORS:
        raise ValueError(
            f"unknown growth {query.growth!r}; use high|growing|flat|declining"
        )
    growth_factor = _GROWTH_FACTORS.get(query.growth, 1.0)

    combined = size_factor * growth_factor
    low = base_low * combined
    high = base_high * combined

    return {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "sector_matched": rec["sector"],
        "metric": query.metric,
        "base_band": [round(base_low, 4), round(base_high, 4)],
        "modifiers": {
            "size_factor": round(size_factor, 4),
            "size_band": size_label,
            "growth_factor": round(growth_factor, 4),
            "growth": query.growth or "unspecified",
            "combined_factor": round(combined, 4),
        },
        "low_multiple": round(low, 4),
        "high_multiple": round(high, 4),
        "mid_multiple": round((low + high) / 2.0, 4),
        "notes": rec.get("notes", ""),
        "source": "Illustrative reference dataset — replace with proprietary comps for live use.",
        "valuation_market": {
            "metric": query.metric,
            "low_multiple": round(low, 4),
            "high_multiple": round(high, 4),
        },
        "disclaimer": "Decision-support only; illustrative ranges, not a market quote or advice.",
    }


def to_valuation_market(result: Dict[str, object]) -> Dict[str, object]:
    """Adapter: comparables result -> valuation engine ``market`` block."""
    return dict(result["valuation_market"])


class ComparablesEngine:
    name = ENGINE_NAME
    version = ENGINE_VERSION

    def lookup(self, query: CompQuery) -> Dict[str, object]:
        return lookup(query)

    def lookup_dict(self, payload: Dict[str, object]) -> Dict[str, object]:
        return lookup(CompQuery.from_dict(payload))
