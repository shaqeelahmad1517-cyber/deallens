"""Convenience launcher: `python3 run.py` (optionally `--port 9000`)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
