"""Put the sibling DealLens packages on sys.path (needs `documents`)."""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)
_PROJECT = os.path.dirname(_PKG_ROOT)

_SIBLINGS = ("deallens_documents",)


def ensure_on_path() -> None:
    root = os.environ.get("DEALLENS_HOME") or _PROJECT
    for sub in _SIBLINGS:
        p = os.path.join(root, sub)
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)


ensure_on_path()
