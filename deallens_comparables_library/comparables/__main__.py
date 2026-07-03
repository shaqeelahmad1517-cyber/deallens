"""CLI adapter for the comparables primitive.

    python -m comparables examples/example_query.json
    echo '{"sector":"saas","metric":"revenue"}' | python -m comparables
    python -m comparables --sectors
    python -m comparables --manifest
"""
from __future__ import annotations

import json
import sys

from .engine import available_sectors
from .primitive import invoke, manifest


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--manifest" in argv:
        print(json.dumps(manifest(), indent=2))
        return 0
    if "--sectors" in argv:
        print(json.dumps(available_sectors(), indent=2))
        return 0

    paths = [a for a in argv if not a.startswith("-")]
    if paths:
        with open(paths[0], "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    else:
        raw = sys.stdin.read().strip()
        payload = json.loads(raw) if raw else {}

    envelope = invoke(payload)
    print(json.dumps(envelope, indent=2))
    return 0 if envelope.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
