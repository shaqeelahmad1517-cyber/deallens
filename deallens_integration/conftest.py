"""Put every DealLens engine on sys.path for the integration/fuzz suite."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_HERE)

for sub in (
    "deallens_valuation_engine", "deallens_diligence_engine",
    "deallens_comparables_library", "deallens_orchestrator", "deallens_report",
    "deallens_workspace", "deallens_quickscreen", "deallens_documents", "deallens_assist",
):
    p = os.path.join(_PROJECT, sub)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
