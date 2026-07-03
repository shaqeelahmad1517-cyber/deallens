"""End-to-end: run the orchestrator, then render a client-ready report.

Produces an HTML report (always) and a Word .docx (if python-docx is installed),
right here in the examples/ folder.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT_ROOT = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(REPORT_ROOT)

sys.path.insert(0, REPORT_ROOT)
for sub in ("deallens_orchestrator", "deallens_valuation_engine",
            "deallens_diligence_engine", "deallens_comparables_library"):
    sys.path.insert(0, os.path.join(PROJECT_ROOT, sub))

import report  # noqa: E402

# Build a deal evaluation. Prefer the live orchestrator; fall back to a saved result.
deal = {
    "target_name": "Northwind Logistics",
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

try:
    import orchestrator
    env = orchestrator.invoke(deal)
    if not env["ok"]:
        raise RuntimeError(env["error"])
    result = env["result"]
    source = "orchestrator"
except Exception as exc:  # pragma: no cover
    print(f"(orchestrator unavailable: {exc}; using bundled sample result)")
    with open(os.path.join(HERE, "sample_result.json"), encoding="utf-8") as fh:
        result = json.load(fh)
    source = "sample"

options = {"as_of": "June 2026", "prepared_by": "DealLens"}

html_path = os.path.join(HERE, "northwind_report.html")
with open(html_path, "w", encoding="utf-8") as fh:
    fh.write(report.render(result, "html", options))
print(f"HTML report written: {html_path}  (source: {source})")

md_path = os.path.join(HERE, "northwind_report.md")
with open(md_path, "w", encoding="utf-8") as fh:
    fh.write(report.render(result, "markdown", options))
print(f"Markdown report written: {md_path}")

if report.docx_available():
    docx_path = os.path.join(HERE, "northwind_report.docx")
    report.write_docx(result, docx_path, options)
    print(f"Word report written: {docx_path}")
else:
    print("Word (.docx) skipped — install python-docx to enable: pip install python-docx")

print("\nOpen the HTML in a browser and print to PDF for a client-ready deliverable.")
