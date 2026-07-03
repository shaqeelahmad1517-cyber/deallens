# DealLens Workspace

The **deal workspace** (PRD feature F1): a persistent layer that turns the five
stateless engines into a coherent app. It creates deals, remembers their inputs,
runs evaluation + report on demand, tracks lifecycle stage, and keeps a history —
all under one deal id.

This is the platform's first **stateful** primitive: it has side effects (it
writes to a store) and composes the orchestrator + report primitives.

---

## What a deal holds

```
id · target_name · stage · created_at · updated_at
inputs:   financials · adjustments · checklist · comparables · options · notes
outputs:  last_evaluation · reports[] · history[]
```

Stages: `sourced → screening → diligence → valuation → decision → closed`.

---

## Integration contract

```python
from workspace.primitive import MANIFEST, invoke

invoke({"action": "create", "deal": {"target_name": "Acme", "financials": {...},
                                      "checklist": {...}, "comparables": {...}}})
invoke({"action": "evaluate", "id": "acme-1a2b3c4d"})   # runs the full pipeline, stores result
invoke({"action": "report",   "id": "acme-1a2b3c4d", "format": "html"})
invoke({"action": "list"})
```

`invoke` dispatches on `action` and returns the usual `{"ok": ...}` envelope.

| Action | Needs | Does |
|--------|-------|------|
| `create` | `deal` | New deal (auto id from target name); returns the record |
| `get` | `id` | Load a deal |
| `list` | — | Summaries of all deals |
| `update` | `id`, `deal` | Patch fields / advance stage |
| `delete` | `id` | Remove a deal |
| `evaluate` | `id` | Run orchestrator on stored inputs; persist result; advance stage |
| `report` | `id` | Render latest evaluation to a file (auto-evaluates if needed) |

### CLI

```bash
python -m workspace create deal_fields.json
python -m workspace list
python -m workspace evaluate <id>
python -m workspace report <id> --format html
python -m workspace get <id>
python -m workspace delete <id>
python -m workspace --manifest
```

---

## Where data lives

One JSON file per deal. Resolution order:

1. `store_root` in the payload (handy for tests / multi-tenant), else
2. `DEALLENS_DATA` environment variable, else
3. `./data/deals` beside the package.

Reports are written under `<store_root>/reports/<id>.<ext>`.

Because it's just files, deals survive between runs and processes — point a new
store at the same root and the deals are there.

---

## Requires the engine folders side by side

`evaluate` and `report` import `orchestrator` and `report`, which in turn need
the three engines. Keep all `deallens_*` folders together (or set `DEALLENS_HOME`
to their parent). CRUD actions work without them.

---

## Layout

```
workspace/
  models.py     # Deal record (+ summary)
  store.py      # JSONFileStore (swappable)
  _deps.py      # find sibling engines
  engine.py     # actions: create/get/list/update/delete/evaluate/report
  primitive.py  # MANIFEST + invoke() action dispatch  ← spine entrypoint
  __main__.py   # CLI
tests/test_workspace.py
examples/run_example.py    # full lifecycle demo
```

## Run it

```bash
python3 -m pytest -q              # 11 tests (evaluate/report auto-skip if engines absent)
python3 examples/run_example.py   # create -> evaluate -> report -> list
```

## Boundaries

Decision-support only. Stores and organizes deal data; does not transact or give
financial/legal/valuation advice.
