# Deploying the AstroQuant OS Discovery Lab

The lab ships as a FastAPI service with a live dashboard. Two supported paths.

## ⚠️ Secrets first
**Never commit API keys, tokens, or broker credentials.** This repo reads everything from
environment variables (`AQ_DB_URL`, `AQ_BROKER`, `AQ_KITE_*`, …). Set secrets only in your host's
dashboard. If a key has ever been pasted into a chat, an email, or a commit, **rotate it**:
- GitHub PAT → GitHub → Settings → Developer settings → Personal access tokens → revoke + regenerate.
- Render API key → Render → Account Settings → API Keys → revoke + regenerate.

## Option A — Render Blueprint (recommended)
1. Push this repo to GitHub (see `scripts/push_to_github.sh`).
2. In Render: **New → Blueprint**, connect the repo. Render reads [`render.yaml`](render.yaml).
3. (Optional, for a persistent ledger) create a Render Postgres and set `AQ_DB_URL` on the service to
   its `postgresql+psycopg://…` URL — as a dashboard env var, not in code.
4. Deploy. Render builds `pip install -e .[api,data]` and starts
   `uvicorn astroquant.api.app:app --host 0.0.0.0 --port $PORT`. Health check: `/healthz`.
5. Open the service URL → the dashboard. Click **Run discovery**.

If the native build chokes on `pyswisseph` (it compiles a tiny C extension), switch the service to
**Docker** in Settings — the bundled [`Dockerfile`](Dockerfile) installs `build-essential`.

## Option B — Docker anywhere
```bash
docker build -t astroquant-os .
docker run -p 8000:8000 -e AQ_BROKER=nse astroquant-os
# open http://localhost:8000
```

## Run locally (no container)
```bash
pip install -e .[api,data]
astroquant serve            # or: PYTHONPATH=python uvicorn astroquant.api.app:app --reload
# open http://localhost:8000
```

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Live dashboard (run the lab, see the leaderboard) |
| GET | `/healthz` | Liveness probe |
| POST | `/lab/run?symbols=NIFTY,BANKNIFTY&source=nse&rounds=1` | Run a discovery round → leaderboard JSON |
| GET | `/discoveries` | The discoveries ledger (from the DB) |
| GET | `/astro/2024-01-01` | Sidereal planetary positions for a date |

## Notes on the free tier
- Render free web services sleep when idle and have limited CPU; a live `source=nse` run over a long
  window can take 30–60s. Use `source=synthetic` or a shorter date range for a snappy demo.
- The default DB is an ephemeral SQLite file in the system temp dir. For a ledger that survives
  restarts, point `AQ_DB_URL` at a managed Postgres.
