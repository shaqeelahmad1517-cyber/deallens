# DealLens Diligence Engine

A **deterministic, embeddable due-diligence primitive**. Given a target's
business type and the reviewer's checklist state (plus structured "signals"),
it instantiates the right checklist template, rolls up **completion** and a
**category risk profile**, and detects **red flags** — both from item ratings
and automatically from signals.

Its red flags are emitted in the exact shape the **valuation engine** consumes,
so the two primitives interlock on the spine:

```
diligence.invoke(checklist) → red_flags → valuation.invoke(deal)
```

Same embedding contract as the valuation engine: a pure function (no I/O, no
global state) behind a single `invoke(payload) → envelope` entrypoint with a
self-describing `MANIFEST`.

---

## Integration contract

```python
from diligence_engine.primitive import MANIFEST, invoke
envelope = invoke(payload_dict)        # JSON in → JSON out, never raises
result = envelope["result"] if envelope["ok"] else None
```

The result includes `valuation_risk_flags` — drop it straight into the
valuation engine's input under `risk_flags`. Or use the explicit adapter:

```python
from diligence_engine import to_valuation_risk_flags
risk_flags = to_valuation_risk_flags(result)
```

### CLI / subprocess

```bash
python -m diligence_engine examples/example_checklist.json   # score a checklist
cat checklist.json | python -m diligence_engine              # stdin
python -m diligence_engine --manifest                        # print manifest
python -m diligence_engine --template saas                   # emit a blank template
```

---

## Input shape

```jsonc
{
  "target_name": "Northwind Logistics",
  "business_type": "smb",                 // general | smb | saas | retail
  "items": [
    {"id": "cust_concentration", "status": "flagged", "risk_rating": "high",
     "notes": "Top customer 38%", "evidence": ["sales_by_customer.xlsx"]}
  ],
  "signals": {                            // drive automatic red-flag detection
    "top_customer_pct": 38,
    "owner_dependent": true,
    "management_team_in_place": false,
    "revenue_trend": "growing",
    "clean_books": true,
    "customer_retention_pct": 82,
    "litigation_pending": false,
    "contracts_assignable": true,
    "taxes_current": true
  }
}
```

Item `status`: `not_started | in_progress | complete | flagged | na`.
Item `risk_rating`: `none | low | medium | high`.
All fields optional — the minimum call is just `{"business_type": "smb"}`.

## Output shape (inside `result`)

- `summary` — total items, completion %, overall risk level, red-flag count.
- `completion_pct` — weighted % of applicable items marked complete (NA excluded).
- `risk_profile` — per-category average risk score, level, and open-item count.
- `red_flags` — deduped, severity-sorted flags (label, severity, category, source).
- `valuation_risk_flags` — the same flags reduced to the valuation-engine contract.
- `items` — every instantiated checklist item with its state.

---

## How red flags are produced

1. **Item-level** — any item marked `flagged`, or rated `high`, becomes a flag
   (critical items escalate to `high`).
2. **Signal-level** — rules in `rules.py` inspect `signals` and emit flags, e.g.
   top customer ≥ 35% → high customer concentration; `owner_dependent` without a
   management team → high owner dependence; `clean_books: false` → high.
3. **Dedupe by concern** — item and signal flags that describe the *same* concern
   (via a shared `concern` key) collapse to one, keeping the highest severity, so
   the valuation engine never double-counts a risk.

Severities (`low/medium/high`) match the valuation engine's `RiskFlag`
severities, which is what makes the interlock clean.

---

## Templates

| Type | Adds on top of `general` |
|------|--------------------------|
| `general` | Base set across Financial, Commercial, Customers, Operations, People, Legal, Tax, Deal |
| `smb` | SDE add-backs, personal-vs-business expenses, lease assignability |
| `saas` | ARR/MRR, churn cohorts, code/IP ownership, security |
| `retail` | Lease terms, inventory, foot traffic, fixtures |

---

## Layout

```
diligence_engine/
  models.py        # dataclasses: items, states, checklist
  templates.py     # checklist templates by business type
  rules.py         # signal → red-flag rules
  engine.py        # pure orchestrator: run(Checklist) → dict (+ valuation adapter)
  primitive.py     # MANIFEST + invoke() envelope  ← spine entrypoint
  __main__.py      # CLI / subprocess adapter
tests/test_diligence.py
examples/example_checklist.json, run_pipeline.py   # ← interlock demo
```

## Run it

```bash
python3 -m pytest -q                 # 18 tests (incl. valuation interlock)
python3 examples/run_pipeline.py     # diligence → flags → valuation, end to end
```

> The interlock test/demo import `valuation_engine` from the sibling
> `deallens_valuation_engine/` folder. Keep both folders side by side.

## Boundaries

Decision-support only — a structured aid to investigation, not financial, legal,
or accounting advice. The engine does not transact or fetch external data.
