"""Asset approach: net asset value (adjusted book value)."""
from __future__ import annotations

from typing import Dict


def net_asset_value(
    total_assets: float,
    total_liabilities: float,
    fair_value_adjustment: float = 0.0,
) -> Dict[str, object]:
    """NAV = assets - liabilities (+/- fair-value adjustment).

    Best used as a floor value or for asset-heavy targets.
    """
    nav = total_assets - total_liabilities + fair_value_adjustment
    return {
        "method": "net_asset_value",
        "value": round(nav, 2),
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "fair_value_adjustment": round(fair_value_adjustment, 2),
    }
