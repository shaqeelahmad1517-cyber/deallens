"""One call in, full deal evaluation out."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import orchestrator  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "example_deal.json"), encoding="utf-8") as fh:
    payload = json.load(fh)

env = orchestrator.invoke(payload)
if not env["ok"]:
    print("ERROR:", env["error"])
    sys.exit(1)
r = env["result"]

bar = "=" * 64
print(bar)
print(f"DEAL EVALUATION — {r['target_name']}")
print(bar)

s = r["steps"]
print("Pipeline steps:")
for name in ("diligence", "comparables", "valuation"):
    st = s.get(name, {})
    mark = "ok" if st.get("ok") else "FAILED"
    extra = " (skipped)" if st.get("skipped") else ""
    print(f"   {name:<12}: {mark}{extra}")

if r["warnings"]:
    print("Warnings:")
    for w in r["warnings"]:
        print(f"   - {w}")

dl = r.get("diligence") or {}
cp = r.get("comparables") or {}
rec = r["recommendation"]

print("\nDiligence:")
print(f"   completion {dl.get('completion_pct', 'n/a')}%  |  "
      f"{dl.get('summary', {}).get('red_flag_count', 0)} red flags  |  "
      f"overall risk {dl.get('summary', {}).get('overall_risk_level', 'n/a')}")
print("Comparables:")
if cp:
    print(f"   {cp['sector_matched']} {cp['metric'].upper()}  "
          f"{cp['low_multiple']}-{cp['high_multiple']}x  "
          f"(size x{cp['modifiers']['size_factor']}, growth x{cp['modifiers']['growth_factor']})")
print("Key risks:")
for k in rec["key_risks"]:
    print(f"   - {k}")

print("\n" + bar)
print(f"   {rec['headline']}")
print(f"   risk multiple cut: {rec['risk_multiple_discount']*100:.0f}%")
print(bar)
print("One invoke() call ran all three engines. That's the spine.")
