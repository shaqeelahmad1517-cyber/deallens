# DealLens — How to Continue (Roadmap)

Everything built so far runs **locally on one machine**: nine primitives, a web
UI, 154 tests. The remaining PRD items (F9 collaboration, F13 integrations, F15
mobile, F16 deployment) are no longer "more Python in a folder" — they need a
running service, a database, accounts with third parties, and hosting decisions.

This doc splits the path into (A) what can still be built locally to bridge
toward production, and (B) the infrastructure work that needs your decisions and
external accounts. Do them roughly in this order.

---

## The core shift: from scripts to a service

Right now each primitive is a Python package you call directly, and state is JSON
files. To support multiple users, integrations, and hosting, three things change:

1. **One API gateway** — wrap all primitives behind a single web service so a
   browser, a phone, or a partner system can call them over HTTP.
2. **A real database** — replace the JSON file store with SQLite (local) →
   Postgres (hosted) so many users and deals coexist safely.
3. **Accounts + auth** — identity, so deals belong to users and teams.

Everything in Part B depends on these three.

---

## Part A — Buildable now, locally (bridges toward production)

These need no external accounts; they can be built and tested here, and they
de-risk the infra work.

1. **API gateway (FastAPI or Flask).** One service that mounts every primitive's
   `invoke` behind REST endpoints and serves each `MANIFEST`. Turns the current
   ad-hoc UI server into a proper API. *Effort: small–medium.*
2. **Swap the store to SQLite.** Same `JSONFileStore` interface, backed by a real
   database file. Keeps everything local but makes the multi-user jump trivial
   later (SQLite → Postgres is a connection-string change). *Effort: small.*
3. **Dockerfile + docker-compose.** Package the whole platform so it runs the same
   on any machine or host with one command. The prerequisite for every hosting
   option. *Effort: small.*
4. **Auth scaffold.** A pluggable "current user" seam (stubbed locally, real
   provider later) plus per-user deal ownership in the store. *Effort: medium.*

Recommended: do 1–3 first (they’re quick and unlock the rest), then 4.

---

## Part B — Needs your decisions / external accounts

### F16 — Deployment (do this first of Part B; it enables the others)
- **Decision:** where it runs — a single VM (DigitalOcean/EC2), a container
  platform (Render, Fly.io, Railway, Google Cloud Run), or your own server.
- **Decision:** single-tenant (one private install per firm) vs multi-tenant (one
  app, many customers). The PRD supports both; multi-tenant needs stricter data
  isolation.
- **Needs:** a hosting account, a domain, HTTPS certs (usually automatic on
  managed platforms), a managed Postgres instance.
- I can produce the deploy config for a chosen target once you pick one.

### F9 — Collaboration
- **Depends on:** service + database + auth (Part A) and hosting (F16).
- **Work:** user accounts and teams, deal sharing/permissions, comments, task
  assignment, activity feed. Optionally real-time updates (WebSockets).
- **Decision:** how much real-time you need (live cursors vs. simple refresh).

### F13 — Integrations (each is an independent OAuth/app project)
- **Accounting (QuickBooks / Xero):** register a developer app with each, do
  OAuth, map their account data to the `documents`/`financials` shape. *This is
  the highest-value integration — it removes manual financial entry entirely.*
- **Cloud storage (Google Drive / Dropbox / Box):** OAuth app + file pickers to
  pull statements into `documents`.
- **SSO (SAML/OIDC via Okta, Google Workspace, Azure AD):** for enterprise login;
  usually via a library (e.g. Authlib) + an identity-provider config.
- **Needs:** a developer account and app registration per provider, plus secret
  management.

### F11 — AI assist (upgrade path)
- Already shipped as a deterministic assistant. To upgrade to a real LLM: add an
  API key (e.g. Anthropic), and swap the rule tables in `deallens_assist` behind
  the same `invoke` contract. The seam is already there. *Needs: an API key.*

### F15 — Mobile
- Lowest priority. The web UI is already browser-based; options are (a) make it
  fully responsive/installable as a PWA, or (b) a thin native wrapper, or (c) a
  React Native app against the same API. Do this last.

---

## Decisions to make before Part B

1. **Hosting target?** (managed platform vs VM vs on-prem)
2. **Single-tenant or multi-tenant?**
3. **Database:** Postgres is the safe default — confirm.
4. **Auth/identity provider?** (email+password, Google, or enterprise SSO)
5. **Which integration first?** (QuickBooks and Xero give the most value)
6. **Real LLM for assist, or keep it rule-based?** (needs an API key)

---

## Suggested sequence

1. **A1–A3** here now: API gateway + SQLite + Docker. (Local, no accounts.)
2. **F16**: pick a host, deploy the container behind HTTPS with Postgres.
3. **A4 + F9**: auth + multi-user + collaboration.
4. **F13**: integrations, starting with QuickBooks/Xero.
5. **F11 upgrade** (optional): wire a real LLM into assist.
6. **F15**: mobile/PWA, last.

The first three steps in Part A are the natural next build and I can start on them
immediately — say the word and I'll begin with the API gateway + Dockerfile, which
is the single biggest step from "local scripts" toward "deployable product."
