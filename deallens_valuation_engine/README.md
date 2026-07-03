# DealLens Valuation Engine

A **deterministic, embeddable valuation primitive**. Given a target's financials,
normalization adjustments, diligence risk flags, and assumptions, it produces a
risk-adjusted, triangulated **value range** across the three standard valuation
approaches — with a full audit trail and sensitivity analysis.

Built to be dropped into an AIOS as a primitive and wired to the spine: it is a
**pure function** (no I/O, no global state, same input → same output) exposed
through a single `invoke(payload) → envelope` entrypoint and a self-describing
manifest.

---

## Why it's safe to embed

- **Deterministic** — the math modules are pure; `invoke` is reproducible.
- **No side effects** — no network, no disk, no clocks, no randomness.
- **Stable contract** — `invoke` never raises; it returns an `{ "ok": ... }` envelope.
- **Self-describing** — `MANIFEST` carries the JSON input/output schemas and capabilities.
- **Decision-support only** — outputs are ranges + evidence, never advice; never executes anything.

---

## Integration contract (the spine only needs this)

```python
from valuation_engine.primitive import MANIFEST, invoke

envelope = invoke(payload_dict)      # JSON-in → JSON-out, never raises
if envelope["ok"]:
    result = envelope["result"]
else:
    err = envelope["error"]          # {"type": ..., "message": ...}
```

- **Register** the primitive with `MANIFEST` (name `deallens.valuation`, entrypoint
  `valuation_engine.primitive:invoke`, input/output JSON schemas attached).
- **Call** it with a dict matching `MANIFEST["input_schema"]`.
- **Route** on `envelope["ok"]`.

### CLI / subprocess adapter

```bash
python -m valuation_engine examples/example_deal.json   # file in, envelope out
cat deal.json | python -m valuation_engine              # stdin in, envelope out
python -m valuation_engine --manifest                   # print the manifest
```

Exit code is `0` when `ok` is true, `1` otherwise — convenient for a process-based spine.

### Object handle (optional)

```python
from valuation_engine import ValuationEngine, Deal
eng = ValuationEngine()
result = eng.run_dict(payload)       # raises on bad input (use invoke for the safe envelope)
```

---

## Input shape

```jsonc
{
  "target_name": "Northwind Logistics",
  "financials": {
    "revenue": 4200000, "net_income": 520000,
    "interest": 40000, "taxes": 110000,
    "depreciation": 90000, "amortization": 20000,
    "owner_compensation": 180000,
    "total_assets": 1900000, "total_liabilities": 700000,
    "fair_value_adjustment": 50000,
    "base_free_cash_flow": null          // optional; else derived from EBITDA × fcf_conversion
  },
  "adjustments": [
    {"label": "Owner perks", "amount": 35000, "type": "add_back"},
    {"label": "One-off gain", "amount": 45000, "type": "deduction"}
  ],
  "risk_flags": [
    {"label": "Customer concentration", "severity": "high", "category": "Customers"}
  ],
  "income": {"discount_rate": 0.22, "growth_rate": 0.06, "terminal_growth": 0.025,
             "projection_years": 5, "long_term_growth": 0.025, "fcf_conversion": 0.65},
  "market": {"metric": "sde", "low_multiple": 3.0, "high_multiple": 5.0},
  "weights": {"income": 1.0, "market": 1.0, "asset": 0.5},
  "enabled_approaches": ["income", "market", "asset"]
}
```

Every field has a sensible default — the minimum viable call is just a `financials`
block and a `market.metric`.

## Output shape (inside `result`)

- `normalization` — reported EBITDA, adjustments total, normalized EBITDA, SDE.
- `risk` — cumulative multiple discount, discount-rate premium, per-flag detail.
- `approaches` — `income` (DCF + capitalization + range), `market` (multiple range), `asset` (NAV).
- `triangulation` — weighted range, floor, ceiling, weights used.
- `sensitivity` — value vs. discount rate and vs. market multiple.
- `recommended_range` — the headline `{low, mid, high}`.
- `disclaimer` — decision-support notice.

---

## Methodology

| Approach | Method | Notes |
|----------|--------|-------|
| Normalization | EBITDA from components + signed adjustments; SDE adds owner comp | Auditable build-up |
| Income | DCF (multi-stage + Gordon terminal value) and capitalization of earnings | Discount rate carries the risk premium |
| Market | Low/high comparable multiple on SDE, EBITDA, or revenue | Risk shrinks the multiple band |
| Asset | Net asset value (assets − liabilities ± fair-value adj.) | Floor / asset-heavy targets |
| Triangulation | Weighted blend of enabled approaches | Returns a range, never false precision |

Diligence **risk flags** transparently (a) shrink market multiples and (b) raise the
discount rate, with the applied deltas reported in `result["risk"]`. Cumulative
effects are capped (≤40% multiple discount, ≤10% rate premium).

---

## Layout

```
valuation_engine/
  models.py         # dataclasses + (de)serialization
  normalization.py  # EBITDA / SDE
  income.py         # DCF + capitalization
  market.py         # comparable multiples
  asset.py          # net asset value
  risk.py           # diligence flags → adjustments
  triangulation.py  # weighted blend
  engine.py         # pure orchestrator: run(Deal) → dict
  primitive.py      # MANIFEST + invoke() envelope  ← spine entrypoint
  __main__.py       # CLI / subprocess adapter
tests/test_engine.py
examples/example_deal.json, run_example.py
```

## Run it

```bash
python -m pytest -q          # 14 tests, known-value + contract checks
python examples/run_example.py
```

## Boundaries

Decision-support only. Outputs are based on user-supplied data and standard
methodologies — **not** financial, legal, or valuation advice. The engine does
not transact, move money, or fetch external data.
