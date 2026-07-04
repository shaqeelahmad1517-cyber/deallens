# DealLens Banking

Values **financial institutions** (banks, insurers, lenders) the way they're
actually valued — on **price-to-book (P/B)** and **price-to-earnings (P/E)** — not
EBITDA or free-cash-flow DCF.

Why separate: for a bank, **interest is revenue, not a cost**, so "adding back
interest" to get EBITDA (what the standard engine does) is meaningless. Banks are
priced on their equity (book value) and net income.

## Use

```python
from banking.primitive import invoke
invoke({"bank_type": "universal_bank", "net_income": 12e9, "book_value": 205e9})
# book_value optional — derived from total_assets - total_liabilities if omitted
```

```bash
echo '{"bank_type":"universal_bank","net_income":12e9,"book_value":205e9}' | python -m banking
python -m banking --manifest
```

## Bank types & bands (illustrative)

| Type | P/B | P/E |
|------|-----|-----|
| universal_bank (money-center) | 0.6–1.2 | 8–13 |
| regional_bank | 1.0–1.6 | 9–13 |
| investment_bank | 0.9–1.6 | 8–12 |
| insurance | 0.8–1.5 | 8–14 |
| general_financial | 0.8–1.4 | 8–12 |

Aliases resolve (e.g. "citi", "jpmorgan" → universal_bank). Output blends the P/B
and P/E ranges, reports ROE, and skips P/E if the bank is loss-making.

## Run

```bash
python3 -m pytest -q     # 8 tests
```

Illustrative multiples; decision-support only, not financial advice.
