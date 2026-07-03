# Connecting QuickBooks & Xero — Step by Step

The integration is **built and tested**. To switch it from the built-in demo
("mock") provider to the real thing, you register a developer app with each
provider, then set a few environment variables. No code changes.

Prerequisite: DealLens is deployed and has a public HTTPS URL (e.g. on Railway),
because OAuth redirects the user back to a URL that must be registered. Let's call
your URL `https://YOUR-APP.up.railway.app`.

---

## A. QuickBooks (Intuit)

1. **Create an Intuit Developer account** — go to `developer.intuit.com` and sign
   up (free).
2. **Create an app** — Dashboard → *Create an app* → choose the **QuickBooks
   Online Accounting** API.
3. **Get your keys** — open the app → *Keys & credentials*. You'll see a
   **Client ID** and **Client Secret** (there are separate Development and
   Production sets — start with Development / Sandbox).
4. **Add the redirect URI** — in the app's *Redirect URIs*, add exactly:
   ```
   https://YOUR-APP.up.railway.app/api/integrations/quickbooks/callback
   ```
5. **Scope** — the app must have the *Accounting* scope (already requested by
   DealLens: `com.intuit.quickbooks.accounting`).
6. **Sandbox company** — under *Sandbox*, Intuit gives you a test company with
   demo data. Use it to try the flow safely.

Then set these environment variables (in Railway → Variables):
```
QB_CLIENT_ID       = <your Development Client ID>
QB_CLIENT_SECRET   = <your Development Client Secret>
QB_API_BASE        = https://sandbox-quickbooks.api.intuit.com   # sandbox
# for production later: https://quickbooks.api.intuit.com
```

---

## B. Xero

1. **Create a Xero Developer account** — `developer.xero.com` → sign up (free).
2. **Create an app** — *My Apps* → *New app* → choose **Web app**.
3. **Fill in the app** — give it a name and your company URL. For **OAuth 2.0
   redirect URI**, add exactly:
   ```
   https://YOUR-APP.up.railway.app/api/integrations/xero/callback
   ```
4. **Get your keys** — open the app → *Configuration* → copy the **Client ID**
   and generate a **Client Secret**.
5. **Scopes** — DealLens requests
   `accounting.reports.read accounting.settings.read offline_access` (read-only +
   refresh). No extra config needed.
6. **Demo company** — in Xero you can use the built-in *Demo Company* to test.

Then set:
```
XERO_CLIENT_ID     = <your Client ID>
XERO_CLIENT_SECRET = <your Client Secret>
XERO_API_BASE      = https://api.xero.com
```

---

## C. One shared variable

Set the public base URL so the redirect URIs are built correctly:
```
DEALLENS_BASE_URL  = https://YOUR-APP.up.railway.app
```
Optionally set `DEALLENS_SECRET` to any long random string to obfuscate stored
tokens at rest.

---

## D. Try it

1. Redeploy so the new variables take effect.
2. In DealLens: **New deal** → in the auto-fill card you'll now see **Connect
   QuickBooks** / **Connect Xero** buttons (they appear once the provider is
   configured).
3. Click **Connect** → a popup sends you to the provider's login/consent screen →
   approve → the popup closes and the button flips to **Import from …**.
4. Click **Import** → DealLens pulls the Profit & Loss and Balance Sheet, maps the
   figures into the financial fields, and you review before creating the deal.

---

## Notes & honesty

- **Read-only.** DealLens only reads reports; it never writes to your books.
- **Report layouts vary.** QuickBooks/Xero let accounts customise report labels.
  The mappers match common labels (Total Income, Net Profit, Total Assets, …);
  if a figure doesn't import, check the label in your report and we can add it to
  the mapping. Verify imported numbers before relying on them.
- **Tokens.** Access/refresh tokens are stored per user so re-import doesn't need
  re-auth. In production, keep the database access restricted and set
  `DEALLENS_SECRET`. For higher assurance, move token storage to a secrets
  manager.
- **No accounts yet?** The built-in **Demo (mock)** provider runs the entire
  connect → import flow locally with sample data, so you can see exactly how it
  behaves before wiring the real ones.
