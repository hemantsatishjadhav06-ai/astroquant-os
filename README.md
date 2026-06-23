# AstroQuant OS

A research lab that scientifically tests whether astrology (Vedic/astronomical), Gann, technical,
options-flow, news-sentiment, and macro signals have **real predictive edge** in Indian markets.
**Nothing is assumed true. Everything is tested.** Full design in [`docs/`](docs/README.md).

> Research platform only — no live trading. Paper-trading backend gates any future live step.

---

## Quickstart (no DB, no API keys, no network needed)

```bash
pip install pyswisseph numpy pytest sqlalchemy pydantic pydantic-settings typer structlog python-dateutil
# (or: pip install -e ".[data,dev]" for the full toolchain)

# 1) Compute real sidereal (Lahiri) planetary positions:
PYTHONPATH=python python3 scripts/run_astronomy.py

# 2) Run the FULL research vertical slice end-to-end (synthetic data, offline) and
#    write a self-contained HTML report you can open in any browser:
PYTHONPATH=python python3 scripts/run_research.py research_report.html

# 3) Run the test suite (astronomy known-values + Gann + features/leakage + research + paper + costs):
PYTHONPATH=python python3 -m pytest tests/ -q

# 4) CLI:
PYTHONPATH=python python3 -m astroquant.cli health
PYTHONPATH=python python3 -m astroquant.cli astro 2024-01-01
PYTHONPATH=python python3 -m astroquant.cli gann 2024-01-01 --price 22000
PYTHONPATH=python python3 -m astroquant.cli research --symbol NIFTY            # prints the verdict
PYTHONPATH=python python3 -m astroquant.cli pipeline --out research_report.html # writes the report
```

The research engine answers **RQ-004** — *do astro + Gann features add out-of-sample, post-cost
predictive power beyond technical + market features for next-day NIFTY direction?* — and prints an
honest verdict (`edge` / `conditional_edge` / `no_edge_found`). On the offline synthetic series the
correct answer is **no edge**: a verdict the integrity controls are *designed* to produce on noise.

## Full stack (with infrastructure)

```bash
docker compose up -d                       # TimescaleDB + Mongo + Redis + n8n
# extensions auto-load from sql/001_extensions.sql on first init
PYTHONPATH=python alembic upgrade head      # create core schema (docs/006)
psql "$AQ_PG_DSN" -f sql/002_hypertables.sql  # convert bars -> hypertable + 5m continuous aggregate

# The repository layer (db/repo.py) runs unchanged on Postgres or local SQLite. Local default:
export AQ_DB_URL="sqlite:///astroquant.db"   # omit to use the same; set a postgresql+psycopg URL for prod
```

---

## What's built

### Month-1 vertical slice (per docs/013)

| Component | Status | File |
|---|---|---|
| Agent contract + run manifests (reproducibility) | ✅ | `python/astroquant/agents/base.py` |
| **Agent 4 — Astronomy/Ephemeris collector** (Swiss Ephemeris, sidereal Lahiri, nakshatras, retrograde, moon phase, aspects) | ✅ runnable + tested | `collectors/astronomy.py` |
| **Agent 1 — Market collector** (pluggable sources; yfinance + synthetic; Kite stub) | ✅ runnable | `collectors/market.py`, `collectors/sources/market_sources.py` |
| India transaction-cost model (verified rates) | ✅ tested | `research/costs.py` |
| Research sanity guards (shuffle-label, random-feature) | ✅ tested | `research/sanity.py` |
| Core DB schema (Postgres/Timescale) + Alembic migration | ✅ | `db/models.py`, `migrations/` |
| Infra (docker-compose) + Timescale/pgvector setup | ✅ | `docker-compose.yml`, `sql/` |
| Config / CLI | ✅ | `common/config.py`, `cli.py` |

### Month-2 layer (this iteration — the research loop is now closed)

| Component | Status | File |
|---|---|---|
| **DB persistence / repository** (idempotent `merge` upserts; runs on SQLite *or* Postgres) | ✅ tested | `db/repo.py`, `db/session.py` |
| **Agent 5 — Gann collector** (Square of Nine, Gann fan/angles, time cycles; pure-Python reference) | ✅ runnable + tested | `collectors/gann.py` |
| **Deterministic synthetic market source** (offline, reproducible — the integrity clean-room) | ✅ tested | `collectors/sources/market_sources.py` |
| **Agent 6 — Feature Factory** (technical/market/astro/gann families; strict no-look-ahead) | ✅ tested | `features/factory.py` |
| **Research Engine** (chronological walk-forward → baseline→augmented→ablation→correction→verdict) | ✅ tested | `research/engine.py`, `research/stats.py`, `research/model.py` |
| Self-contained statistics (AUC, Benjamini–Hochberg FDR, Probabilistic & **Deflated Sharpe**) | ✅ tested | `research/stats.py` |
| **Paper-Trading backend (G5 gate)** (post-cost ledger, reconciliation invariant, equity curve) | ✅ tested | `paper/engine.py` |
| End-to-end pipeline + **HTML research report** | ✅ runnable | `research/pipeline.py`, `research/report.py`, `scripts/run_research.py` |

**Test status:** 44/44 passing. Highlights:
- astronomy positions verified vs published Vedic ephemeris for 2024-01-01 (Jupiter in Aries, Saturn
  in Aquarius, Rahu in Pisces, Mercury retrograde);
- Gann Square-of-Nine verified against closed-form values (base 144 → 360° = 196, 180° = 169);
- Feature Factory passes the **no-look-ahead** guard (truncating the future cannot change past rows);
- the Research Engine **detects a planted signal** *and* **reports the null on pure noise** — both
  directions are tested, because a platform that only ever says "no edge" is useless and one that says
  "edge" on noise is dangerous;
- the paper-trade **ledger reconciles** every run (`equity == cash + Σpnl − Σcost`).

## Methodology controls (docs/007)
Chronological walk-forward with an **embargo** (never a random shuffle), ablation as the only evidence
for a family, shuffle-label & random-feature guards, **Benjamini–Hochberg** FDR plus a **Deflated
Sharpe Ratio** (a Sharpe selected from N trials must clear a bar that rises with N), and **post-cost**
performance throughout. Honest nulls are first-class results.

## Next (per roadmap, docs/013)
- Agent 2 (Options chain + Greeks) and Agent 3 (Economic, with point-in-time vintages).
- SHAP attribution on any detected lift; Reality-Check / SPA across the full hypothesis family; PBO.
- C++ fast-paths (ephemeris, Gann, tick backtest) under `cpp/` via pybind11.
- Live-mode paper trading (latency, slippage, partial fills) building on the G5 gate here.

## Repo layout
See `docs/000_MASTER_SPEC.md` §repo layout. C++ performance components attach under `cpp/` via
pybind11 in later phases; the Python paths already run the full daily-research loop.

## License note
Swiss Ephemeris is AGPL (or commercial). Fine for this private research platform; see
`docs/VERIFICATION_ADDENDUM.md` before any distributed/SaaS use. The engine is isolated behind
`collectors/astronomy.py` so it can be swapped.
