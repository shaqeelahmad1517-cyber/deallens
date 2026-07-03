"""Run the engine on the bundled example deal and print a readable summary."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation_engine import invoke  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "example_deal.json"), encoding="utf-8") as fh:
    payload = json.load(fh)

env = invoke(payload)
assert env["ok"], env
r = env["result"]

print(f"Target: {r['target_name']}")
print(f"  Normalized EBITDA : {r['normalization']['normalized_ebitda']:>14,.0f}")
print(f"  SDE               : {r['normalization']['sde']:>14,.0f}")
print(f"  Risk multiple cut : {r['risk']['multiple_discount']*100:>13.1f}%")
print(f"  Eff. discount rate: {r['effective_discount_rate']*100:>13.1f}%")
print("  Approach ranges:")
for name, a in r["approaches"].items():
    rng = a.get("range")
    if rng is None and a.get("low") is not None:
        rng = {"low": a["low"], "high": a["high"]}
    if rng is None:  # point estimate (asset/NAV)
        print(f"    - {name:<7}: {a['value']:>14,.0f}")
    else:
        print(f"    - {name:<7}: {rng['low']:>14,.0f}  to  {rng['high']:,.0f}")
rr = r["recommended_range"]
print(f"  RECOMMENDED RANGE : {rr['low']:,.0f}  to  {rr['high']:,.0f}  (mid {rr['mid']:,.0f})")
