# Deploying DealLens to Railway

DealLens ships as one Docker container (pure Python standard library — no pip
deps required). Railway builds the `Dockerfile` and gives you an HTTPS URL.

## What's in the box

- `Dockerfile` — builds the image; runs `python -m ui` (the gateway) on `$PORT`.
- `railway.toml` — build/deploy config with a `/api/health` health check.
- `.dockerignore` — keeps the image lean.
- Storage: **SQLite** at `DEALLENS_DB` (default `/data/deallens.db`). Mount a
  volume at `/data` so deals survive redeploys.

## One-time setup

1. Push this folder to a Git repo (GitHub/GitLab).
2. In Railway: **New Project -> Deploy from repo**, pick this repo. Railway
   detects the `Dockerfile` automatically.
3. **Variables** (Settings -> Variables):
   - `DEALLENS_DB = /data/deallens.db`
   - `DEALLENS_HOME = /app`
   - (`PORT` and `HOST` are handled automatically / by the Dockerfile.)
4. **Volume** (Settings -> Volumes): add one mounted at `/data` (a few GB is
   plenty) so the SQLite file persists.
5. Deploy. Railway builds and gives you a public URL; open it and the UI loads.

## Verify

- `GET /api/health` -> `{"ok": true, "status": "healthy"}` (also the healthcheck).
- `GET /api/manifests` -> every primitive's manifest (service discovery).
- The web UI at `/` works exactly as it does locally.

## Run the container locally first (recommended)

```bash
cd "<this folder>"
docker build -t deallens .
docker run -p 8765:8765 -e PORT=8765 -v "$PWD/_data:/data" deallens
# open http://localhost:8765
```

## Accounts & multi-user

Auth is **built in**. On first visit users see a login screen; they can create an
account (email + password) and each user sees only their own deals. Deals can be
**shared** with teammates by email as `viewer` or `editor`, and collaborators can
leave **comments**. Passwords are hashed (PBKDF2-HMAC-SHA256); sessions are
HttpOnly cookies. Everything persists in the same SQLite database on `/data`.

So you can safely share the public URL — visitors must sign up and only access
their own (or shared) deals.

## Notes & next steps

- **Scaling to many users:** the store interfaces (`workspace/store.py`,
  `accounts/store.py`) abstract persistence. Moving from SQLite to Postgres is a
  new `Store` implementation + a connection string — no engine changes.
- **Backups:** the SQLite file lives on the `/data` volume; snapshot it
  periodically.
- **Hardening for scale:** consider rate-limiting the `/api/auth/*` routes and
  adding email verification / password reset before a wide public launch.
