# DealLens Comparables Library

A **deterministic, embeddable comparables primitive**. Given a sector (and
optionally size and growth), it returns a **valuation multiple band**
(SDE / EBITDA / revenue) with transparent size and growth adjustments — so the
valuation engine stops relying on hardcoded multiples.

Its output plugs straight into the valuation engine's `market` block, the same
way diligence plugs into `risk_flags`:

```
comparables.invoke(query) → valuation_market → valuation.invoke(deal)
```

> **Data note:** the bundled dataset is **illustrative** — sensible default
> ranges for small/lower-midmarket private businesses, meant to be edited or
> replaced with your own proprietary comp data. It is not a live market feed.

---

## Integration contract

```python
from comparables.primitive import MANIFEST, invoke
envelope = invoke({"sector": "logistics", "metric": "sde",
                   "size_ebitda": 830000, "growth": "growing"})
market = envelope["result"]["valuation_market"]   # -> valuation input["market"]
```

Or the explicit adapter:

```python
from comparables import lookup, to_valuation_market, CompQuery
market = to_valuation_market(lookup(CompQuery(sector="saas", metric="revenue")))
```

### CLI / subprocess

```bash
python -m comparables examples/example_query.json
echo '{"sector":"saas","metric":"revenue"}' | python -m comparables
python -m comparables --sectors        # list sectors
python -m comparables --manifest
```

---

## Input

```jsonc
{
  "sector": "logistics",     // sector key or alias (e.g. "trucking")
  "metric": "sde",           // sde | ebitda | revenue
  "size_ebitda": 830000,     // optional — drives size premium/discount
  "growth": "growing"        // optional — high | growing | flat | declining
}
```

## Output (inside `result`)

- `sector_matched`, `metric`, `base_band` — the unmodified band from the dataset.
- `modifiers` — `size_factor`, `growth_factor`, `combined_factor`, and labels.
- `low_multiple` / `high_multiple` / `mid_multiple` — the adjusted band.
- `valuation_market` — `{metric, low_multiple, high_multiple}` for the valuation engine.
- `notes`, `source`, `disclaimer`.

---

## How adjustments work

Base band (from the sector dataset) × **size factor** × **growth factor**:

| Size (EBITDA) | Factor |  | Growth | Factor |
|---|---|---|---|---|
| < $250k | 0.85 |  | high | 1.15 |
| $250k–$1M | 1.00 |  | growing | 1.07 |
| $1M–$5M | 1.15 |  | flat | 1.00 |
| > $5M | 1.30 |  | declining | 0.85 |

Both are reported in `modifiers`, so the multiple is never a black box. Larger,
faster-growing businesses earn higher multiples — consistent with how the market
prices size and growth.

## Sectors

`general`, `logistics`, `saas`, `ecommerce`, `retail`, `restaurant`,
`manufacturing`, `professional_services`, `healthcare_services`, `construction`,
`home_services`, `distribution` (plus aliases like `trucking`, `software`,
`hvac`). Edit `comparables/dataset.py` to add your own.

---

## Layout

```
comparables/
  dataset.py     # seed sector multiple bands (edit/replace with your comps)
  models.py      # CompQuery dataclass
  engine.py      # lookup + size/growth modifiers (+ valuation adapter)
  primitive.py   # MANIFEST + invoke() envelope  ← spine entrypoint
  __main__.py    # CLI / subprocess adapter
tests/test_comparables.py
examples/example_query.json, run_full_pipeline.py   # ← 3-engine demo
```

## Run it

```bash
python3 -m pytest -q                     # 14 tests (incl. valuation interlock)
python3 examples/run_full_pipeline.py    # diligence + comps -> valuation, end to end
```

> The interlock test/demo import `valuation_engine` and `diligence_engine` from
> the sibling folders. Keep all three `deallens_*` folders side by side.

## Sources (reviewed 2026-07)

The bands are grounded in published benchmark data, not invented:

- **SMB (private) multiples** — BizBuySell transaction benchmarks (businesses
  actually sold, Q1 2021 – Q4 2025). Overall SDE multiple averages ~2.57×
  (range ~2.0–3.3×); revenue ~0.67×. Sector examples used: HVAC/home services
  ~2.6–3.0× SDE, landscaping ~1.8–3.1×, restaurants ~1.5–3.0×, construction
  ~2.9×, software/SaaS SDE avg ~3.4×.
- **Public (stock-market) EV/EBITDA** — NYU Stern / Damodaran industry data
  (Jan 2026) and industry aggregators. Public multiples run materially higher
  than private (commonly 30–50%+, far more for high-growth software; e.g. public
  SaaS ~15–35× EBITDA, healthcare services ~9–15×, manufacturing ~7–12×).

These are **researched aggregate ranges**, not deal-specific or a live feed —
a sound default. For a real transaction, replace the target's sector band with
vetted comps for that specific company. Reference pages:
bizbuysell.com/learning-center/industry-valuation-multiples,
pages.stern.nyu.edu/~adamodar (vebitda dataset).

## Boundaries

Decision-support only — illustrative ranges, not a market quote or financial
advice. Replace the seed dataset with vetted comps before relying on outputs.
