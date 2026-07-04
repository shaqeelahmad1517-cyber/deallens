"""CLI for banking valuation.

    echo '{"bank_type":"universal_bank","net_income":12e9,"book_value":205e9}' | python -m banking
    python -m banking bank.json
    python -m banking --manifest
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
        with open(paths[0], encoding="utf-8") as fh:
            payload = json.load(fh)
    else:
        raw = sys.stdin.read().strip()
        payload = json.loads(raw) if raw else {}
    env = invoke(payload)
    print(json.dumps(env, indent=2))
    return 0 if env.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
