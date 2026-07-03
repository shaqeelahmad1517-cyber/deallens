"""Launch the DealLens UI.

    python -m ui                 # serve on http://127.0.0.1:8765
    python -m ui --port 9000
"""
from __future__ import annotations

import os
import sys

from .server import run


def _flag(argv, name):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def _resolve_port(argv) -> int:
    """Resolve the port robustly. Handles an unexpanded '$PORT' arg (which some
    hosts pass literally) by falling back to the PORT env var, then a default."""
    candidates = []
    flag = _flag(argv, "--port")
    if flag:
        # If a host passed the literal "$PORT" (or "${PORT}"), expand from env.
        if flag.startswith("$"):
            flag = os.environ.get(flag.strip("${}"), "")
        candidates.append(flag)
    candidates.append(os.environ.get("PORT", ""))
    for c in candidates:
        try:
            return int(c)
        except (TypeError, ValueError):
            continue
    return 8765


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    host = _flag(argv, "--host") or os.environ.get("HOST", "127.0.0.1")
    if host.startswith("$"):
        host = os.environ.get(host.strip("${}"), "0.0.0.0")
    run(host, _resolve_port(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
