"""Put the comparables library on sys.path (the engine SOTP composes)."""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(os.path.dirname(_HERE))

# comparables for "multiple" mode; the full engine set for "deep" mode.
for sub in ("deallens_comparables_library", "deallens_valuation_engine",
            "deallens_diligence_engine", "deallens_orchestrator"):
    p = os.path.join(os.environ.get("DEALLENS_HOME") or _PROJECT, sub)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
