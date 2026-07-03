# DealLens Documents

**Document ingestion** (PRD feature F4): drop in a financial statement and get a
clean `financials` block out — no more typing numbers by hand. It reads the
line-item labels, parses the figures, flags likely add-backs, and tells you what
it couldn't find.

Reads **CSV, Excel (.xlsx), Word (.docx), plain text, and pasted text with zero
dependencies** (the xlsx and docx readers are pure standard library). **PDF**
works if `pdfplumber` or `pypdf` is installed. In the web app you can **upload a
file** (Excel/CSV/Word/PDF) or paste text — both hit the same extractor.

The extraction is **deterministic and best-effort + transparent**: it returns
what it matched, what it didn't, and warnings — for a human to confirm. It never
silently guesses a number into place.

---

## Integration contract

```python
from documents.primitive import MANIFEST, invoke

invoke({"path": "statement.csv"})            # a file
invoke({"text": "Revenue 4,200,000\n..."})   # pasted text
invoke({"csv_text": "Revenue,4200000\n..."})  # raw CSV
invoke({"rows": [["Revenue", 4200000]]})      # structured rows
```

Result `financials` plugs straight into the workspace / quick-screen / valuation.

### CLI

```bash
python -m documents statement.csv
python -m documents statement.xlsx
python -m documents statement.pdf      # needs pdfplumber or pypdf
cat statement.txt | python -m documents
python -m documents --manifest
```

---

## What it extracts

Canonical fields, matched by label synonyms: `revenue`, `net_income`, `interest`,
`taxes`, `depreciation`, `amortization`, `owner_compensation`, `total_assets`,
`total_liabilities`.

It also handles the silent-error cases that wreck real-world ingestion:

- **Scale detection** — spots "$ in thousands" / "in millions" and scales every
  figure accordingly (with a warning), instead of being 1,000× off.
- **Locale-aware numbers** — US *and* European formats: `1,234.50`, `1.234,56`,
  `1.234.567`, plus `$1,200,000`, `(45,000)` → −45000, `520000-`, unicode minus,
  `1.5m`, `830k`.
- **Signed losses** — "Net loss (300,000)" *and* "Net loss 300,000" both become
  −300,000.
- **Avoids field traps** — "Cost of sales", "Sales returns", "Other revenue",
  "Interest income", "Accumulated depreciation" don't get mis-mapped.
- **Ignores footnote/year cells** — won't pick a stray "3" or "2022" as the value;
  warns when multiple value columns (multi-year) are present.
- **Flags add-back candidates** — "Owner's vehicle", "One-time legal", etc.
- **Warns on gaps** — if revenue or net income wasn't found.

## Output (inside `result`)

- `financials` — the extracted block.
- `line_items` — each match with the original label it came from.
- `adjustment_candidates` — possible add-backs to review.
- `unmatched` — labels it didn't map.
- `warnings`, `source`, `disclaimer`.

---

## Layout

```
documents/
  extract.py    # pure core: number parser + label matcher (the IP)
  readers.py    # CSV/XLSX/TXT (stdlib) + optional PDF
  engine.py     # ingest(path|text|rows|csv_text) dispatch
  primitive.py  # MANIFEST + invoke() envelope  ← spine entrypoint
  __main__.py   # CLI
tests/test_documents.py
examples/sample_financials.csv, run_example.py
```

## Run it

```bash
python3 -m pytest -q              # 37 tests (one xlsx test needs openpyxl to build a fixture)
python3 examples/run_example.py
```

## Boundaries

Auto-extraction is a convenience, not an audit. **Review every figure before
use.** Not financial, legal, or accounting advice.
