# DealLens Assist

**AI assist** (PRD feature F11), built as a deterministic, rule-based helper that
does the judgment-support work a human then approves:

- **Suggest add-backs** — turns the flagged lines from document ingestion into
  proposed normalization adjustments, each with a plain-English rationale and a
  confidence level.
- **Draft a narrative** — composes a plain-English valuation summary from an
  evaluation result (the range, what drove it, the risks, the comparables basis,
  and a caveat).

> **Honest scope:** this is **not a large language model** — it's deterministic
> and template/rule-driven (`uses_llm: false` in the manifest). That keeps it
> reproducible and dependency-free. The rule tables and templates are the clean
> seam where an LLM could later be substituted.

Everything it produces is **for review** — it proposes, the human disposes.

---

## Integration contract

```python
from assist.primitive import MANIFEST, invoke

# 1. Suggest add-backs from a documents-primitive result
invoke({"action": "suggest_adjustments", "ingestion": documents_result})

# 2. Draft a narrative from an orchestrator/valuation result
invoke({"action": "draft_narrative", "result": evaluation_result,
        "options": {"format": "markdown"}})
```

### CLI

```bash
python -m assist suggest_adjustments ingestion.json
python -m assist draft_narrative result.json
python -m assist --manifest
```

---

## suggest_adjustments

Input: a documents result (`ingestion`) or an explicit `adjustment_candidates`
list + `financials`.

Output `suggestions[]`, each: `label`, `amount`, `type` (`add_back`),
`rationale`, `confidence` (high/medium/low), `status` (`suggested`). Plus
contextual `notes` (e.g. owner-comp treatment for SDE vs EBITDA).

Confidence comes from keyword rules — "one-time/legal/settlement" and
"owner/personal/vehicle" score **high**; vaguer lines score **low** so you know
what to scrutinize.

## draft_narrative

Input: an orchestrator result or a bare valuation result (auto-detected) and an
optional `format` (`markdown` or `text`).

Output: a `narrative` string — headline range, the approaches behind it,
normalized earnings, comparables basis (if present), the key risks and the
multiple discount they caused, diligence completeness, and a decision-support
caveat.

---

## Layout

```
assist/
  adjustments.py  # rule-based add-back suggestions (the rule table)
  narrative.py    # deterministic narrative template
  primitive.py    # MANIFEST + invoke() action dispatch  ← spine entrypoint
  __main__.py     # CLI
tests/test_assist.py
examples/run_example.py
```

## Run it

```bash
python3 -m pytest -q              # 10 tests
python3 examples/run_example.py
```

In the web app, evaluate a deal and click **✦ Draft summary** on its page.

## Boundaries

Suggestions and summaries are decision-support only — review, edit, or reject
before use. Not financial, legal, or valuation advice.
