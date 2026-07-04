"""Seed comparables dataset: private-business AND public-market multiple bands.

Each sector carries two calibrations:
  * SMB bands (sde/ebitda/revenue) — small & lower-mid-market PRIVATE businesses.
  * Public bands (ebitda_public/revenue_public) — how the STOCK MARKET prices
    large, liquid, often faster-growing companies (much higher multiples).

The ``tier`` on a query selects which calibration to use. All figures are
ILLUSTRATIVE reference ranges you can edit or replace with proprietary comps.
They are NOT a live market feed.
"""
from __future__ import annotations

from typing import Any, Dict, List

_SEED: List[Dict[str, Any]] = [
    {
        "sector": "general",
        "aliases": ["other", "misc", "smb"],
        "sde": [2.0, 3.0], "ebitda": [3.0, 5.0], "revenue": [0.5, 1.0],
        "ebitda_public": [8.0, 12.0], "revenue_public": [1.0, 3.0],
        "notes": "Generic default band.",
    },
    {
        "sector": "logistics",
        "aliases": ["transportation", "trucking", "freight", "shipping"],
        "sde": [2.0, 3.0], "ebitda": [3.5, 5.5], "revenue": [0.4, 0.8],
        "ebitda_public": [10.0, 16.0], "revenue_public": [1.0, 2.5],
        "notes": "Asset-influenced; public LTL/freight names trade ~10-16x EBITDA.",
    },
    {
        "sector": "saas",
        "aliases": ["software", "b2b software", "cloud"],
        "sde": [3.0, 5.0], "ebitda": [6.0, 12.0], "revenue": [3.0, 8.0],
        "ebitda_public": [20.0, 40.0], "revenue_public": [6.0, 15.0],
        "notes": "Recurring revenue; public SaaS often priced on revenue multiples.",
    },
    {
        "sector": "ecommerce",
        "aliases": ["online retail", "dtc", "d2c"],
        "sde": [2.5, 4.0], "ebitda": [4.0, 7.0], "revenue": [0.8, 2.5],
        "ebitda_public": [10.0, 18.0], "revenue_public": [1.5, 4.0],
        "notes": "Brand strength and retention drive the band.",
    },
    {
        "sector": "retail",
        "aliases": ["brick and mortar", "store", "shop"],
        "sde": [1.5, 3.0], "ebitda": [3.0, 5.0], "revenue": [0.3, 0.7],
        "ebitda_public": [6.0, 10.0], "revenue_public": [0.5, 1.5],
        "notes": "Lease terms, location, and inventory quality are pivotal.",
    },
    {
        "sector": "restaurant",
        "aliases": ["food and beverage", "f&b", "cafe", "hospitality"],
        "sde": [1.5, 2.5], "ebitda": [2.5, 4.0], "revenue": [0.3, 0.6],
        "ebitda_public": [8.0, 12.0], "revenue_public": [1.0, 2.5],
        "notes": "Thin margins; brand and location dependent.",
    },
    {
        "sector": "manufacturing",
        "aliases": ["industrial", "production", "factory"],
        "sde": [2.5, 3.5], "ebitda": [4.0, 6.5], "revenue": [0.5, 1.2],
        "ebitda_public": [8.0, 13.0], "revenue_public": [1.0, 2.5],
        "notes": "Asset-heavy; customer concentration and capex matter.",
    },
    {
        "sector": "professional_services",
        "aliases": ["consulting", "agency", "accounting", "law firm"],
        "sde": [2.0, 3.5], "ebitda": [3.5, 6.0], "revenue": [0.6, 1.5],
        "ebitda_public": [9.0, 14.0], "revenue_public": [1.0, 3.0],
        "notes": "People-dependent; key-person and client concentration risk.",
    },
    {
        "sector": "healthcare_services",
        "aliases": ["healthcare", "medical", "clinic", "dental"],
        "sde": [2.5, 4.0], "ebitda": [4.5, 7.5], "revenue": [0.7, 1.6],
        "ebitda_public": [10.0, 16.0], "revenue_public": [1.5, 3.5],
        "notes": "Regulatory and payer-mix sensitive; recurring patients valued.",
    },
    {
        "sector": "construction",
        "aliases": ["contractor", "trades", "building"],
        "sde": [2.0, 3.0], "ebitda": [3.0, 5.0], "revenue": [0.3, 0.7],
        "ebitda_public": [6.0, 10.0], "revenue_public": [0.5, 1.2],
        "notes": "Backlog quality and project concentration drive value.",
    },
    {
        "sector": "home_services",
        "aliases": ["hvac", "plumbing", "landscaping", "cleaning"],
        "sde": [2.0, 3.5], "ebitda": [3.5, 6.0], "revenue": [0.6, 1.3],
        "ebitda_public": [10.0, 16.0], "revenue_public": [1.5, 3.0],
        "notes": "Recurring contracts and route density command premiums.",
    },
    {
        "sector": "distribution",
        "aliases": ["wholesale", "supplier"],
        "sde": [2.5, 3.5], "ebitda": [4.0, 6.0], "revenue": [0.4, 0.9],
        "ebitda_public": [8.0, 12.0], "revenue_public": [0.7, 1.8],
        "notes": "Working-capital intensive; concentration matters.",
    },
]


def load_dataset() -> List[Dict[str, Any]]:
    """Return a copy of the seed dataset (safe to mutate)."""
    return [dict(r, aliases=list(r["aliases"])) for r in _SEED]
