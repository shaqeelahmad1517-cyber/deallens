"""Interlock demo: run diligence, then feed its red flags into valuation.

This is the two primitives connected — exactly what the AIOS spine does:
    diligence.invoke(checklist) -> red_flags -> valuation.invoke(deal)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DILIGENCE_ROOT = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(DILIGENCE_ROOT)
VALUATION_ROOT = os.path.join(PROJECT_ROOT, "deallens_valuation_engine")

sys.path.insert(0, DILIGENCE_ROOT)
sys.path.insert(0, VALUATION_ROOT)

import diligence_engine  # noqa: E402

try:
    import valuation_engine  # noqa: E402
    HAS_VALUATION = True
except ImportError:
    HAS_VALUATION = False

# --- Step 1: run diligence ---------------------------------------------------
with open(os.path.join(HERE, "example_checklist.json"), encoding="utf-8") as fh:
    checklist = json.load(fh)

dili_env = diligence_engine.invoke(checklist)
assert dili_env["ok"], dili_env
dili = dili_env["result"]

print("=" * 64)
print(f"DILIGENCE — {dili['target_name']} ({dili['business_type']})")
print("=" * 64)
print(f"  Completion        : {dili['completion_pct']}%")
print(f"  Overall risk      : {dili['summary']['overall_risk_level']} "
      f"(score {dili['summary']['overall_risk_score']})")
print(f"  Red flags ({dili['summary']['red_flag_count']}):")
for f in dili["red_flags"]:
    print(f"    [{f['severity'].upper():<6}] {f['category']:<11} {f['label']}")

# --- Step 2: hand red flags to valuation ------------------------------------
risk_flags = diligence_engine.to_valuation_risk_flags(dili)

if not HAS_VALUATION:
    print("\n(valuation_engine not found alongside this folder — skipping step 2)")
    sys.exit(0)

deal = {
    "target_name": dili["target_name"],
    "financials": {
        "revenue": 4200000, "net_income": 520000, "interest": 40000,
        "taxes": 110000, "depreciation": 90000, "amortization": 20000,
        "owner_compensation": 180000, "total_assets": 1900000,
        "total_liabilities": 700000, "fair_value_adjustment": 50000
    },
    "adjustments": [
        {"label": "Owner perks", "amount": 35000, "type": "add_back"},
        {"label": "One-off legal", "amount": 60000, "type": "add_back"},
        {"label": "Asset sale gain", "amount": 45000, "type": "deduction"}
    ],
    "market": {"metric": "sde", "low_multiple": 3.0, "high_multiple": 5.0},
    "risk_flags": risk_flags,          # <-- THE INTERLOCK
}

val_env = valuation_engine.invoke(deal)
assert val_env["ok"], val_env
val = val_env["result"]

print("\n" + "=" * 64)
print(f"VALUATION — driven by {len(risk_flags)} diligence red flag(s)")
print("=" * 64)
print(f"  Normalized SDE    : {val['normalization']['sde']:,.0f}")
print(f"  Risk multiple cut : {val['risk']['multiple_discount']*100:.1f}%")
print(f"  Eff. discount rate: {val['effective_discount_rate']*100:.1f}%")
rr = val["recommended_range"]
print(f"  RECOMMENDED RANGE : {rr['low']:,.0f}  to  {rr['high']:,.0f}  (mid {rr['mid']:,.0f})")
print("\nDiligence findings flowed straight into the price. That's the spine.")
