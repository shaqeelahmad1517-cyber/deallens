"""Market approach: comparable-multiple valuation."""
from __future__ import annotations

from typing import Dict


def multiple_valuation(
    metric_value: float,
    low_multiple: float,
    high_multiple: float,
    metric: str = "sde",
) -> Dict[str, object]:
    """Apply a low/high multiple band to a normalized metric.

    Returns a value range. Multiples are typically drawn from a comparables
    library (e.g. 3-5x SDE, 4-8x EBITDA, or a revenue multiple).
    """
    if low_multiple > high_multiple:
        low_multiple, high_multiple = high_multiple, low_multiple
    # Sort the products so low <= high even if metric_value is negative.
    low, high = sorted([metric_value * low_multiple, metric_value * high_multiple])
    return {
        "method": "market_multiple",
        "metric": metric,
        "metric_value": round(metric_value, 2),
        "low_multiple": round(low_multiple, 4),
        "high_multiple": round(high_multiple, 4),
        "low": round(low, 2),
        "high": round(high, 2),
        "mid": round((low + high) / 2.0, 2),
    }
