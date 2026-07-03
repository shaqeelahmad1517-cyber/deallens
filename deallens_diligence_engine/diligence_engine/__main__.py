"""CLI adapter for the diligence primitive.

    python -m diligence_engine examples/example_checklist.json
    cat checklist.json | python -m diligence_engine
    python -m diligence_engine --manifest
    python -m diligence_engine --template saas      # print a blank template
"""
from __future__ import annotations

import json
import sys

from .primitive import invoke, manifest
from .templates import get_template


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--manifest" in argv:
        print(json.dumps(manifest(), indent=2))
        return 0

    if "--template" in argv:
        i = argv.index("--template")
        bt = argv[i + 1] if i + 1 < len(argv) else "general"
        tmpl = get_template(bt)
        blank = {
            "target_name": "",
            "business_type": bt,
            "items": [{"id": t.id, "status": "not_started", "risk_rating": "none"} for t in tmpl],
            "signals": {},
        }
        print(json.dumps(blank, indent=2))
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
