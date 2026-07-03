"""CLI for quick-screen.

    python -m quickscreen example.json
    echo '{"earnings":1010000,"sector":"logistics","asking_price":2500000}' | python -m quickscreen
    python -m quickscreen --manifest
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
        with open(paths[0], "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    else:
        raw = sys.stdin.read().strip()
        payload = json.loads(raw) if raw else {}
    env = invoke(payload)
    print(json.dumps(env, indent=2))
    return 0 if env.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
