# DealLens Orchestrator

The **spine primitive**: one `invoke()` call runs the whole deal evaluation by
chaining the three engines internally —

```
diligence.invoke(checklist) --> red_flags ----\
                                                >--> valuation.invoke(deal) --> result
comparables.invoke(query)  --> market band ---/
```

Your AIOS sends a single payload (financials + checklist + sector) and gets back
a unified evaluation: diligence summary, comparable multiples, full valuation,
and a top-line recommendation.

Same embedding contract as the other primitives: pure, deterministic,
`invoke(payload) → {"ok": ...}` envelope, self-describing `MANIFEST`.

---

## Requires the three engines side by side

```
Financial Analysis/
  deallens_valuation_engine/
  deallens_diligence_engine/
  deallens_comparables_library/
  deallens_orchestrator/        ← this one
```

The orchestrator locates its siblings automatically. If your layout differs, set
`DEALLENS_HOME` to the folder that contains the `deallens_*` directories.

---

## Integration contract

```python
from orchestrator.primitive import MANIFEST, invoke
envelope = invoke(payload_dict)        # one call -> full evaluation
result = envelope["result"] if envelope["ok"] else None
```

### CLI / subprocess

```bash
python -m orchestrator examples/example_deal.json
cat deal.json | python -m orchestrator
python -m orchestrator --manifest
```

---

## Input (one payload)

```jsonc
{
  "target_name": "Northwind Logistics",
  "financials": { "revenue": 4200000, "net_income": 520000, "...": "..." },
  "adjustments": [ {"label": "Owner perks", "amount": 35000, "type": "add_back"} ],
  "checklist": {                      // -> diligence engine
    "business_type": "smb",
    "items": [ {"id": "cust_concentration", "status": "flagged", "risk_rating": "high"} ],
    "signals": { "top_customer_pct": 38, "owner_dependent": true, "revenue_trend": "growing" }
  },
  "comparables": { "sector": "logistics", "metric": "sde" },   // -> comparables engine
  "market": { "...": "..." },         // optional fallback if comparables omitted/fails
  "income": { "...": "..." },         // optional valuation assumptions
  "weights": { "...": "..." },
  "enabled_approaches": ["income", "market", "asset"]
}
```

`checklist` and `comparables` are both optional — omit either and the
orchestrator skips that step and proceeds.

### Auto-derivation

- **Size**: if `comparables.size_ebitda` is missing, it's inferred from
  `financials` (+ adjustments) so the size premium applies automatically.
- **Growth**: if `comparables.growth` is missing, it's taken from the diligence
  `signals.revenue_trend`.

## Output (inside `result`)

- `steps` — ok/failed/skipped status for each engine.
- `warnings` — any graceful-degradation notes.
- `diligence`, `comparables`, `valuation` — each engine's full result.
- `recommendation` — `range`, `headline`, `risk_multiple_discount`, `key_risks`,
  `diligence_completion_pct`.

---

## Graceful degradation

| Situation | Behavior |
|-----------|----------|
| `checklist` omitted | Skips diligence; valuation runs with no risk flags |
| Diligence fails | Warning recorded; proceeds with no risk flags |
| `comparables` omitted | Uses explicit `market`, else valuation's default band |
| Comparables fails (e.g. bad sector) | Warning recorded; falls back to `market`/default |
| Valuation fails | Overall `ok: false` with the underlying error |

Only a valuation failure (or missing engine packages) produces an overall error.

---

## Layout

```
orchestrator/
  _deps.py      # finds sibling engine packages (honors DEALLENS_HOME)
  engine.py     # the pipeline: run(payload) -> unified result
  primitive.py  # MANIFEST + invoke() envelope  ← spine entrypoint
  __main__.py   # CLI / subprocess adapter
tests/test_orchestrator.py
examples/example_deal.json, run_example.py
```

## Run it

```bash
python3 -m pytest -q                 # 10 tests incl. graceful-degradation
python3 examples/run_example.py      # one call -> full evaluation
```

## Boundaries

Decision-support only. Aggregates user-supplied data through standard
methodologies; not financial, legal, or valuation advice. Does not transact.
