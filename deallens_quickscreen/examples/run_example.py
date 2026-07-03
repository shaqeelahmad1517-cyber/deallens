"""Quick-screen a deal in seconds."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import quickscreen  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "example.json"), encoding="utf-8") as fh:
    payload = json.load(fh)

env = quickscreen.invoke(payload)
if not env["ok"]:
    print("ERROR:", env["error"]); sys.exit(1)
r = env["result"]

print("QUICK SCREEN")
print(f"  Sector            : {r['sector']}  ({r['metric'].upper()} {r['earnings']:,.0f})")
band = r["multiple_band_adjusted"]
print(f"  Multiple (adj.)   : {band[0]}x – {band[1]}x   (risk haircut {r['risk_haircut']*100:.0f}%)")
rr = r["range"]
print(f"  INDICATIVE RANGE  : {rr['low']:,.0f} – {rr['high']:,.0f}  (mid {rr['mid']:,.0f})")
if "verdict" in r:
    print(f"  Asking price      : {r['asking_price']:,.0f}")
    print(f"  Verdict           : {r['verdict']}  ({r['vs_midpoint_pct']:+.0f}% vs midpoint)")
    print(f"                      {r['verdict_note']}")
print(f"\n  {r['disclaimer']}")
