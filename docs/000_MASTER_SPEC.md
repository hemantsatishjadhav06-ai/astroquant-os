# Document 000 — Master Spec

**Status:** Source of truth. When any document conflicts with another, this one wins.
**Audience:** Claude Code / Cursor / developers / AI agents building the system.

---

## 1. What AstroQuant OS is (and is not)

**Is:** an autonomous *research laboratory* that ingests Indian market data, astronomical data,
Gann constructs, news/sentiment, and macro data; manufactures thousands of features; generates
and tests pre-registered hypotheses with proper statistical controls; backtests promising signals;
and forward-validates them in a paper-trading backend.

**Is not (for now):** a live-trading bot, an astrology-prediction app, or a client-facing advisory
product. There is no broker order-placement path in scope. SEBI Research Analyst / algo-approval
concerns are deferred and noted only where a future live path would require them.

**The platform succeeds even if astrology fails.** The most likely and most valuable outcome is a
rigorous, defensible answer to *which* signal families (cycles, sentiment, options flow, sector
rotation, planetary, Gann) carry edge and which do not. A clean "astrology adds no incremental
predictive power" is a publishable, money-saving result — not a failure.

---

## 2. Architecture — the 8 layers

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1  DATA COLLECTION                                     │
│  Agents: Market, Options, Economic, Astronomy, (Gann calc)   │
│  Sources: Upstox/Kite/SmartAPI · Swiss Ephemeris/JPL ·        │
│           NewsAPI/GDELT · FRED/World Bank/RBI                 │
└───────────────┬─────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2  DATA WAREHOUSE                                      │
│  PostgreSQL (structured) · TimescaleDB (1m/5m/daily bars) ·   │
│  MongoDB (news/notes/events) · Vector DB (knowledge/patterns) │
└───────────────┬─────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3  FEATURE FACTORY                                     │
│  Technical · Astrology · Gann · Market features → feature store│
│  Output: (date, symbol, 1000+ features) point-in-time correct │
└───────────────┬─────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 4  RESEARCH ENGINE / AI LAB                            │
│  Hypothesis registry · Pattern Discovery · ML models ·        │
│  Ablation & SHAP · multiple-testing correction                │
└───────────────┬─────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 5  BACKTESTING                                         │
│  Event-driven · walk-forward · Monte Carlo · regime testing · │
│  Deflated Sharpe · cost & slippage modelling                  │
└───────────────┬─────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 6  PAPER TRADING BACKEND  ← first-class component      │
│  Live-data, simulated fills · ledger · P&L · attribution      │
│  6–12 month forward validation gate                           │
└───────────────┬─────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 7  (DEFERRED) LIVE TRADING                             │
│  Out of scope. Gated behind formal milestone + compliance.    │
└─────────────────────────────────────────────────────────────┘

         Cross-cutting: ORCHESTRATOR · RISK · AUDIT · REPORTING · ANOMALY
