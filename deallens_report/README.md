# DealLens Report

The **last link in the spine**: turns an orchestrator (or valuation) result into
a polished, client-ready report.

- **HTML** — a standalone, styled, print-ready page (open in any browser, print to PDF). Zero dependencies.
- **Markdown** — clean text for emails, wikis, or further processing. Zero dependencies.
- **Word (.docx)** — optional, via `python-docx`.

Rendering is **pure** (returns the document as a string), so the primitive stays
deterministic and embeddable. Writing files is done at the edge (CLI / helper).

---

## Integration contract

```python
from report.primitive import MANIFEST, invoke
env = invoke({"result": orchestrator_result, "format": "html",
              "options": {"as_of": "June 2026", "prepared_by": "DealLens"}})
document_string = env["result"]["content"]   # the rendered HTML (or Markdown)
```

Accepts **either** an orchestrator result (with diligence + comparables sections)
**or** a bare valuation result (valuation-only report). It auto-detects the shape.

### Write files (CLI)

```bash
# result.json holds an orchestrator/valuation result (or an invoke envelope)
python -m report result.json --html report.html
python -m report result.json --md report.md
python -m report result.json --docx report.docx   # needs python-docx
python -m report result.json --html r.html --as-of "June 2026" --by "DealLens"
```

### Word output

```bash
pip install python-docx
```

Then `--docx` works, or call `report.write_docx(result, "out.docx", options)`.
Check availability programmatically with `report.docx_available()`.

### PDF

Open the HTML in a browser and **Print → Save as PDF** (the stylesheet is
print-optimized), or export the generated `.docx` to PDF from Word.

---

## What's in the report

- Header with DealLens branding, target name, as-of / prepared-by.
- **Recommended value range** (hero) with midpoint.
- Summary: normalized EBITDA, SDE, risk multiple cut, diligence completion.
- **Valuation approaches** table (DCF, capitalization, market band, NAV).
- **Comparables basis** (if present): sector, base band, applied multiple, modifiers.
- **Key risks**: diligence red flags with severity badges.
- **Sensitivity**: DCF vs. discount rate.
- Disclaimer.

---

## Layout

```
report/
  normalize.py    # accept orchestrator OR valuation result shape
  render.py       # pure build_html / build_markdown (DealLens styling)
  docx_writer.py  # optional Word output (python-docx)
  primitive.py    # MANIFEST + invoke() envelope  ← spine entrypoint
  __main__.py     # CLI: write --html/--md/--docx
tests/test_report.py
examples/run_example.py          # orchestrator -> report files
examples/sample_result.json      # fallback if engines aren't side by side
```

## Run it

```bash
python3 -m pytest -q              # 13 tests (docx test auto-skips if no python-docx)
python3 examples/run_example.py   # writes northwind_report.html / .md / .docx
```

## Boundaries

Decision-support only — the report presents user-supplied data and standard
methodologies; not financial, legal, or valuation advice.
