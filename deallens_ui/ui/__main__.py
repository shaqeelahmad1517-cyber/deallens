"""Launch the DealLens UI.

    python -m ui                 # serve on http://127.0.0.1:8765
    python -m ui --port 9000
"""
from __future__ import annotations

import os
import sys

from .server import run


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Env wins for hosted deployment (Railway sets $PORT); flags override locally.
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "127.0.0.1")
    if "--port" in argv:
        i = argv.index("--port")
        if i + 1 < len(argv):
            port = int(argv[i + 1])
    if "--host" in argv:
        i = argv.index("--host")
        if i + 1 < len(argv):
            host = argv[i + 1]
    run(host, port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
