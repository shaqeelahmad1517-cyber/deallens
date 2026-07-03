# DealLens

A due-diligence and valuation platform, built as **eleven composable primitives**
for an AIOS spine. Feed in a target's financials (drop in an Excel/CSV/Word/PDF
statement, paste text, or import from QuickBooks/Xero), a diligence checklist, and
a sector — get back a defensible, risk-adjusted valuation and a client-ready
report, all persisted in a multi-user deal workspace with sharing and comments,
plus a fast quick-screen for triage and an assist that drafts the summary.

Every primitive shares one contract: a pure, deterministic `invoke(payload)` that
returns an `{"ok": bool, "result"|"error": ...}` envelope, plus a self-describing
`MANIFEST`. No I/O, no global state, no surprises — safe to register and chain.

---

## The eleven primitives

| # | Folder | Primitive | Does | Feeds |
|---|--------|-----------|------|-------|
| 1 | `deallens_valuation_engine/` | `deallens.valuation` | Normalization, DCF, capitalization, market multiples, NAV, triangulation, sensitivity | — |
| 2 | `deallens_diligence_engine/` | `deallens.diligence` | Checklist templates, completion, risk roll-up, red-flag detection | → valuation `risk_flags` |
| 3 | `deallens_comparables_library/` | `deallens.comparables` | Sector multiple bands with size/growth adjustments | → valuation `market` |
| 4 | `deallens_orchestrator/` | `deallens.orchestrator` | One call runs diligence → comparables → valuation | composes 1–3 |
| 5 | `deallens_report/` | `deallens.report` | Renders a result into HTML / Markdown / Word | consumes 4 (or 1) |
| 6 | `deallens_workspace/` | `deallens.workspace` | Persistent deal records: create/list/evaluate/report, lifecycle stages, history | composes 4 + 5 |
| 7 | `deallens_quickscreen/` | `deallens.quickscreen` | Fast indicative valuation for triage + asking-price verdict | consumes 3 |
| 8 | `deallens_documents/` | `deallens.documents` | Extract a financials block from a CSV/Excel/PDF/text statement | feeds 1, 6, 7 |
| 9 | `deallens_assist/` | `deallens.assist` | Rule-based assist: suggest add-backs (with rationale) + draft the valuation narrative | consumes 8, 4 |
| 10 | `deallens_accounts/` | `deallens.accounts` | User accounts + sessions (PBKDF2 hashing, stdlib) — powers multi-user auth | secures 6 |
| 11 | `deallens_integrations/` | `deallens.integrations` | QuickBooks/Xero OAuth + import financials (mock provider for local demos) | feeds 6, 1 |

Primitives 1–5 and 7–9 are pure and stateless; **6 and 10 are stateful** (they
persist to a store). Deals carry an owner, can be **shared** (viewer/editor) with
teammates, and support **comments** — enforced at the gateway via login sessions.
Primitive 9 is deterministic/rule-based (not an LLM), with a clean seam to add one.

Plus a clickable front end and a deployable gateway:

| Folder | What | Notes |
|--------|------|-------|
| `deallens_ui/` | Web app + API gateway over all primitives | Zero-dependency (stdlib HTTP server); `python3 run.py` → http://127.0.0.1:8765. Adds `/api/health` and `/api/manifests`. |

**Deploying:** the same server is container-ready. `Dockerfile` + `railway.toml`
build a one-container deployment; storage switches from JSON files to **SQLite**
via the `DEALLENS_DB` env var (a `Store` swap away from Postgres for multi-user).
See `DEPLOY.md` and `ROADMAP.md`.

Plus `DealLens_Concept_Architecture_Design_PRD.docx` — the product spec
(concept, architecture, design, PRD) the build is based on.

---

## How they connect

```
                 ┌─────────────────────────┐
                 │      ORCHESTRATOR        │   one invoke() in
                 │  (deallens.orchestrator) │
                 └────────────┬────────────-┘
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                       ▼
 ┌────────────┐        ┌──────────────┐        ┌──────────────┐
 │ DILIGENCE  │        │ COMPARABLES  │        │  VALUATION   │
 │ red_flags ─┼───────▶│ market band ─┼───────▶│  (the math)  │
 └────────────┘        └──────────────┘        └──────┬───────┘
        diligence findings + market comps              │
        both flow into the price ──────────────────────┘
                                                       ▼
                                              ┌──────────────┐
                                              │    REPORT     │  HTML / MD / Word
                                              │ client-ready  │
                                              └──────────────┘
```

