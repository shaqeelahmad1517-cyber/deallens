# Document Understanding — setup

The `understanding` primitive reads a **real-world business document** (annual report,
10-K, CIM, memo) and returns two things:

- **financials** — revenue, net income, interest, taxes, D&A, owner comp, total assets/liabilities
- **findings** — diligence red/amber flags a buyer should verify (customer/supplier
  concentration, going-concern language, litigation, key-person risk, covenants, …),
  plus a few pre-filled **risk signals** (top-customer %, revenue trend, owner-dependence).

It powers the **🧠 Read full report (AI)** button on the New Deal screen.

## Two modes (automatic)

| Mode | When | Quality |
|------|------|---------|
| **AI** | An API key is configured | Understands prose — the real thing. Handles full reports. |
| **Keyword scan** | No key, or the AI call fails | Deterministic fallback. Finds risk *phrases* and simple figures. Crude but never errors. |

You don't choose — it uses AI when a key is present and silently falls back otherwise, so
an upload always returns *something*.

## Turning on the AI mode

No new libraries to install (the client is pure standard library). Just set env vars.

**Anthropic (default):**

```
ANTHROPIC_API_KEY = sk-ant-…
```

**OpenAI instead:**

```
DEALLENS_LLM_PROVIDER = openai
OPENAI_API_KEY        = sk-…
```

**Optional:**

```
DEALLENS_LLM_MODEL = <model name>   # overrides the per-provider default
```

### On Railway

Project → **Variables** → add `ANTHROPIC_API_KEY` (same place as the DealLens/QuickBooks
secrets). Redeploy. That's it — the **🧠 Read full report (AI)** button switches from
keyword mode to AI mode automatically. `GET /api/manifests` shows `understanding.uses_llm: true`
once the key is live.

## Cost & limits

- Billed per document by your provider — roughly cents per report; large reports are
  truncated to ~120k characters (about a full statements-and-MD&A section).
- Every figure and finding is a **suggestion to confirm** against the source, not a
  verified fact — the output says so.

## CLI

```
python -m understanding path/to/report.pdf
python -m understanding --text "…document text…"
```
