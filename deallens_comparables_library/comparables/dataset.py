"""Seed comparables dataset: typical private-business valuation multiple bands.

IMPORTANT: these are ILLUSTRATIVE reference ranges for small-to-lower-midmarket
private businesses, meant as sensible defaults you can edit or replace with your
own proprietary comp data. They are NOT a live market feed and not a claim about
any specific current transaction environment. Override via ``load_dataset``.

Each record:
    sector   : canonical key
    aliases  : alternative names that resolve to this sector
    sde      : [low, high] multiple of Seller's Discretionary Earnings
    ebitda   : [low, high] multiple of EBITDA
    revenue  : [low, high] multiple of revenue (None if not commonly used)
    notes    : short context
"""
from __future__ import annotations

from typing import Any, Dict, List

_SEED: List[Dict[str, Any]] = [
    {
        "sector": "general",
        "aliases": ["other", "misc", "smb"],
        "sde": [2.0, 3.0], "ebitda": [3.0, 5.0], "revenue": [0.5, 1.0],
        "notes": "Generic small-business default band.",
    },
    {
        "sector": "logistics",
        "aliases": ["transportation", "trucking", "freight", "shipping"],
        "sde": [2.0, 3.0], "ebitda": [3.5, 5.5], "revenue": [0.4, 0.8],
        "notes": "Asset-influenced; multiples sensitive to fleet condition and contracts.",
    },
    {
        "sector": "saas",
        "aliases": ["software", "b2b software", "cloud"],
        "sde": [3.0, 5.0], "ebitda": [6.0, 12.0], "revenue": [3.0, 8.0],
        "notes": "Recurring revenue commands premium; revenue multiple common pre-profit.",
    },
    {
        "sector": "ecommerce",
        "aliases": ["online retail", "dtc", "d2c"],
        "sde": [2.5, 4.0], "ebitda": [4.0, 7.0], "revenue": [0.8, 2.5],
        "notes": "Brand strength, channel concentration, and retention drive the band.",
    },
    {
        "sector": "retail",
        "aliases": ["brick and mortar", "store", "shop"],
        "sde": [1.5, 3.0], "ebitda": [3.0, 5.0], "revenue": [0.3, 0.7],
        "notes": "Lease terms, location, and inventory quality are pivotal.",
    },
    {
        "sector": "restaurant",
        "aliases": ["food and beverage", "f&b", "cafe", "hospitality"],
        "sde": [1.5, 2.5], "ebitda": [2.5, 4.0], "revenue": [0.3, 0.6],
        "notes": "Thin margins; brand and location dependent.",
    },
    {
        "sector": "manufacturing",
        "aliases": ["industrial", "production", "factory"],
        "sde": [2.5, 3.5], "ebitda": [4.0, 6.5], "revenue": [0.5, 1.2],
        "notes": "Asset-heavy; customer concentration and capex matter.",
    },
    {
        "sector": "professional_services",
        "aliases": ["consulting", "agency", "accounting", "law firm"],
        "sde": [2.0, 3.5], "ebitda": [3.5, 6.0], "revenue": [0.6, 1.5],
        "notes": "People-dependent; key-person and client concentration risk.",
    },
    {
        "sector": "healthcare_services",
        "aliases": ["healthcare", "medical", "clinic", "dental"],
        "sde": [2.5, 4.0], "ebitda": [4.5, 7.5], "revenue": [0.7, 1.6],
        "notes": "Regulatory and payer-mix sensitive; recurring patient base valued.",
    },
    {
        "sector": "construction",
        "aliases": ["contractor", "trades", "building"],
        "sde": [2.0, 3.0], "ebitda": [3.0, 5.0], "revenue": [0.3, 0.7],
        "notes": "Backlog quality and project concentration drive value.",
    },
    {
        "sector": "home_services",
        "aliases": ["hvac", "plumbing", "landscaping", "cleaning"],
        "sde": [2.0, 3.5], "ebitda": [3.5, 6.0], "revenue": [0.6, 1.3],
        "notes": "Recurring contracts and route density command premiums.",
    },
    {
        "sector": "distribution",
        "aliases": ["wholesale", "supplier"],
        "sde": [2.5, 3.5], "ebitda": [4.0, 6.0], "revenue": [0.4, 0.9],
        "notes": "Working-capital intensive; supplier and customer concentration matter.",
    },
]


def load_dataset() -> List[Dict[str, Any]]:
    """Return a deep-ish copy of the seed dataset (safe to mutate)."""
    return [dict(r, aliases=list(r["aliases"])) for r in _SEED]
