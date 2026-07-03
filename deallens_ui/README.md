# DealLens UI

A **local web app** that puts a clickable interface over the whole platform —
no command line needed. Create a deal, fill in the numbers, hit **Evaluate**, see
the value range and risks, and save a report.

Built on Python's standard-library HTTP server, so there is **nothing to install**.

---

## Run it

```bash
cd deallens_ui
python3 run.py            # then open http://127.0.0.1:8765
# or: python3 -m ui --port 9000
```

Keep the other `deallens_*` folders side by side (the UI drives the workspace,
which drives the engines).

---

## What you can do

- **Deal list** (left) — every saved deal with its stage and value range.
- **New deal** — a form for target name, business type, sector, financials, and a
  few risk signals (top-customer %, owner-dependent, revenue trend).
- **Evaluate** — runs diligence + comparables + valuation; shows the recommended
  range, the three approaches, and the key risks.
- **Reports** — save HTML, Word (needs `python-docx`), or Markdown; "View report"
  opens the rendered HTML in a new tab.
- **Delete** / stage tracking, all persisted.

Everything is stored by the workspace (JSON files), shared with the
`python -m workspace` CLI — deals made in one show up in the other.

---

## How it's built

```
ui/
  server.py        # http.server + handle_api(method, path, body) -> (status, payload, ctype)
  static/index.html# single-page app (vanilla JS, no build step)
  _deps.py         # find sibling engines
  __main__.py      # python -m ui
run.py             # convenience launcher
tests/test_ui.py
```

The API is a thin shell over the workspace primitive:

| Route | Action |
|-------|--------|
| `GET /api/meta` | sectors, business types, metrics, stages |
| `GET /api/deals` | list deals |
| `POST /api/deals` | create |
| `GET /api/deals/<id>` | get one |
| `PATCH /api/deals/<id>` | update (stage, notes) |
| `DELETE /api/deals/<id>` | delete |
| `POST /api/deals/<id>/evaluate` | run the pipeline |
| `POST /api/deals/<id>/report` | save a report file |
| `GET /api/deals/<id>/report` | view the report HTML inline |

`handle_api` is a plain function (returns `(status, payload, content_type)`), so
it's unit-tested without opening a socket.

## Run the tests

```bash
python3 -m pytest -q     # 6 tests (evaluate/report-view auto-skip if engines absent)
```

## Notes

- Local only — binds to `127.0.0.1`. It is a single-user convenience UI, not a
  hardened multi-user server.
- Data dir: `DEALLENS_DATA` if set, else the workspace default. Reports land in
  `<data>/reports/`.

Decision-support only — not financial, legal, or valuation advice.
