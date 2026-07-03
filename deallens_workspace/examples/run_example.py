"""Full deal lifecycle through the workspace: create -> evaluate -> report -> list."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import workspace  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "demo_data")  # self-contained demo store

deal_fields = {
    "target_name": "Northwind Logistics",
    "stage": "diligence",
    "financials": {
        "revenue": 4200000, "net_income": 520000, "interest": 40000, "taxes": 110000,
        "depreciation": 90000, "amortization": 20000, "owner_compensation": 180000,
        "total_assets": 1900000, "total_liabilities": 700000, "fair_value_adjustment": 50000,
    },
    "adjustments": [
        {"label": "Owner perks", "amount": 35000, "type": "add_back"},
        {"label": "One-off legal", "amount": 60000, "type": "add_back"},
        {"label": "Asset sale gain", "amount": 45000, "type": "deduction"},
    ],
    "checklist": {
        "business_type": "smb",
        "items": [
            {"id": "fin_statements", "status": "complete", "risk_rating": "low"},
            {"id": "cust_concentration", "status": "flagged", "risk_rating": "high", "notes": "Top customer 38%"},
            {"id": "ppl_owner_dependence", "status": "flagged", "risk_rating": "medium"},
        ],
        "signals": {"top_customer_pct": 38, "owner_dependent": True,
                    "management_team_in_place": False, "revenue_trend": "growing"},
    },
    "comparables": {"sector": "logistics", "metric": "sde"},
}


def step(title):
    print("\n" + "-" * 60)
    print(title)
    print("-" * 60)


step("1. CREATE a deal")
env = workspace.invoke({"action": "create", "deal": deal_fields, "store_root": STORE})
deal_id = env["result"]["id"]
print(f"   created deal id: {deal_id}  (stage: {env['result']['stage']})")

step("2. EVALUATE it (runs diligence + comparables + valuation)")
env = workspace.invoke({"action": "evaluate", "id": deal_id, "store_root": STORE})
rr = env["result"]["recommendation"]["range"]
print(f"   recommended range: {rr['low']:,.0f} - {rr['high']:,.0f}  (mid {rr['mid']:,.0f})")
print(f"   risk cut: {env['result']['recommendation']['risk_multiple_discount']*100:.0f}%")

step("3. REPORT it (writes a client-ready file)")
env = workspace.invoke({"action": "report", "id": deal_id, "format": "html", "store_root": STORE})
print(f"   report: {env['result']['path']}")

step("4. LIST deals in the workspace")
env = workspace.invoke({"action": "list", "store_root": STORE})
for d in env["result"]["deals"]:
    rng = d.get("recommended_range")
    rng_s = f"{rng['low']:,.0f}-{rng['high']:,.0f}" if rng else "not evaluated"
    print(f"   [{d['stage']:<10}] {d['target_name']:<22} {rng_s}  ({d['reports']} report/s)")

step("5. The deal persisted to disk")
print(f"   stored under: {STORE}")
print("   Re-run this and the deal list grows — state survives between runs.")
