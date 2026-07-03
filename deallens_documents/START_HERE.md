# START HERE — DealLens Documents

Stop typing financials by hand. Hand it a statement (CSV, Excel, text, or PDF)
and it pulls the numbers out for you to review.

## Easiest: use it in the web app

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_ui"
python3 run.py        # open http://127.0.0.1:8765, click "+ New deal"
```

On the new-deal form there's a **"📄 Paste financials to auto-fill"** box at the
top. Paste lines from a statement, click **Extract & fill**, and the financial
fields populate. Review them, then create the deal.

## Command line

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_documents"
python3 examples/run_example.py                 # ingest the sample CSV
python3 -m documents examples/sample_financials.csv
```

Your own files:

```bash
python3 -m documents /path/to/statement.csv      # or .xlsx, .txt
python3 -m documents /path/to/statement.pdf      # PDF: pip3 install pdfplumber first
```

Or pipe text in:

```bash
printf "Revenue 4,200,000\nNet income 520,000\n" | python3 -m documents
```

## What it handles

- Messy numbers: `$1,200,000`, `(45,000)` (negative), `1.5m`, `830k`
- Multi-year tables (takes the latest column)
- Flags likely owner perks / one-offs as add-backs to review
- Warns if it couldn't find revenue or net income

## Run the tests

```bash
python3 -m pytest -q     # 22 passed
```

For PDF support: `pip3 install pdfplumber`. For the xlsx **builder** in one test:
`pip3 install openpyxl` (reading xlsx needs nothing extra).

Always review the extracted numbers — it's a best-effort helper, not an audit.
Not advice.