- **Diligence → Valuation**: red flags become risk adjustments (shrink the
  multiple, raise the discount rate) — transparently.
- **Comparables → Valuation**: sector band (size/growth-adjusted) sets the market
  multiples instead of hardcoded numbers.
- **Orchestrator**: chains all three from one payload, with auto-derivation
  (size from financials, growth from the diligence signal) and graceful
  degradation if a step is missing or fails.
- **Report**: turns the result into a polished deliverable.

---

## Quick start

Use Python 3 (`python3` on macOS). Each folder has its own `START_HERE.md`.

**Run the whole thing from one call:**

```bash
cd deallens_orchestrator
python3 examples/run_example.py          # diligence + comparables + valuation
```

**Manage deals in the persistent workspace (create → evaluate → report → list):**

```bash
cd deallens_workspace
python3 examples/run_example.py
```

**Or just use the web app (no command line after launch):**

```bash
cd deallens_ui
python3 run.py            # open http://127.0.0.1:8765
```

**Generate a client-ready report end-to-end:**

```bash
cd deallens_report
pip3 install python-docx                  # one-time, enables Word output
python3 examples/run_example.py           # writes HTML / Markdown / Word
```

**Each primitive on its own:**

```bash
cd deallens_valuation_engine   && python3 examples/run_example.py
cd deallens_diligence_engine   && python3 examples/run_pipeline.py
cd deallens_comparables_library && python3 examples/run_full_pipeline.py
```

**Run every test suite:**

```bash
for d in deallens_valuation_engine deallens_diligence_engine \
         deallens_comparables_library deallens_orchestrator deallens_report \
         deallens_workspace deallens_quickscreen deallens_documents \
         deallens_assist deallens_accounts deallens_integrations \
         deallens_ui deallens_integration; do
  echo "== $d =="; (cd "$d" && python3 -m pytest -q); done
```

Expected: **202 tests passing** (19 + 17 + 13 + 10 + 13 + 27 + 12 + 38 + 10 + 13 + 11 + 13 + 6).
The last 6 are in `deallens_integration/` — an end-to-end fuzz/property suite that
runs ~1,470 randomized, deliberately-nasty deals (loss-making, insolvent, empty,
bad sectors, garbage numbers) through the whole pipeline and asserts invariants
(never crashes, envelopes well-formed, value ranges never negative or inverted).
Two extra cross-engine interlock tests — one each in the diligence and comparables
suites — `skip` when run standalone and `pass` when the valuation engine is on the
path (giving 156). To run those too, point Python at the valuation folder, e.g.:

```bash
cd deallens_diligence_engine
PYTHONPATH=../deallens_valuation_engine python3 -m pytest -q   # 18 passed
```

---

## Calling a primitive from the spine

```python
from orchestrator.primitive import invoke      # the one-call entrypoint

envelope = invoke({
    "target_name": "Northwind Logistics",
    "financials":  {"revenue": 4_200_000, "net_income": 520_000, "...": "..."},
    "checklist":   {"business_type": "smb", "items": [...], "signals": {...}},
    "comparables": {"sector": "logistics", "metric": "sde"},
})
result = envelope["result"]                     # diligence + comps + valuation + recommendation
```

Then render it:

```python
from report.primitive import invoke as render
html = render({"result": result, "format": "html"})["result"]["content"]
```

Each primitive is also a CLI: `python3 -m <package> --manifest` prints its
contract; `python3 -m <package> input.json` runs it.

### Layout the orchestrator expects

Keep the five `deallens_*` folders side by side (as they are here). The
orchestrator finds its siblings automatically, or set `DEALLENS_HOME` to their
parent directory.

---

## Design principles

- **Deterministic primitives** — pure functions; same input, same output.
- **Stable envelopes** — `invoke` never throws across the boundary.
- **Self-describing** — every primitive ships a `MANIFEST` with JSON I/O schemas.
- **Evidence over assertion** — every number traces to its inputs; risk
  adjustments and comp modifiers are always shown, never black-boxed.
- **Triangulate, don't false-precision** — outputs are ranges.
- **Decision-support, not advice** — DealLens informs decisions; it never
  transacts, moves money, or gives financial/legal/valuation advice.

---

## Status

All five primitives built, tested, and connected; full pipeline runs locally.
See each folder's `README.md` for its detailed contract and `START_HERE.md` for
copy-paste commands.
