"""CLI adapter for the report primitive.

    # result.json is an orchestrator or valuation result (the {"result": {...}} body)
    python -m report result.json --html report.html
    python -m report result.json --md report.md
    python -m report result.json --docx report.docx
    cat result.json | python -m report --html out.html
    python -m report --manifest

Input JSON may be either a raw result, or an envelope {"ok":true,"result":{...}}.
"""
from __future__ import annotations

import json
import sys

from . import docx_writer
from .primitive import manifest
from .render import render


def _load(paths):
    if paths:
        with open(paths[0], "r", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
    # Accept an envelope or a bare result.
    if isinstance(data, dict) and "result" in data and ("ok" in data or "engine" not in data):
        # could be an invoke envelope OR a report payload {"result":...}
        inner = data["result"]
        if isinstance(inner, dict):
            return inner
    return data


def _opt_value(argv, flag):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--manifest" in argv:
        print(json.dumps(manifest(), indent=2))
        return 0

    options = {}
    if _opt_value(argv, "--as-of"):
        options["as_of"] = _opt_value(argv, "--as-of")
    if _opt_value(argv, "--by"):
        options["prepared_by"] = _opt_value(argv, "--by")

    flags_with_args = {"--html", "--md", "--markdown", "--docx", "--as-of", "--by"}
    consumed = set()
    for f in flags_with_args:
        if f in argv:
            i = argv.index(f)
            consumed.add(i)
            consumed.add(i + 1)
    paths = [a for idx, a in enumerate(argv) if not a.startswith("-") and idx not in consumed]

    result = _load(paths)

    wrote = []
    html_out = _opt_value(argv, "--html")
    md_out = _opt_value(argv, "--md") or _opt_value(argv, "--markdown")
    docx_out = _opt_value(argv, "--docx")

    if html_out:
        with open(html_out, "w", encoding="utf-8") as fh:
            fh.write(render(result, "html", options))
        wrote.append(html_out)
    if md_out:
        with open(md_out, "w", encoding="utf-8") as fh:
            fh.write(render(result, "markdown", options))
        wrote.append(md_out)
    if docx_out:
        if not docx_writer.available():
            print("python-docx not installed; run: pip install python-docx", file=sys.stderr)
            return 2
        docx_writer.write_docx(result, docx_out, options)
        wrote.append(docx_out)

    if not wrote:
        # Default: print HTML to stdout.
        print(render(result, "html", options))
    else:
        for p in wrote:
            print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
