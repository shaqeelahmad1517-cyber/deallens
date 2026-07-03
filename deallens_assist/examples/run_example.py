"""Assist demo: suggest add-backs from a document, then draft a narrative."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import assist  # noqa: E402

ingestion = {
    "financials": {"revenue": 4200000, "net_income": 520000, "owner_compensation": 180000},
    "adjustment_candidates": [
        {"label": "Owner's personal vehicle", "amount": 35000, "type": "add_back"},
        {"label": "One-time legal settlement", "amount": 60000, "type": "add_back"},
    ],
}

print("=== SUGGESTED ADD-BACKS (for review) ===")
env = assist.invoke({"action": "suggest_adjustments", "ingestion": ingestion})
for s in env["result"]["suggestions"]:
    print(f"  [{s['confidence'].upper():<6}] {s['label']}: {s['amount']:,.0f}")
    print(f"           → {s['rationale']}")
for note in env["result"]["notes"]:
    print(f"  NOTE: {note}")

result = {
    "target_name": "Northwind Logistics",
    "recommendation": {"range": {"low": 1921022, "high": 2618932, "mid": 2269977}},
    "diligence": {"completion_pct": 25.9, "red_flags": [
        {"label": "Customer concentration 38%", "severity": "high"},
        {"label": "Owner dependence", "severity": "high"}]},
    "comparables": {"sector_matched": "logistics", "base_band": [2.0, 3.0],
                    "modifiers": {"size_factor": 1.0, "growth_factor": 1.07}},
    "valuation": {
        "target_name": "Northwind Logistics",
        "normalization": {"normalized_ebitda": 830000, "sde": 1010000},
        "risk": {"multiple_discount": 0.24},
        "approaches": {"income": {"dcf": {"value": 2589041}, "capitalization": {"value": 3458333}},
                       "market": {"metric": "sde", "low_multiple": 2.49, "high_multiple": 4.15},
                       "asset": {"value": 1250000}},
        "recommended_range": {"low": 1921022, "high": 2618932, "mid": 2269977},
    },
}

print("\n=== DRAFT NARRATIVE ===")
env = assist.invoke({"action": "draft_narrative", "result": result, "options": {"format": "text"}})
print(env["result"]["narrative"])
