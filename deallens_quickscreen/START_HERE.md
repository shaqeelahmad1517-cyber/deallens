# START HERE — DealLens Quick-Screen

A fast ballpark valuation for triaging deals. Earnings + sector → indicative
range in a flash. Add an asking price for a go/no-go read.

## Easiest: use it in the web app

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_ui"
python3 run.py        # open http://127.0.0.1:8765, click "⚡ Quick screen" (top right)
```

## Command line

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_quickscreen"
python3 examples/run_example.py
```

Or screen your own numbers directly:

```bash
echo '{"earnings":1010000,"sector":"logistics","metric":"sde","asking_price":2500000}' | python3 -m quickscreen
```

## What you give it

- **earnings** (required) — SDE or EBITDA figure
- **sector** (required) — e.g. logistics, saas, retail, manufacturing
- optional: metric, growth, top-customer %, owner-dependent, asking price

## What you get

An indicative low–high range, the multiple used, the risk haircut applied, and —
if you gave an asking price — whether it's **below / within / above** the range.

## Run the tests

```bash
python3 -m pytest -q     # 10 passed
```

Keep `deallens_comparables_library` side by side. This is triage only — run the
full evaluation (orchestrator / workspace) before deciding. Not advice.
