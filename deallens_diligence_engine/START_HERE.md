# START HERE — DealLens Diligence Engine

## First, every time: go to this folder

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_diligence_engine"
```

On Mac use **`python3`** (not `python`). Copy commands one line at a time;
don't paste the `#` notes.

---

## The star demo: the two engines connected

```bash
python3 examples/run_pipeline.py
```

This runs **diligence**, takes its red flags, and feeds them into the
**valuation** engine — so the price reflects what diligence found. (Keep the
`deallens_valuation_engine` folder next to this one for it to work.)

## Score a checklist on its own

```bash
python3 -m diligence_engine examples/example_checklist.json
```

## Get a blank checklist to fill in

```bash
python3 -m diligence_engine --template smb > my_checklist.json
```

Open `my_checklist.json`, set each item's `status` and `risk_rating`, fill in
the `signals`, then score it:

```bash
python3 -m diligence_engine my_checklist.json
```

## Run the tests

```bash
python3 -m pytest -q
```

Should say `18 passed` (includes the diligence→valuation interlock test).

---

## Business types

`general`, `smb`, `saas`, `retail` — pick with `--template <type>` or the
`business_type` field in your JSON.

## Reading the output

| Field | Meaning |
|-------|---------|
| `completion_pct` | Weighted % of applicable items marked complete |
| `risk_profile` | Risk level per category (Financial, Customers, …) |
| `red_flags` | Deduped, severity-sorted concerns |
| `valuation_risk_flags` | Same flags, ready to paste into the valuation engine |

Decision-support only — not financial, legal, or accounting advice.
