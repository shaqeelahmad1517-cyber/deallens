"""Comparables dataset: private-business AND public-market multiple bands.

Each sector carries two calibrations:
  * SMB bands (sde/ebitda/revenue) — small & lower-mid-market PRIVATE businesses.
  * Public bands (ebitda_public/revenue_public) — how the STOCK MARKET prices
    large, liquid, often faster-growing companies (much higher multiples).

The ``tier`` on a query selects which calibration to use.

SOURCING (reviewed 2026-07): the SMB bands are grounded in BizBuySell's published
transaction benchmarks (businesses actually sold, Q1 2021 - Q4 2025; overall SDE
multiple avg ~2.57, range ~2.0-3.3; revenue avg ~0.67). The public bands are
grounded in industry EV/EBITDA data (NYU Stern / Damodaran, Jan 2026; industry
benchmark aggregators). Public multiples run materially higher than private ones
(commonly 30-50%+, far more for high-growth software).

These are RESEARCHED AGGREGATE RANGES, not deal-specific or a live feed. They are
a sound default; for a real transaction, replace a sector's band with vetted comps
for that specific target. Sources are listed in the library README.
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
        "ebitda_public": [15.0, 35.0], "revenue_public": [5.0, 12.0],
        "notes": "Recurring revenue; SMB software SDE avg ~3.4 (BizBuySell 2025); "
                 "public SaaS 15-35x EBITDA (higher for fast growth), often priced on revenue.",
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
        "sde": [1.5, 3.0], "ebitda": [2.5, 4.0], "revenue": [0.3, 0.6],
        "ebitda_public": [8.0, 12.0], "revenue_public": [1.0, 2.5],
        "notes": "Single-unit owner-operated ~1.5-3.0x SDE (BizBuySell); thin margins.",
    },
    {
        "sector": "manufacturing",
        "aliases": ["industrial", "production", "factory"],
        "sde": [2.5, 3.5], "ebitda": [4.0, 6.5], "revenue": [0.5, 1.2],
        "ebitda_public": [7.0, 12.0], "revenue_public": [1.0, 2.5],
        "notes": "Asset-heavy; ~5-7x EBITDA private, ~7-12x public; capex matters.",
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
        "ebitda_public": [9.0, 15.0], "revenue_public": [1.5, 3.5],
        "notes": "Regulatory and payer-mix sensitive; services ~9-15x EBITDA public.",
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
    # --- Larger public-market categories (added 2026-07) -------------------
    # Bands grounded in Damodaran (NYU Stern, Jan 2026) EV/EBITDA by industry
    # and 2025-26 M&A medians; public > private by ~30-50%.
    {
        "sector": "consumer_staples",
        "aliases": ["food", "foods", "packaged food", "packaged foods", "food processing",
                    "food manufacturer", "food producer", "food production", "cpg",
                    "consumer packaged goods", "consumer staples", "consumer goods",
                    "household products", "snacks", "cereal", "grocery products",
                    "packaged goods", "packaged consumer goods", "personal care"],
        "sde": [2.5, 4.0], "ebitda": [5.0, 8.0], "revenue": [0.6, 1.5],
        "ebitda_public": [12.0, 16.0], "revenue_public": [1.5, 3.0],
        "notes": "Branded packaged food/CPG (e.g. cereal, snacks). Stable, brand-driven; "
                 "public names ~12-16x EBITDA (branded > private-label). Private-label runs lower.",
    },
    {
        "sector": "beverages",
        "aliases": ["beverage", "drinks", "soft drinks", "brewery", "distillery", "winery",
                    "bottling", "non-alcoholic beverages", "alcoholic beverages", "spirits", "brewing"],
        "sde": [2.5, 4.0], "ebitda": [5.0, 8.5], "revenue": [0.8, 2.0],
        "ebitda_public": [12.0, 18.0], "revenue_public": [2.0, 4.0],
        "notes": "Brand and distribution moats; large soft-drink/spirits names trade richly (14-20x).",
    },
    {
        "sector": "consumer_discretionary",
        "aliases": ["apparel", "clothing", "footwear", "leisure", "consumer durables",
                    "furniture", "toys", "luxury", "luxury goods", "apparel and accessories",
                    "household durables", "recreation", "consumer discretionary", "fashion"],
        "sde": [2.0, 3.5], "ebitda": [4.0, 6.5], "revenue": [0.5, 1.2],
        "ebitda_public": [8.0, 13.0], "revenue_public": [1.0, 2.5],
        "notes": "Cyclical demand; brand strength and inventory risk drive the band.",
    },
    {
        "sector": "pharmaceuticals",
        "aliases": ["pharma", "biotech", "biotechnology", "drug", "drugs", "life sciences",
                    "pharmaceutical", "pharmaceuticals", "medical devices", "medical device"],
        "sde": [3.0, 5.0], "ebitda": [5.0, 9.0], "revenue": [1.5, 3.5],
        "ebitda_public": [10.0, 15.0], "revenue_public": [3.0, 6.0],
        "notes": "Pipeline, patents, and regulatory approval drive value; public ~10-15x EBITDA.",
    },
    {
        "sector": "energy",
        "aliases": ["oil", "gas", "oil and gas", "petroleum", "upstream", "midstream",
                    "oilfield services", "exploration and production", "e&p", "refining"],
        "sde": [2.0, 3.5], "ebitda": [3.5, 6.0], "revenue": [0.5, 1.2],
        "ebitda_public": [5.0, 9.0], "revenue_public": [0.8, 2.0],
        "notes": "Commodity-price cyclical; capital-intensive; public ~5-9x EBITDA.",
    },
    {
        "sector": "utilities",
        "aliases": ["utility", "power", "electric", "electricity", "water utility",
                    "gas utility", "renewable energy", "power generation", "renewables"],
        "sde": [2.5, 3.5], "ebitda": [4.0, 7.0], "revenue": [0.8, 2.0],
        "ebitda_public": [9.0, 13.0], "revenue_public": [1.5, 3.5],
        "notes": "Regulated, stable cash flows; public ~9-13x EBITDA.",
    },
    {
        "sector": "media_entertainment",
        "aliases": ["media", "entertainment", "publishing", "broadcasting", "streaming",
                    "gaming", "film", "television", "advertising", "music", "content", "video games"],
        "sde": [2.0, 3.5], "ebitda": [3.5, 6.5], "revenue": [0.6, 1.8],
        "ebitda_public": [6.0, 12.0], "revenue_public": [1.0, 3.0],
        "notes": "Wide spread: digital/subscription (~9-10x) vs ad-dependent traditional (~4-5x).",
    },
    {
        "sector": "telecom",
        "aliases": ["telecommunications", "wireless", "carrier", "telco", "mobile network",
                    "broadband", "isp", "telecommunication", "telecom services"],
        "sde": [2.0, 3.0], "ebitda": [3.5, 5.5], "revenue": [0.8, 1.8],
        "ebitda_public": [6.0, 9.0], "revenue_public": [1.5, 3.0],
        "notes": "Capital-heavy infrastructure; public ~6-9x EBITDA.",
    },
    {
        "sector": "real_estate",
        "aliases": ["reit", "real estate", "property", "property management",
                    "commercial real estate", "residential real estate", "real estate operations"],
        "sde": [2.5, 4.0], "ebitda": [5.0, 9.0], "revenue": [1.5, 4.0],
        "ebitda_public": [15.0, 22.0], "revenue_public": [4.0, 10.0],
        "notes": "Often valued on FFO/cap rate rather than EBITDA; EV/EBITDA runs high (~15-25x) "
                 "because depreciation is large. Treat EBITDA multiples here with care.",
    },
    {
        "sector": "technology_hardware",
        "aliases": ["hardware", "semiconductor", "semiconductors", "electronics", "devices",
                    "chips", "computer hardware", "networking equipment", "tech hardware"],
        "sde": [2.5, 4.0], "ebitda": [5.0, 8.5], "revenue": [0.8, 2.0],
        "ebitda_public": [10.0, 16.0], "revenue_public": [2.0, 5.0],
        "notes": "Chips/devices; cyclical but higher-margin leaders trade ~12-18x.",
    },
    {
        "sector": "automotive",
        "aliases": ["auto", "automobile", "car manufacturer", "vehicles", "auto parts",
                    "automotive parts", "dealership", "car dealer", "automaker"],
        "sde": [2.0, 3.0], "ebitda": [3.5, 5.5], "revenue": [0.3, 0.8],
        "ebitda_public": [5.0, 9.0], "revenue_public": [0.5, 1.5],
        "notes": "Capital-intensive, cyclical, thin margins; public ~5-9x EBITDA.",
    },
    {
        "sector": "aerospace_defense",
        "aliases": ["aerospace", "defense", "defence", "aviation", "defense contractor",
                    "aircraft", "defense and aerospace"],
        "sde": [2.5, 4.0], "ebitda": [5.0, 8.0], "revenue": [0.8, 1.8],
        "ebitda_public": [10.0, 15.0], "revenue_public": [1.5, 3.0],
        "notes": "Long-cycle backlogs and government contracts; public ~10-15x EBITDA.",
    },
    {
        "sector": "agriculture",
        "aliases": ["agriculture", "farming", "agribusiness", "agri", "crop", "livestock",
                    "agricultural", "agricultural products"],
        "sde": [2.0, 3.5], "ebitda": [3.5, 6.0], "revenue": [0.5, 1.2],
        "ebitda_public": [7.0, 11.0], "revenue_public": [1.0, 2.5],
        "notes": "Commodity-linked, weather- and cycle-sensitive; public ~7-11x EBITDA.",
    },
    {
        "sector": "materials_chemicals",
        "aliases": ["materials", "chemicals", "mining", "metals", "commodities",
                    "industrial materials", "specialty chemicals", "plastics", "steel", "paper"],
        "sde": [2.5, 3.5], "ebitda": [4.0, 6.5], "revenue": [0.6, 1.4],
        "ebitda_public": [7.0, 11.0], "revenue_public": [1.0, 2.5],
        "notes": "Cyclical, capital-intensive; specialty chemicals trade above bulk commodities.",
    },
    {
        "sector": "insurance",
        "aliases": ["insurer", "insurance", "underwriting", "brokerage", "insurance broker", "reinsurance"],
        "sde": [2.5, 4.0], "ebitda": [4.0, 7.0], "revenue": [0.8, 2.0],
        "ebitda_public": [8.0, 12.0], "revenue_public": [1.0, 2.5],
        "notes": "For carriers, consider the bank/financial-institution method (book value / earnings) too.",
    },
]


def load_dataset() -> List[Dict[str, Any]]:
    """Return a copy of the seed dataset (safe to mutate)."""
    return [dict(r, aliases=list(r["aliases"])) for r in _SEED]
