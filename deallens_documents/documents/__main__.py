"""CLI for document ingestion.

    python -m documents statement.csv
    python -m documents statement.xlsx
    python -m documents statement.pdf        # needs pdfplumber or pypdf
    cat statement.txt | python -m documents   # read text from stdin
    python -m documents --manifest
"""
from __future__ import annotations

import json
import sys

from .primitive import invoke, manifest


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--manifest" in argv:
        print(json.dumps(manifest(), indent=2))
        return 0
    paths = [a for a in argv if not a.startswith("-")]
    if paths:
        payload = {"path": paths[0]}
    else:
        raw = sys.stdin.read()
        payload = {"text": raw}
    env = invoke(payload)
    print(json.dumps(env, indent=2))
    return 0 if env.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
