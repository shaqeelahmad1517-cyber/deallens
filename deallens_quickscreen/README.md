# DealLens Quick-Screen

A **fast indicative valuation** for triage (PRD feature F14). Give it an earnings
figure and a sector and it returns a ballpark value range in milliseconds — no
full financials, no checklist. Add an asking price and it tells you whether the
price looks **attractive, fair, or expensive**.

Use it to sift a pipeline quickly; run the full `orchestrator` on the ones worth
deep work.

Deterministic and pure. Depends only on the comparables library.

---

## Integration contract

```python
from quickscreen.primitive import MANIFEST, invoke
env = invoke({"earnings": 1010000, "sector": "logistics", "metric": "sde",
              "asking_price": 2500000})
env["result"]["range"]      # {"low":..., "high":..., "mid":...}
env["result"]["verdict"]    # below_range | within_range | above_range (if asking given)
```

### CLI

```bash
python -m quickscreen examples/example.json
echo '{"earnings":1010000,"sector":"logistics","asking_price":2500000}' | python -m quickscreen
python -m quickscreen --manifest
```

---

## Input

```jsonc
{
  "earnings": 1010000,        // required — the metric value (SDE or EBITDA)
  "metric": "sde",            // sde | ebitda | revenue (default sde)
  "sector": "logistics",      // required — comparables sector or alias
  "growth": "growing",        // optional — high | growing | flat | declining
  "size_ebitda": 830000,      // optional — defaults to earnings for sde/ebitda
  "top_customer_pct": 38,     // optional — auto risk flag
  "owner_dependent": true,    // optional — auto risk flag
  "risk_flags": [{"label":"...","severity":"high"}],  // optional explicit flags
  "asking_price": 2500000     // optional — triggers a verdict
}
```

## Output (inside `result`)

- `range` — indicative `{low, mid, high}`.
- `multiple_band_adjusted` — the sector multiple after size/growth and risk haircut.
- `risk_haircut` — total discount applied (capped at 40%).
- `verdict` / `verdict_note` / `vs_midpoint_pct` — only if `asking_price` given.
- `comparables` — the base band and modifiers used; `disclaimer`.

---

## How it works

1. Looks up the sector multiple band (size/growth-adjusted) via `deallens.comparables`.
2. Applies a light risk haircut from flags — high 12%, medium 5%, low 2% per flag
   (capped 40%), matching the valuation engine's risk defaults.
3. `range = earnings × adjusted multiple band`.
4. If an asking price is supplied: below the range → *potentially attractive*,
   within → *broadly fair*, above → *expensive*, plus % vs midpoint.

This is a deliberately simple, fast path — **not** the full DCF/triangulation
valuation. It's for go/no-go triage.

## Run it

```bash
python3 -m pytest -q              # 10 tests
python3 examples/run_example.py
```

Keep `deallens_comparables_library` side by side (or set `DEALLENS_HOME`).

## Boundaries

Indicative triage only — not a full valuation, and not financial, legal, or
valuation advice. Run the full pipeline before acting.
