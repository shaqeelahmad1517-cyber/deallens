"""CLI: read a document into financials + findings.

    python -m understanding path/to/report.pdf
    python -m understanding --text "…document text…"

Uses an LLM if an API key is configured (see understanding/llm.py), else a
deterministic keyword scan.
"""
from __future__ import annotations

import json
import sys

from .primitive import invoke


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--text":
        payload = {"text": " ".join(argv[1:])}
    else:
        payload = {"path": argv[0]}
    env = invoke(payload)
    print(json.dumps(env, indent=2, default=str))
    return 0 if env.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
