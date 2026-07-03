# START HERE — DealLens Comparables Library

## First, every time: go to this folder

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_comparables_library"
```

On Mac use **`python3`**. Copy commands one line at a time; don't paste `#` notes.

---

## The star demo: all THREE engines connected

```bash
python3 examples/run_full_pipeline.py
```

Runs **diligence** (→ risk flags) and **comparables** (→ market multiples), then
feeds both into the **valuation** engine. Keep the other two `deallens_*` folders
next to this one for it to work.

## Look up a multiple band

```bash
python3 -m comparables examples/example_query.json
```

## See available sectors

```bash
python3 -m comparables --sectors
```

## Quick one-liner

```bash
echo '{"sector":"saas","metric":"revenue","growth":"high"}' | python3 -m comparables
```

## Run the tests

```bash
python3 -m pytest -q
```

Should say `14 passed` (includes the comparables→valuation interlock test).

---

## Edit the multiples to your own data

Open `comparables/dataset.py` and change the `sde` / `ebitda` / `revenue` bands,
or add new sectors. The bundled numbers are **illustrative defaults**, not a live
market feed — replace them with your vetted comps.

## Reading the output

| Field | Meaning |
|-------|---------|
| `base_band` | The unmodified multiple range for the sector |
| `modifiers` | Size and growth factors applied (fully transparent) |
| `low/high/mid_multiple` | The adjusted multiple band |
| `valuation_market` | Ready to paste into the valuation engine's `market` block |

Decision-support only — illustrative ranges, not a market quote or advice.
