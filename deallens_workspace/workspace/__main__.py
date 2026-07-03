"""CLI for the workspace primitive.

    python -m workspace create deal.json        # create from a JSON file of fields
    python -m workspace list
    python -m workspace get  <id>
    python -m workspace evaluate <id>
    python -m workspace report <id> --format html
    python -m workspace delete <id>
    python -m workspace --manifest

Data lives under ./data/deals by default; override with DEALLENS_DATA.
"""
from __future__ import annotations

import json
import sys

from .primitive import invoke, manifest


def _read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--manifest" in argv:
        print(json.dumps(manifest(), indent=2))
        return 0
    if not argv:
        print("usage: python -m workspace <create|list|get|update|delete|evaluate|report> ...", file=sys.stderr)
        return 2

    action = argv[0]
    rest = argv[1:]

    def opt(flag, default=None):
        return rest[rest.index(flag) + 1] if flag in rest and rest.index(flag) + 1 < len(rest) else default

    payload = {"action": action}
    positional = [a for a in rest if not a.startswith("-")]
    # strip values that belong to flags
    for flag in ("--format", "--out-dir", "--store-root"):
        if flag in rest:
            i = rest.index(flag)
            if i + 1 < len(rest) and rest[i + 1] in positional:
                positional.remove(rest[i + 1])

    if action in ("create", "update") and positional:
        payload["deal"] = _read_json(positional[0])
        positional = positional[1:]
    if action in ("get", "update", "delete", "evaluate", "report") and positional:
        payload["id"] = positional[0]
    if opt("--format"):
        payload["format"] = opt("--format")
    if opt("--out-dir"):
        payload["out_dir"] = opt("--out-dir")
    if opt("--store-root"):
        payload["store_root"] = opt("--store-root")

    env = invoke(payload)
    print(json.dumps(env, indent=2))
    return 0 if env.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
