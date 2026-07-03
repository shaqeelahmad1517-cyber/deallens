"""Locate the sibling DealLens engine packages and put them on sys.path.

The four primitives live in sibling folders under one project directory:

    Financial Analysis/
      deallens_valuation_engine/
      deallens_diligence_engine/
      deallens_comparables_library/
      deallens_orchestrator/        <- this package

Importing this module makes ``valuation_engine``, ``diligence_engine``, and
``comparables`` importable when the folders are side by side. If they're already
installed/on the path, this is a no-op.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))           # .../deallens_orchestrator/orchestrator
_PKG_ROOT = os.path.dirname(_HERE)                            # .../deallens_orchestrator
_PROJECT = os.path.dirname(_PKG_ROOT)                         # .../Financial Analysis

_SIBLINGS = (
    "deallens_valuation_engine",
    "deallens_diligence_engine",
    "deallens_comparables_library",
)


def ensure_on_path() -> None:
    # Allow an explicit override for non-standard layouts.
    override = os.environ.get("DEALLENS_HOME")
    roots = [override] if override else [_PROJECT]
    for root in roots:
        if not root:
            continue
        for sub in _SIBLINGS:
            p = os.path.join(root, sub)
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)


ensure_on_path()
