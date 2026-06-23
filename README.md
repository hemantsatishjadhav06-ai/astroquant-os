# AstroQuant OS

A research lab that scientifically tests whether astrology (Vedic/astronomical), Gann, technical,
options-flow, news-sentiment, and macro signals have **real predictive edge** in Indian markets.
**Nothing is assumed true. Everything is tested.** Full design in [`docs/`](docs/README.md).

> Research platform only — no live trading. Paper-trading backend gates any future live step.

---

## Quickstart (no DB, no API keys needed)

```bash
pip install pyswisseph numpy pytest        # minimal, to run the astronomy core + tests
# (or: pip install -e ".[data,dev]" for the full toolchain)

# 1) Compute real sidereal (Lahiri) planetary positions:
PYTHONPATH=python python3 scripts/run_astronomy.py

# 2) Run the test suite (astronomy known-values + India cost model + research sanity guards):
PYTHONPATH=python python3 -m pytest tests/ -q

# 3) CLI:
PYTHONPATH=python python3 -m astroquant.cli health
PYTHONPATH=python python3 -m astroquant.cli astro 2024-01-01
PYTHONPATH=python python3 -m astroquant.cli market --symbols NIFTY --start 2024-01-01 --end 2024-02-01
```

## Full stack (with infrastructure)

```bash
docker compose up -d                       # TimescaleDB + Mongo + Redis + n8n
# extensions auto-load from sql/001_extensions.sql on first init
PYTHONPATH=python alembic upgrade head      # create core schema (docs/006)
psql "$AQ_PG_DSN" -f sql/002_hypertables.sql  # convert bars -> hypertable + 5m continuous aggregate
```

---

## What's built (Month-1 vertical slice, per docs/013)

| Component | Status | File |
|---|---|---|
| Agent contract + run manifests (reproducibility) | ✅ | `python/astroquant/agents/base.py` |
| **Agent 4 — Astronomy/Ephemeris collector** (Swiss Ephemeris, sidereal Lahiri, nakshatras, retrograde, moon phase, aspects) | ✅ runnable + tested | `collectors/astronomy.py` |
| **Agent 1 — Market collector** (pluggable sources; yfinance fallback; Kite stub) | ✅ runnable | `collectors/market.py`, `collectors/sources/market_sources.py` |
| India transaction-cost model (verified rates) | ✅ tested | `research/costs.py` |
| Research sanity guards (shuffle-label, random-feature) | ✅ tested | `research/sanity.py` |
| Core DB schema (Postgres/Timescale) + Alembic migration | ✅ | `db/models.py`, `migrations/` |
| Infra (docker-compose) + Timescale/pgvector setup | ✅ | `docker-compose.yml`, `sql/` |
| Config / CLI | ✅ | `common/config.py`, `cli.py` |

**Test status:** 16/16 passing (astronomy positions verified against published Vedic ephemeris for
2024-01-01: Jupiter in Aries, Saturn in Aquarius, Rahu in Pisces, Mercury retrograde; cost-model rules;
sanity guards correctly distinguish real signal from noise).

## Next (per roadmap, docs/013)
- Wire collector persistence into the DB layer (upserts → `bars`, `planetary_data`, …).
- Agent 5 (Gann, C++ via pybind11), Agent 2 (Options), Agent 3 (Economic, with vintages).
- Feature Factory (Agent 6) with family tags + leakage tests → Gate G2.
- Research engine (baseline→augmented→ablation→SHAP→correction) → answers RQ-004.
- Paper-trading backend (`docs/011`) as the forward-validation gate.

## Repo layout
See `docs/000_MASTER_SPEC.md` §repo layout. C++ performance components (ephemeris fast-path, Gann,
tick backtest engine) attach under `cpp/` via pybind11 in later phases; the Python ephemeris path
already works for daily research.

## License note
Swiss Ephemeris is AGPL (or commercial). Fine for this private research platform; see
`docs/VERIFICATION_ADDENDUM.md` before any distributed/SaaS use. The engine is isolated behind
`collectors/astronomy.py` so it can be swapped.
