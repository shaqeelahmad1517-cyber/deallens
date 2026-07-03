# START HERE — DealLens Assist

A helper that suggests normalization add-backs (with reasons) and auto-drafts a
plain-English valuation summary. Everything is for you to review.

> It's deterministic/rule-based, not a large language model — reproducible and
> with nothing to install. The rules are the seam where a real LLM could slot in.

## Easiest: in the web app

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_ui"
python3 run.py        # open http://127.0.0.1:8765
```

Open a deal, click **Evaluate**, then click **✦ Draft summary** to get a written
summary of the valuation.

## Command line

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_assist"
python3 examples/run_example.py
```

That prints suggested add-backs (with rationale + confidence) and a drafted
narrative.

### Use your own data

```bash
# Suggest add-backs from a documents-primitive result saved as ingestion.json
python3 -m assist suggest_adjustments ingestion.json

# Draft a narrative from an evaluation result saved as result.json
python3 -m assist draft_narrative result.json
```

## Run the tests

```bash
python3 -m pytest -q     # 10 passed
```

Always review and edit suggestions and summaries before sharing — decision-support
only, not advice.
