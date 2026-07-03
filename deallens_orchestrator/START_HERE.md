# START HERE — DealLens Orchestrator

The orchestrator runs **all three engines from one call**. Keep the four
`deallens_*` folders side by side.

## First, every time: go to this folder

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_orchestrator"
```

On Mac use **`python3`**. Copy commands one line at a time; don't paste `#` notes.

---

## The whole thing in one command

```bash
python3 examples/run_example.py
```

Sends one payload → runs diligence + comparables + valuation → prints a unified
deal evaluation with the recommended value range.

## Evaluate a deal from JSON (what your spine calls)

```bash
python3 -m orchestrator examples/example_deal.json
```

Prints the full JSON result (`{"ok": true, "result": {...}}`).

## Evaluate YOUR OWN deal

1. Copy the example:
   ```bash
   cp examples/example_deal.json my_deal.json
   ```
2. Edit `my_deal.json` — fill in `financials`, the `checklist` (items + signals),
   and `comparables.sector`. You can omit `checklist` or `comparables` and it
   still works.
3. Run it:
   ```bash
   python3 -m orchestrator my_deal.json
   ```

## Run the tests

```bash
python3 -m pytest -q
```

Should say `10 passed`.

---

## What one call gives you

| Section | Contents |
|---------|----------|
| `steps` | ok / failed / skipped for each engine |
| `diligence` | completion %, risk profile, red flags |
| `comparables` | sector multiple band actually used |
| `valuation` | full DCF / multiples / NAV / triangulation |
| `recommendation` | headline range, risk cut, key risks |

## If it can't find the engines

The orchestrator looks for the sibling `deallens_*` folders automatically. If
they live elsewhere, point it at their parent:

```bash
DEALLENS_HOME="/path/to/parent" python3 -m orchestrator my_deal.json
```

Decision-support only — not financial, legal, or valuation advice.
