"""CLI for assist.

    python -m assist draft_narrative result.json
    python -m assist suggest_adjustments ingestion.json
    python -m assist --manifest

The JSON file is the action's payload body (without the "action" key), or a full
payload including "action".
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
    pos = [a for a in argv if not a.startswith("-")]
    if not pos:
        print("usage: python -m assist <suggest_adjustments|draft_narrative> payload.json", file=sys.stderr)
        return 2
    action = pos[0]
    payload = {}
    if len(pos) > 1:
        with open(pos[1], "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Allow either a body or a full payload.
        payload = data if data.get("action") else dict(data, action=action)
        if action == "draft_narrative" and "result" not in payload and "action" not in data:
            payload = {"action": action, "result": data}
    else:
        payload = {"action": action}
    env = invoke(payload)
    print(json.dumps(env, indent=2))
    return 0 if env.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
