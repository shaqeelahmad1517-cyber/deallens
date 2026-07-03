"""Triangulate per-approach results into a single weighted value range."""
from __future__ import annotations

from typing import Dict, List

from .models import Range


def triangulate(approach_ranges: Dict[str, Range], weights: Dict[str, float]) -> Dict[str, object]:
    """Weighted-average the low/high bounds of each enabled approach.

    Only approaches present in ``approach_ranges`` with positive weight count.
    Returns the blended range plus the absolute floor/ceiling across methods.
    """
    items = [(name, rng, max(weights.get(name, 0.0), 0.0)) for name, rng in approach_ranges.items()]
    items = [it for it in items if it[2] > 0.0]
    if not items:
        raise ValueError("no weighted approaches available to triangulate")

    total_w = sum(w for _, _, w in items)
    blended_low = sum(r.low * w for _, r, w in items) / total_w
    blended_high = sum(r.high * w for _, r, w in items) / total_w
    blended_mid = sum(r.mid * w for _, r, w in items) / total_w

    # Defensive: guarantee low <= high and a non-negative valuation range.
    blended_low, blended_high = sorted([blended_low, blended_high])
    blended_low = max(blended_low, 0.0)
    blended_high = max(blended_high, 0.0)

    floor = max(min(r.low for _, r, _ in items), 0.0)
    ceiling = max(r.high for _, r, _ in items)

    return {
        "weighted_range": Range(blended_low, blended_high).to_dict(),
        "weighted_mid": round(blended_mid, 2),
        "floor": round(floor, 2),
        "ceiling": round(ceiling, 2),
        "weights_used": {name: round(w, 4) for name, _, w in items},
    }
