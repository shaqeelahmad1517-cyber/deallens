# START HERE — DealLens Valuation Engine

## First, every time: go to this folder

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_valuation_engine"
```

All commands below must be run from here. On Mac, use **`python3`** (not `python`).

> Tip: copy commands **one line at a time**. Don't paste the `#` notes — those are
> comments for you, and the terminal will choke on the `#`.

---

## The three things you can do

### 1. Run the built-in example (simplest)
```bash
python3 examples/run_example.py
```
Prints a readable valuation summary for the sample deal.

### 2. Value a deal from a JSON file (what your AIOS spine calls)
```bash
python3 -m valuation_engine examples/example_deal.json
```
Prints the full JSON result (`{"ok": true, "result": {...}}`).

### 3. Run the tests (confirm nothing's broken)
```bash
python3 -m pytest -q
```
Should say `14 passed`.

---

## Value YOUR OWN business

1. Copy the example file:
   ```bash
   cp examples/example_deal.json my_deal.json
   ```
2. Open `my_deal.json` in any text editor and change the numbers
   (revenue, net_income, owner_compensation, multiples, risk flags, etc.).
3. Run it:
   ```bash
   python3 -m valuation_engine my_deal.json
   ```

The only required parts are a `financials` block and `market.metric`
(`"sde"`, `"ebitda"`, or `"revenue"`). Everything else has sensible defaults.

---

## Reading the output

| Field | What it tells you |
|-------|-------------------|
| `normalization` | Cleaned-up earnings: normalized EBITDA and SDE |
| `risk` | How diligence red flags lowered the multiple / raised the discount rate |
| `approaches` | Each method's value (DCF, capitalization, market multiple, asset/NAV) |
| `sensitivity` | How value moves as discount rate and multiple change |
| `recommended_range` | The headline `{low, mid, high}` value range |

## Use it from the spine (Python)
```python
from valuation_engine.primitive import MANIFEST, invoke
envelope = invoke(payload_dict)   # JSON in -> JSON out, never raises
result = envelope["result"] if envelope["ok"] else None
```

Decision-support only — not financial, legal, or valuation advice.
