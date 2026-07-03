# START HERE — DealLens Workspace

The workspace remembers your deals. It ties the five engines into one app:
create a deal, evaluate it, generate a report — and it all persists.

## First, every time: go to this folder

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_workspace"
```

On Mac use **`python3`**. Keep the other `deallens_*` folders side by side.

---

## See the whole lifecycle

```bash
python3 examples/run_example.py
```

Creates a deal → evaluates it (runs diligence + comparables + valuation) →
writes a report → lists your deals. Re-run it and the list grows — state sticks.

## Use it yourself

Create a deal from a JSON file of fields (copy the example's structure):

```bash
python3 -m workspace create my_deal_fields.json
```

That prints a deal `id`. Then:

```bash
python3 -m workspace evaluate <id>            # run the full pipeline, save the result
python3 -m workspace report   <id> --format html
python3 -m workspace list                     # see all your deals
python3 -m workspace get      <id>            # full deal record
```

For Word reports: `pip3 install python-docx`, then `--format docx`.

## Run the tests

```bash
python3 -m pytest -q
```

Should say `11 passed`.

---

## Where are my deals stored?

By default under `./data/deals` (JSON, one file per deal). To keep them
somewhere specific:

```bash
DEALLENS_DATA="/path/to/my/deals" python3 -m workspace list
```

Reports land in `<data>/reports/`.

## The actions at a glance

`create` · `get` · `list` · `update` · `delete` · `evaluate` · `report`

`evaluate` runs the orchestrator on the deal's saved inputs and stores the
result; `report` renders that result to a file (and auto-evaluates if you
haven't yet).

Decision-support only — not financial, legal, or valuation advice.
