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

# 5) Autonomous Alpha Discovery Lab — Collect→Hypotheses→Backtest→Validate→Rank→Learn→Repeat
PYTHONPATH=python python3 -m astroquant.cli lab --symbols NIFTY,BANKNIFTY --source synthetic
PYTHONPATH=python python3 -m astroquant.cli lab --symbols NIFTY,RELIANCE --source nse   # LIVE NSE data

# 6) Serve the live web dashboard + API (http://127.0.0.1:8000):
pip install -e ".[api,data]" && astroquant serve

# 7) Market Genome Project (Idea 2) — knowledge discovery → research note + knowledge graph
PYTHONPATH=python python3 -m astroquant.cli genome --symbol NIFTY --source nse --out genome_NIFTY.md

# 8) Self-Evolving Hedge Fund (Idea 3) — evolve strategies → validate → paper portfolio
PYTHONPATH=python python3 -m astroquant.cli fund --symbol NIFTY --source nse --generations 5

# 9) Stock Deep Dive — astro + technical + Gann + backtest + analyst narrative, per stock
PYTHONPATH=python python3 -m astroquant.cli stock --symbol RELIANCE --source nse --out RELIANCE.md

# 10) Options Greeks Engine — vol regime → structure → risk-sized order intents (+ backtest)
PYTHONPATH=python python3 -m astroquant.cli options --symbol NIFTY --source nse --backtest
```

## The Autonomous Alpha Discovery Lab (Idea 1)

> "An AI research lab that continuously discovers, tests, validates, and ranks profitable market
> signals from any data source — including astrology, Gann, technical, and market price action."

```
Collect → Generate Hypotheses → Backtest → Validate → Rank → Learn → Repeat
```

The lab (`python/astroquant/lab/`) enumerates hypotheses (each symbol × family-on-trial × decision
band), runs every one through the full research protocol + paper-trade gate, and ranks the survivors.
The decisive discipline: **every hypothesis increments a global comparison counter that deflates all
p-values and Sharpes** (Benjamini–Hochberg + Deflated Sharpe), so searching a huge astro/Gann space
can't manufacture a fake edge. Verified on **live NSE/BSE data** (free, via the `nse`/`bse` sources).
A run that finds **0 survivors** on real NIFTY is the lab working correctly — an honest null.

The **FastAPI service** (`python/astroquant/api/app.py`) exposes a live dashboard at `/` (run the lab,
watch the leaderboard), plus `/lab/run`, `/discoveries`, `/astro/{date}`, `/healthz`.
Deploy it on Render in minutes — see [`DEPLOY.md`](DEPLOY.md) and [`render.yaml`](render.yaml).
**Secrets (broker/API keys) go in env vars only — never in code or git.**

## Market Genome Project (Idea 2) & Self-Evolving Hedge Fund (Idea 3)

**Idea 2 — Market Genome** (`python/astroquant/genome/`): knowledge discovery, not trading. Runs a
battery of relationship studies (*Does Moon illumination affect volatility? Do Gann cycles predict
reversals? Does Mercury retrograde shift returns?*), each with a permutation p-value and a batch-wide
FDR correction, then builds a **knowledge graph** + an auto-generated **research note** (Markdown +
Mermaid). Method-control studies (RSI, weekday, momentum) keep the battery's sensitivity visible.
API: `POST /genome/run`. CLI: `astroquant genome --out note.md`.

**Idea 3 — Self-Evolving Hedge Fund** (`python/astroquant/fund/`): an evolutionary search over
strategy genomes (which feature families, decision band, regularisation). Fitness is the **post-cost
Deflated Sharpe, deflated by the number of strategies tried**, so breeding thousands of variants
raises the bar rather than guaranteeing a winner. The evolved winner is then **re-validated by the
rigorous research engine** before a paper portfolio + risk report (Sharpe, DSR, max-DD, VaR, exposure)
is produced. **Deploy = paper only (G5 gate); no live orders, ever.** This is the platform's sharpest
lesson in code: a strategy can look spectacular in the evolution slice (e.g. +65%, Sharpe 1.1) and
still be graded **no-edge** once walk-forward + multiple-testing correction is applied.
API: `POST /fund/evolve`. CLI: `astroquant fund --generations 5`.

## Stock Deep Dive — all three lenses on one name

`python/astroquant/analysis/` + `python/astroquant/universe/` fuse everything into a per-stock report:
a **technical** read (trend, RSI, SMAs, momentum, volatility), **Gann** geometry (Square-of-Nine
support/resistance around the live price, swing pivots, upcoming time-cycle dates), the **astrological**
backdrop (current sidereal transits, retrogrades, Moon nakshatra, tight aspects — flagged as an unproven
prior), and a **backtest verdict** that honestly states whether astro+Gann add real edge for that name.
A synthesized **stance** (Constructive / Neutral / Cautious) leans on the evidence-based technical core.
An **LLM analyst narrative** is generated when `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set in the
environment (model via `AQ_LLM_MODEL`); otherwise a strong built-in narrative is used — **no keys in code**.
Runs over the **full Indian instrument universe** — every **NSE** equity (~2,372) + every **BSE** equity
(~4,898) + **MCX** commodity futures (~7,300 instruments), bundled from the official exchange masters in
`python/astroquant/universe/data/` (refresh with `scripts/fetch_universe.py`). Each instrument resolves to
its correct free Yahoo ticker (`SYMBOL.NS`, `<scrip_code>.BO`, or an MCX commodity proxy like `GC=F`), so
data is fetched lazily per symbol. The universe is searchable via `GET /universe?q=&exchange=&limit=`.
UI: the **📈 Stock Deep Dive** tab. API: `GET /universe`, `POST /stock/analyze`. CLI: `astroquant stock --symbol RELIANCE --out note.md`.

