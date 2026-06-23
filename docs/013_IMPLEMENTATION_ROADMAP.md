# Document 013 — Implementation Roadmap (6 months)

A lean build order designed to *ship a working research loop fast*, then deepen. Each month ends at a
gate (`000` §7). Do not advance past a red gate. This is the antidote to the 3,000-page-never-ships trap.

---

## Month 1 — Data Platform → **Gate G1**
**Build:** repo scaffold (`000` repo layout), docker-compose infra (Postgres+Timescale, Mongo, Redis,
pgvector, n8n), Alembic migrations for `006` schema, trading calendar + symbol master, **Market Data
Collector** (Agent 1) with backfill + daily incremental, **Astronomy Collector** (Agent 4: C++/Swiss
Ephemeris via pybind11, sidereal Lahiri), **Anomaly Detector** (Agent 15) basic checks.
**Gate G1:** ≥2 yrs daily + ≥6 mo intraday stored & cross-checked vs a 2nd source; ephemeris matches
JPL Horizons within tolerance; survivorship-safe universe (delisted symbols retained).

## Month 2 — Feature & Gann Engine → **Gate G2**
**Build:** **Options Collector** (Agent 2), **Economic Collector** (Agent 3, with vintages), **Gann
Calculator** (Agent 5, C++), **Feature Builder** (Agent 6) producing the point-in-time feature store
with family tags, leakage tests, `feature_catalog`. Basic research dashboard (read-only views).
**Gate G2:** 1000+ features built point-in-time-correct across full history; all leakage/shuffle-label
tests pass; feature definitions versioned.

## Month 3 — Research Engine + Agent Layer → **Gate G3**
**Build:** hypothesis registry + pre-registration; **Pattern Discovery** (Agent 7) with comparison
counting; **Research Analyst** (Agent 8) running baseline→augmented→ablation→SHAP→correction; ML
models (`009`: XGBoost/LightGBM/CatBoost first, TFT/LSTM later); the `007` statistical machinery
(FDR, DSR, PBO, sanity tests); **Orchestrator** (Agent 0) DAG + n8n schedules.
**Gate G3:** baseline beats naive out-of-sample; pipeline reports honest nulls on shuffled labels;
RQ-004 can be run end-to-end and produces a corrected verdict.

## Month 4 — Backtesting → **Gate G4**
**Build:** VectorBT sweep harness (trial-counted) + **C++ event-driven engine** sharing the cost/fill
model; walk-forward, Monte Carlo, regime testing; **Backtester** (Agent 9) writing `backtests` with
DSR/PBO; **Risk Manager** (Agent 10) integrated into backtest.
**Gate G4:** at least one candidate shows positive **Deflated Sharpe** out-of-sample, post-cost, across
≥2 regimes — or an honest "no candidate qualifies yet" (also acceptable; iterate hypotheses).

## Month 5 — Paper Trading → **(begins) Gate G5 clock**
**Build:** **Paper Trading backend** (`011`) in this order — ledger+invariants → versioned India cost
model → matching engine (latency + conservative fills, replay first) → strategy runtime + risk gate →
attribution + live-vs-backtest comparison → live (read-only) market-data mode. **Performance Auditor**
(Agent 13) comparing realized vs backtest.
**Gate G5 (starts here, runs 6–12 mo):** forward paper performance consistent with backtest; risk
limits never breached; edge persists across a regime change.

## Month 6 — Hardening, Reporting, Evaluation
**Build:** **Report Generator** (Agent 14) daily/weekly honest reports via n8n; discoveries-ledger
dedup; reproducibility audit (rebuild a result from its manifest); documentation pass.
**Decision review:** assess the discoveries ledger. Likely honest outcomes: some sentiment/cycle/
options-flow signals show conditional edge; astro/Gann characterized (edge / no-edge / conditional)
with full provenance. **Only if G5 ultimately passes** does the (out-of-scope, compliance-gated) live
conversation begin.

---

## Sequencing notes for Claude Code
- Build vertically thin first: one symbol, daily bars, a handful of features, the full pipeline end-to-end, *then* widen. A working end-to-end loop on NIFTY daily beats a half-built warehouse for 2000 symbols.
- C++ components (ephemeris, Gann, event engine) get clean `pybind11` boundaries + unit tests before integration.
- Write the sanity tests (`007` §6) *early* — they catch leakage while the system is small and debuggable.
- Keep the live-trading package physically absent from the repo until G5 (`011` §8 guard).

## What to verify against current sources before/while building
- Indian broker API specifics (rate limits, historical depth, costs) — `005`.
- India transaction-cost rates (STT, exchange charges, GST, stamp duty) for the paper cost model — `011` §3.
- Swiss Ephemeris licensing if the project ever becomes distributed — `000` §3.
