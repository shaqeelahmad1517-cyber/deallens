"""Full spine demo: diligence + comparables -> valuation.

Three primitives connected, exactly as the AIOS spine would chain them:

    diligence.invoke(checklist) --> red_flags ----\
                                                    >--> valuation.invoke(deal)
    comparables.invoke(query)  --> market band ---/
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMPS_ROOT = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(COMPS_ROOT)

for sub in ("deallens_valuation_engine", "deallens_diligence_engine", "deallens_comparables_library"):
    sys.path.insert(0, os.path.join(PROJECT_ROOT, sub))

import comparables          # noqa: E402

try:
    import valuation_engine  # noqa: E402
    import diligence_engine   # noqa: E402
except ImportError as exc:    # pragma: no cover
    print(f"Need sibling engine folders present: {exc}")
    sys.exit(1)

TARGET = "Northwind Logistics"

# --- Step 1: diligence -> red flags -----------------------------------------
checklist = {
    "target_name": TARGET,
    "business_type": "smb",
    "items": [
        {"id": "cust_concentration", "status": "flagged", "risk_rating": "high",
         "notes": "Top customer 38%"},
        {"id": "ppl_owner_dependence", "status": "flagged", "risk_rating": "medium",
         "notes": "Owner holds key relationships"},
    ],
    "signals": {"top_customer_pct": 38, "owner_dependent": True,
                "management_team_in_place": False, "revenue_trend": "growing"},
}
dili = diligence_engine.invoke(checklist)["result"]
risk_flags = diligence_engine.to_valuation_risk_flags(dili)

# --- Step 2: comparables -> market multiple band ----------------------------
comps = comparables.invoke({
    "sector": "logistics", "metric": "sde",
    "size_ebitda": 830_000, "growth": "growing",
})["result"]
market = comparables.to_valuation_market(comps)

# --- Step 3: valuation, driven by BOTH --------------------------------------
deal = {
    "target_name": TARGET,
    "financials": {
        "revenue": 4_200_000, "net_income": 520_000, "interest": 40_000,
        "taxes": 110_000, "depreciation": 90_000, "amortization": 20_000,
        "owner_compensation": 180_000, "total_assets": 1_900_000,
        "total_liabilities": 700_000, "fair_value_adjustment": 50_000,
    },
    "adjustments": [
        {"label": "Owner perks", "amount": 35_000, "type": "add_back"},
        {"label": "One-off legal", "amount": 60_000, "type": "add_back"},
        {"label": "Asset sale gain", "amount": 45_000, "type": "deduction"},
    ],
    "market": market,            # <-- from comparables
    "risk_flags": risk_flags,    # <-- from diligence
}
val = valuation_engine.invoke(deal)["result"]

# --- Report ------------------------------------------------------------------
bar = "=" * 64
print(bar); print(f"FULL PIPELINE — {TARGET}"); print(bar)
print(f"1. DILIGENCE  : {dili['completion_pct']}% complete, "
      f"{dili['summary']['red_flag_count']} red flags "
      f"({dili['summary']['overall_risk_level']} risk)")
for f in dili["red_flags"]:
    print(f"               [{f['severity'].upper():<6}] {f['label']}")
print(f"2. COMPARABLES: {comps['sector_matched']} {comps['metric'].upper()} "
      f"base {comps['base_band']}  ->  "
      f"{comps['low_multiple']}-{comps['high_multiple']}x "
      f"(size x{comps['modifiers']['size_factor']}, growth x{comps['modifiers']['growth_factor']})")
print(f"3. VALUATION  : SDE {val['normalization']['sde']:,.0f}, "
      f"risk cut {val['risk']['multiple_discount']*100:.0f}%")
rr = val["recommended_range"]
print(bar)
print(f"   RECOMMENDED RANGE : {rr['low']:,.0f}  to  {rr['high']:,.0f}  (mid {rr['mid']:,.0f})")
print(bar)
print("Diligence risk + market comps both flowed into one price. That's the spine.")
