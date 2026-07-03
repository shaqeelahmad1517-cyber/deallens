# START HERE — DealLens Report

Turns a deal evaluation into a client-ready report (HTML, Markdown, Word).

## First, every time: go to this folder

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_report"
```

On Mac use **`python3`**. Copy commands one line at a time; don't paste `#` notes.

---

## Generate a report end-to-end

```bash
python3 examples/run_example.py
```

This runs the full pipeline (orchestrator) and writes, in `examples/`:

- `northwind_report.html` — open in a browser; **Print → Save as PDF** for a PDF
- `northwind_report.md` — markdown version
- `northwind_report.docx` — Word version (if python-docx is installed)

## Enable Word output (one-time)

```bash
pip3 install python-docx
```

## Report from a saved result file

If you've saved an orchestrator/valuation result as `result.json`:

```bash
python3 -m report result.json --html report.html
python3 -m report result.json --docx report.docx
python3 -m report result.json --md report.md --as-of "June 2026" --by "Your Name"
```

## Run the tests

```bash
python3 -m pytest -q
```

Should say `13 passed` (the Word test auto-skips if python-docx isn't installed).

---

## Two ways the spine uses it

```python
from report.primitive import invoke
env = invoke({"result": orchestrator_result, "format": "html"})
html = env["result"]["content"]      # render in-memory (no file written)
```

Or write straight to disk with the CLI above.

It accepts **either** a full orchestrator result (with diligence + comparables)
**or** a plain valuation result — it figures out the shape automatically.

Decision-support only — not financial, legal, or valuation advice.