```

**Data-flow contract between layers:** each layer reads from the warehouse and writes back to it.
Layers never call each other directly except through the message bus or the database. This keeps
agents independently testable and re-runnable (idempotency is required — re-running a collector for
a date range must not duplicate rows; use upserts keyed on natural keys).

---

## 3. Technology stack & justifications

| Concern | Choice | Why |
|---|---|---|
| Performance-critical math | **C++17** | Ephemeris loops, Square-of-Nine grids, and tick-level backtesting are hot paths. Swiss Ephemeris is C; binding directly avoids per-call Python overhead across millions of timestamps. |
| Ephemeris | **Swiss Ephemeris** (via C++), cross-checked with **NASA JPL Horizons** | Industry-standard, sub-arcsecond accuracy, supports sidereal zodiac + Lahiri ayanamsa needed for Vedic work. JPL used as an independent correctness check, not in the hot path. |
| Glue / ML / agents | **Python 3.11+** | Ecosystem (pandas, polars, scikit-learn, XGBoost/LightGBM/CatBoost, PyTorch, statsmodels, SHAP). |
| Structured store | **PostgreSQL 16** | Reference data, signals, backtests, strategies, planetary_data, gann_cycles, economic_data. ACID, rich SQL. |
| Time-series | **TimescaleDB** (Postgres extension) | Hypertables + continuous aggregates for 1m/5m/daily bars. Stays in the Postgres ecosystem — one fewer system to operate. |
| Unstructured | **MongoDB** | News docs, research notes, event logs — flexible schema. |
| Semantic search | **Vector DB** (pgvector first; Qdrant if scale demands) | Knowledge base, discovered patterns, dedup of hypotheses. Start with `pgvector` to avoid a 5th datastore; migrate only if needed. |
| Message bus | **Redis Streams** (or NATS) | Lightweight agent-to-agent eventing; you already run Redis. |
| Orchestration | **Python orchestrator + n8n** | n8n for scheduling/cron/visual ops glue (you already run `hemantbg.app.n8n.cloud`); Python orchestrator for stateful research pipelines. |
| Backtest libs | **VectorBT** (vectorized sweeps) + **custom C++ event engine** (realistic fills) | VectorBT for fast parameter sweeps during discovery; C++ engine for honest, path-dependent backtests before paper. Backtrader optional for sanity cross-checks. |
| Migrations | **Alembic** | Versioned Postgres/Timescale schema. |
| Config | **pydantic-settings** + `.env` | Typed config, no secrets in code. |

> **Licensing flag (read before shipping):** Swiss Ephemeris is dual-licensed — AGPL **or** a paid
> commercial license from Astrodienst. For a private research platform that is never distributed,
> AGPL terms are generally workable, but if AstroQuant ever becomes a distributed/SaaS product you
> must either open-source under AGPL or buy the commercial license. Document the decision now.
> **VERIFIED (June 2026, see `VERIFICATION_ADDENDUM.md`):** dual license confirmed — AGPL-3.0 or
> Professional License (~CHF 750 first / CHF 400 additional, one-time per project). For a private,
> non-distributed research platform AGPL is workable; keep the ephemeris behind a clean interface so
> it can be swapped if the project ever becomes a distributed/SaaS product.

---

## 4. Agent inventory (full detail in `004`)

| # | Agent | Layer | Tech |
|---|-------|-------|------|
| 1 | Market Data Collector | 1 | Python |
| 2 | Options Collector | 1 | Python |
| 3 | Economic Collector | 1 | Python |
| 4 | Astronomy/Ephemeris Collector | 1/2 | C++ core + Python wrapper |
| 5 | Gann Calculator | 2 | C++ core + Python wrapper |
| 6 | Feature Builder | 3 | Python (polars) |
| 7 | Pattern Discovery | 4 | Python |
| 8 | Research Analyst | 4 | Python + LLM |
| 9 | Backtester | 5 | Python + C++ engine |
| 10 | Risk Manager | cross | Python |
| 11 | Paper Trader | 6 | Python (+C++ matching optional) |
| 12 | Live Trader | 7 | **deferred** |
| 13 | Performance Auditor | cross | Python |
| 14 | Report Generator | cross | Python + LLM |
| 15 | Anomaly Detector | cross | Python |
| 0 | Orchestrator | cross | Python + n8n |

---

## 5. The central research question (RQ-004) and how the whole system answers it

Everything funnels toward: **"Do planetary/Gann features add predictive power beyond technical indicators?"**

The system answers it by construction:
1. **Feature Factory** tags every feature with a `family`: `technical`, `market`, `astro`, `gann`, `news`, `macro`.
2. **Baseline model** = trained on `technical ∪ market` only.
3. **Augmented model** = baseline families ∪ `astro ∪ gann`.
4. **Ablation**: measure out-of-sample lift (AUC / IC / Sharpe of resulting strategy) of augmented over baseline.
5. **SHAP**: attribute the lift to specific astro/Gann features.
6. **Multiple-testing correction**: deflate for the number of feature combinations and hypotheses tried.
7. **Verdict**: edge is declared only if incremental lift is positive, out-of-sample, post-cost, and survives correction. Otherwise: "no incremental edge found" — recorded honestly in the discoveries store.

This pattern (baseline → augmented → ablation → correction → verdict) is the recurring motif of the platform. Internalize it; it appears in `007`, `009`, and `010`.

---

## 6. Idempotency, point-in-time correctness, and reproducibility (mandatory)

- **Idempotent collectors:** upsert on natural keys (`symbol, timestamp, source`). Re-runs heal gaps, never duplicate.
- **Point-in-time feature store:** every feature row carries `as_of_ts`. Joins for model training must use `as_of_ts <= label_origin_ts`. No exceptions.
- **Versioned everything:** datasets, feature definitions, models, and hypotheses all get content hashes + semantic versions. A backtest result references the exact dataset hash and code commit that produced it.
- **Seeded randomness:** every stochastic step records its seed.
- **Run manifests:** each research run writes a manifest (inputs, code commit, config, seeds, output hashes) so any result is reproducible from the manifest alone.

---

## 7. Milestone gates (the only way layers advance)

| Gate | Condition to pass | Unlocks |
|---|---|---|
| **G1 Data** | ≥2 years daily + ≥6 months intraday market data stored, validated against a second source; ephemeris cross-checks JPL within tolerance. | Feature Factory |
| **G2 Features** | 1000+ features built point-in-time-correct for full history; leakage tests pass. | Research Engine |
| **G3 Research** | Baseline model beats naive (random/buy-hold) out-of-sample; pipeline produces honest null results on shuffled labels. | Backtesting |
| **G4 Backtest** | A candidate strategy shows positive Deflated Sharpe out-of-sample, post-cost, across ≥2 regimes. | Paper Trading |
| **G5 Paper** | 6–12 months forward paper performance consistent with backtest (no severe degradation); risk limits never breached. | Live decision review |

**No gate may be skipped.** Claude Code should refuse to wire a downstream layer to live action before its gate is green.

---

## 8. What "done" looks like for v1

A running system that, every trading day: pulls market/options/macro data, computes the day's
ephemeris + Gann constructs, refreshes the feature store, lets the Research Engine run its registered
hypotheses, surfaces ranked candidate signals with proper statistical caveats, runs them through the
paper-trading backend, and emits a daily research report — all reproducible from run manifests, with
the astro/Gann families honestly measured against the technical baseline.
