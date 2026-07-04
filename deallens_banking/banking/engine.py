"""Banking / financial-institution valuation.

Banks are NOT valued like operating companies: EBITDA and free-cash-flow DCF are
meaningless because interest is their core revenue, not a financing cost. Instead
they trade on **book value (P/B)** and **net income (P/E)**. This primitive
implements that method explicitly — no interest add-back, no EBITDA.

Bands are illustrative; edit or replace with your own comps.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

ENGINE_NAME = "deallens.banking"
ENGINE_VERSION = "1.0.0"

# Illustrative multiple bands by institution type: (P/B band, P/E band).
BANK_TYPES: Dict[str, Dict[str, Any]] = {
    "universal_bank": {
        "aliases": ["megabank", "global bank", "money center", "citibank", "citi",
                    "jpmorgan", "bank of america", "wells fargo"],
        "pb": [0.6, 1.2], "pe": [8.0, 13.0],
        "notes": "Large diversified banks; often trade near or below book value.",
    },
    "regional_bank": {
        "aliases": ["community bank", "regional", "savings bank"],
        "pb": [1.0, 1.6], "pe": [9.0, 13.0],
        "notes": "Regional/community banks; usually above book.",
    },
    "investment_bank": {
        "aliases": ["broker dealer", "broker-dealer", "ib", "advisory"],
        "pb": [0.9, 1.6], "pe": [8.0, 12.0],
        "notes": "Capital-markets sensitive; earnings volatile.",
    },
    "insurance": {
        "aliases": ["insurer", "life insurance", "p&c", "reinsurer"],
        "pb": [0.8, 1.5], "pe": [8.0, 14.0],
        "notes": "Valued on book value and return on equity.",
    },
    "general_financial": {
        "aliases": ["bank", "financial", "fintech lender", "lender", "credit union"],
        "pb": [0.8, 1.4], "pe": [8.0, 12.0],
        "notes": "Generic financial-institution default.",
    },
}


def _resolve_type(key: str) -> str:
    key = (key or "general_financial").lower()
    if key in BANK_TYPES:
        return key
    for name, rec in BANK_TYPES.items():
        if key in rec["aliases"]:
            return name
    raise ValueError(f"unknown bank_type {key!r}; use one of {list(BANK_TYPES)} (or an alias)")


def value_bank(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object (dict)")
    bank_type = _resolve_type(payload.get("bank_type", "general_financial"))
    rec = BANK_TYPES[bank_type]

    net_income = payload.get("net_income")
    net_income = float(net_income) if net_income is not None else None

    # Book value = shareholders' equity. Prefer explicit, else assets - liabilities.
    book = payload.get("book_value")
    if book is None:
        ta = payload.get("total_assets")
        tl = payload.get("total_liabilities")
        if ta is not None and tl is not None:
            book = float(ta) - float(tl)
    book = float(book) if book is not None else None

    warnings: List[str] = []
    approaches: Dict[str, Any] = {}
    lows: List[float] = []
    highs: List[float] = []

    # Price-to-book
    if book is not None and book > 0:
        pb_low, pb_high = rec["pb"]
        approaches["price_to_book"] = {
            "book_value": round(book, 2), "multiple": rec["pb"],
            "low": round(book * pb_low, 2), "high": round(book * pb_high, 2),
        }
        lows.append(book * pb_low)
        highs.append(book * pb_high)
    else:
        warnings.append("Price-to-book skipped: book value missing or non-positive.")

    # Price-to-earnings
    if net_income is not None and net_income > 0:
        pe_low, pe_high = rec["pe"]
        approaches["price_to_earnings"] = {
            "net_income": round(net_income, 2), "multiple": rec["pe"],
            "low": round(net_income * pe_low, 2), "high": round(net_income * pe_high, 2),
        }
        lows.append(net_income * pe_low)
        highs.append(net_income * pe_high)
    else:
        warnings.append("Price-to-earnings skipped: net income missing or non-positive.")

    if not lows:
        return {
            "engine": ENGINE_NAME, "version": ENGINE_VERSION,
            "bank_type": bank_type, "approaches": approaches, "warnings": warnings,
            "recommended_range": None,
            "disclaimer": "Decision-support only; not financial advice.",
        }

    low = sum(lows) / len(lows)
    high = sum(highs) / len(highs)

    # Return on equity, if both available (useful context).
    roe = None
    if net_income is not None and book and book > 0:
        roe = round(net_income / book, 4)

    return {
        "engine": ENGINE_NAME, "version": ENGINE_VERSION,
        "bank_type": bank_type,
        "notes": rec["notes"],
        "roe": roe,
        "approaches": approaches,
        "warnings": warnings,
        "recommended_range": {"low": round(low, 2), "high": round(high, 2), "mid": round((low + high) / 2, 2)},
        "method": "Price-to-book and price-to-earnings (no EBITDA — banks earn on interest).",
        "disclaimer": "Illustrative bank multiples; decision-support only, not financial advice.",
    }