## Options Greeks Engine (Δ / Θ / Γ)

`python/astroquant/strategies/options_greeks/` is the volatility-and-Greeks decision layer that turns
the platform's directional/timing signals into **structured, risk-bounded options positions** on
Indian index & stock options. It encodes the one rule that governs options P&L — **you cannot be long
Gamma and long Theta at the same time** — so every trade is an explicit bet on realized vs. implied
volatility, with Delta carrying the directional view.

Pipeline: `signal (dir + conviction) + option chain (IV, IV-rank) → vol regime → structure → worst-case-gap risk sizing → order intents + Greek-based exits + a live trigger`. It ships:
Black–Scholes pricing + Greeks + an IV solver (`greeks.py`); a live-NSE/synthetic **option chain**
collector with IV-rank (`chain.py`); the **NSE/BSE expiry calendar** with the Gamma-cliff rule
(`expiry.py`); a Greek-profiled **structure library** — straddle, strangle, debit spread, calendar,
iron condor, broken-wing (`structures.py`); the deterministic **`(regime, conviction, dir) → structure`**
mapping with Greek-aware **gates** (never sell vol when IV-rank < 0.50; never hold net-short-Gamma into
the expiry final hour) (`decision.py`); **worst-case-gap risk sizing** (`risk.py`); and a **backtest**
with the India options cost stack and the metrics that matter — net-of-cost P&L, max drawdown, win
rate, **tail loss (worst 1%)**, and realized-vs-implied capture (`backtest.py`).
**Research/paper only — order intents are never sent to a broker.**
UI: the **⚡ Options Greeks** tab. API: `POST /options/signal`, `POST /options/backtest`, `GET /options/chain`. CLI: `astroquant options --symbol NIFTY --backtest`.

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

### Month-3 layer — the Autonomous Alpha Discovery Lab + service

| Component | Status | File |
|---|---|---|
| **Free real NSE + BSE data** (live, via Yahoo `.NS`/`.BO`; synthetic fallback offline) | ✅ tested | `collectors/sources/india_sources.py` |
| **Discovery Lab** (Collect→Hypotheses→Backtest→Validate→Rank→Learn→Repeat; global comparison denominator) | ✅ tested, runs on live data | `lab/` |
| **FastAPI service + live dashboard** (`/`, `/lab/run`, `/discoveries`, `/astro`, `/healthz`) | ✅ tested | `api/app.py` |
| **Render-deployable** (`render.yaml`, `Dockerfile`, secrets via env only) | ✅ | `render.yaml`, `Dockerfile`, `DEPLOY.md` |
| **Market Genome Project (Idea 2)** — relationship studies → knowledge graph + research note | ✅ tested | `genome/` |
| **Self-Evolving Hedge Fund (Idea 3)** — evolutionary search → validate → gated paper portfolio | ✅ tested | `fund/` |
| **Stock Deep Dive** — per-stock astro+technical+Gann+backtest + LLM narrative over a curated NSE universe | ✅ tested | `analysis/`, `universe/` |
| **Options Greeks Engine (Δ/Θ/Γ)** — vol regime → structure → risk-sized intents + options backtest | ✅ tested | `strategies/options_greeks/` |
| **Unified 5-tab dashboard** (Lab · Genome · Fund · Stock · Options) with inline-SVG charts | ✅ tested | `api/dashboard.py` |

**Universe:** ~7,300 instruments — NSE (2,372) + BSE (4,898) + MCX (14) + indices, bundled from official masters.

**Test status:** 87/87 passing. Highlights:
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
