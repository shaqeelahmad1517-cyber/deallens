# START HERE — DealLens UI

The clickable version of DealLens. No command line needed once it's running.

## Start the app

```bash
cd "/Users/mohammadrusdianto/Claude/Projects/Financial Analysis/deallens_ui"
python3 run.py
```

Then open this in your browser:

```
http://127.0.0.1:8765
```

Keep the other `deallens_*` folders side by side. To stop the app, press
**Ctrl+C** in the terminal. To use a different port: `python3 run.py --port 9000`.

---

## Using it

1. Click **+ New deal** (top left).
2. Enter a target name, pick a business type and sector, and type in the
   financials you have (revenue and net income are enough to start).
3. Optionally add risk signals (top-customer %, owner-dependent, revenue trend).
4. Click **Create deal**, then **Evaluate** — you'll see the recommended value
   range, the valuation approaches, and the key risks.
5. Click **Save HTML report** (or Word/Markdown), or **View report** to open it
   in a new tab. Print → Save as PDF from there for a PDF.

For Word reports: `pip3 install python-docx` once, then the Word button works.

---

## Where deals are stored

Same place the `workspace` CLI uses, so they're shared. To pick a location:

```bash
DEALLENS_DATA="/path/to/my/deals" python3 run.py
```

## Run the tests

```bash
python3 -m pytest -q          # 6 passed
```

## Good to know

- Runs **locally only** (127.0.0.1) — it's a personal tool, not a public server.
- Nothing to install for the app itself (pure Python standard library).

Decision-support only — not financial, legal, or valuation advice.
