"""Ingest a sample financial statement (CSV) and show what was extracted."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import documents  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
env = documents.invoke({"path": os.path.join(HERE, "sample_financials.csv")})
if not env["ok"]:
    print("ERROR:", env["error"]); sys.exit(1)
r = env["result"]

print("EXTRACTED FINANCIALS  (from", r["source"] + ")")
for k, v in r["financials"].items():
    print(f"  {k:<20} {v:>14,.0f}")

if r["adjustment_candidates"]:
    print("\nPossible add-backs to review:")
    for a in r["adjustment_candidates"]:
        print(f"  - {a['label']}: {a['amount']:,.0f}")

if r["warnings"]:
    print("\nWarnings:")
    for w in r["warnings"]:
        print(f"  - {w}")

print(f"\n{len(r['line_items'])} line items matched, {len(r['unmatched'])} unmatched.")
print(r["disclaimer"])
