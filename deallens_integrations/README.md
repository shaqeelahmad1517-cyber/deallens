# DealLens Integrations

Accounting integrations (PRD feature F13): connect **QuickBooks** or **Xero** and
**import financials** straight into a deal — no manual entry. A built-in **mock**
provider runs the whole flow locally with no accounts, so it's fully testable now.

OAuth 2.0 (authorization-code), pure standard library, injectable HTTP transport
(real network in production, a fake in tests).

> Setup for the real providers: see **`INTEGRATIONS_SETUP.md`** at the repo root.

---

## Flow

```
connect  -> authorize_url (user approves at provider)
callback -> exchange code for tokens, store per user
import   -> fetch P&L + Balance Sheet, map to a financials block
```

## Integration contract

```python
from integrations.primitive import invoke
invoke({"action": "list", "user_id": "u-1"})                       # providers + status
invoke({"action": "connect", "provider": "xero", "user_id": "u-1"}) # -> authorize_url
# ... provider redirects back to /callback, handled by the gateway ...
invoke({"action": "import", "provider": "xero", "user_id": "u-1"})  # -> financials
```

`invoke(payload, transport=...)` accepts an injectable transport for tests.

## Configuration (env vars, never in code)

| Provider | Vars |
|----------|------|
| QuickBooks | `QB_CLIENT_ID`, `QB_CLIENT_SECRET`, `QB_API_BASE` |
| Xero | `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`, `XERO_API_BASE` |
| Shared | `DEALLENS_BASE_URL` (for redirect URIs), `DEALLENS_SECRET` (token obfuscation) |

A provider is offered in the UI only when its client id/secret are set. The
`mock` provider is always available.

## Layout

```
integrations/
  providers.py  # QB/Xero/mock configs + env-based credentials
  oauth.py      # authorize_url / exchange_code / refresh (injectable transport)
  client.py     # fetch P&L + Balance Sheet, map to financials (QB/Xero/mock)
  store.py      # per-user tokens + OAuth state (SQLite/JSON, obfuscated at rest)
  engine.py     # connect / callback / import / disconnect
  primitive.py  # MANIFEST + invoke()  ← spine entrypoint
tests/test_integrations.py   # mock end-to-end + QB/Xero mapper fixtures
```

## Run it

```bash
python3 -m pytest -q     # 11 tests, no network (injected transport)
```

## Boundaries

Read-only — never writes to your books. Report layouts vary by account; verify
imported figures before use. Not financial advice.
