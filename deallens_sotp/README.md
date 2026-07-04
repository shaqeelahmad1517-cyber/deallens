# DealLens Sum-of-the-Parts (SOTP)

Values **conglomerates** — companies with multiple distinct businesses (Amazon =
ecommerce + AWS + ads; a holding company; a diversified industrial). A single
sector multiple can't capture them, because each division earns different margins
and deserves a different multiple.

SOTP values **each segment on its own sector comp**, sums them, applies a
**conglomerate/holdco discount**, and subtracts **net debt**.

Composes the comparables primitive (one lookup per segment).

## Use

```python
from sotp.primitive import invoke
invoke({
  "segments": [
    {"name": "AWS",    "sector": "saas",      "metric": "ebitda",  "tier": "public", "earnings": 40e9, "growth": "growing"},
    {"name": "Retail", "sector": "ecommerce", "metric": "revenue", "tier": "public", "earnings": 400e9},
    {"name": "Ads",    "sector": "saas",      "metric": "ebitda",  "tier": "public", "earnings": 20e9, "growth": "high"}
  ],
  "conglomerate_discount": 0.10,
  "net_debt": 0
})
```

```bash
python -m sotp conglomerate.json
python -m sotp --manifest
```

## Output

- `segments` — each segment's sector, multiple, and value range.
- `gross_enterprise_range` — sum of segment values.
- `equity_range` — after the holdco discount and net-debt bridge.

## Run

```bash
python3 -m pytest -q     # 8 tests (needs the comparables library alongside)
```

Illustrative; decision-support only, not financial advice.
