# Document 004 — Agent Architecture

**Audience:** Claude Code. Each agent below is a buildable unit with a defined contract.
**Communication model:** agents are independent services that read/write the warehouse and emit
events on **Redis Streams**. No agent imports another agent. The **Orchestrator** schedules and
sequences them; **n8n** triggers schedules and handles ops alerts.

## Agent contract (every agent implements this)

```python
class Agent(Protocol):
    name: str
    version: str
    def run(self, ctx: RunContext) -> RunResult: ...   # idempotent
    def healthcheck(self) -> Health: ...
```

- `RunContext`: date range / symbols / config / run_id / seeds.
- `RunResult`: rows_written, output_hashes, metrics, status, manifest_path.
- Every run writes a **manifest** (see `000` §6) and emits `agent.<name>.completed` on the bus.
- Failures emit `agent.<name>.failed` with a structured error; the Orchestrator decides retry/halt.

---

## Agent 1 — Market Data Collector
- **Layer:** 1 · **Tech:** Python
- **Responsibilities:** pull OHLCV + sector/index data for NSE/BSE stocks, NIFTY, BANKNIFTY, sector indices, futures, VIX. Backfill history; incremental daily updates; gap detection & healing.
- **Inputs:** symbol universe (`symbols` table), broker API credentials, date range.
- **Outputs:** `bars` hypertable (1m/5m/daily), `index_bars`, updates to `symbols`.
- **Sources:** Upstox / Kite Connect / SmartAPI (see `005`).
- **Interfaces:** `collect(symbols, interval, start, end)`.
- **Validation:** every bar validated (high≥low, volume≥0, no duplicate keys); daily counts cross-checked vs a second source; emits data-quality metrics.
- **Idempotency:** upsert on `(symbol, ts, interval, source)`.

## Agent 2 — Options Collector
- **Layer:** 1 · **Tech:** Python
- **Responsibilities:** capture option chains for index + liquid stock underlyings — strikes, expiries, LTP, OI, IV, volume. Derive PCR (OI & volume), max-pain, IV skew snapshots.
- **Inputs:** underlyings list, expiries, broker option-chain endpoint.
- **Outputs:** `option_chain_snapshots` hypertable, `derived_options` (PCR, max_pain, skew).
- **Cadence:** intraday snapshots (configurable, e.g. every 5 min) + EOD close snapshot.
- **Notes:** OI is the high-value, hard-to-get-clean field — validate aggressively. Store raw snapshots; compute derivations in Feature Factory, not here (keep collector dumb & idempotent).

## Agent 3 — Economic Collector
- **Layer:** 1 · **Tech:** Python
- **Responsibilities:** pull macro series — inflation (CPI/WPI), GDP, RBI policy/interest rates, USDINR, crude oil, gold, India bond yields (10Y G-Sec), US 10Y, DXY.
- **Inputs:** series catalog (FRED series IDs, World Bank indicators, RBI sources).
- **Outputs:** `economic_data` (series_id, date, value, vintage/as_of).
- **Critical:** store **vintages** (release date vs reference date). Macro data is revised; using revised figures as if known in real time is a classic look-ahead bug. Always join on what was *known as of* the feature date.

## Agent 4 — Astronomy / Ephemeris Collector
- **Layer:** 1→2 · **Tech:** C++ core (Swiss Ephemeris) + Python wrapper
- **Responsibilities:** compute daily (and configurable intraday) geocentric **sidereal (Lahiri ayanamsa)** longitudes for Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu/Ketu (mean & true nodes); plus derived constructs: nakshatra + pada, rasi (sign), moon phase/tithi, retrograde flags, combustion, planetary aspects/angles (separation in degrees), Vimshottari dasha/antardasha periods. Cross-check a sample against **NASA JPL Horizons**.
- **Inputs:** date range, location (for any topocentric needs; geocentric default), ayanamsa = Lahiri.
- **Outputs:** `planetary_data` (date, body, longitude_sidereal, longitude_tropical, speed, retrograde, sign, nakshatra, pada), `planetary_aspects` (date, body_a, body_b, angle, aspect_type), `dasha_periods`, `moon_phase`.
- **Why C++:** computing positions for every body across decades of dates (and intraday) is millions of calls; native Swiss Ephemeris avoids Python overhead. Expose via `pybind11`.
- **Determinism:** these are pure functions of time — fully reproducible, no source-data risk. But **predictive** claims about them are still subject to out-of-sample testing (see `007`).
- **Correctness gate (G1):** sampled longitudes must match JPL Horizons within tolerance (arcseconds for planets; account for ayanamsa offset when comparing sidereal vs tropical/ICRF).

## Agent 5 — Gann Calculator
- **Layer:** 2 · **Tech:** C++ core + Python wrapper
- **Responsibilities:** generate Gann time constructs (45/90/180/360/720-day cycle anchors from designated pivots), Square of Nine levels around a price, Gann angles (1×1, 2×1, 1×2, etc.), and price-time squaring candidates.
- **Inputs:** anchor pivots (significant highs/lows from `bars`), reference prices, calendar.
- **Outputs:** `gann_cycles` (anchor_date, cycle_len, target_date, type), `gann_levels` (symbol, ref_price, so9_levels[], date), `gann_angles` (symbol, anchor, slope, projected_level_by_date).
- **Honesty note:** Gann's "natural" constructs are numerology-adjacent. Treat every Gann output as a *candidate feature to be tested*, never as a signal to act on. The doc that judges it is `007`/`009`.

## Agent 6 — Feature Builder (Feature Factory)
- **Layer:** 3 · **Tech:** Python (polars for speed)
- **Responsibilities:** assemble the point-in-time feature matrix `(date, symbol, features…)` from all warehouse sources. Tag each feature with `family ∈ {technical, market, astro, gann, news, macro}`. Enforce no-look-ahead. Version every feature definition.
- **Inputs:** `bars`, `option_chain_snapshots`, `planetary_data`, `gann_*`, `economic_data`, `news_sentiment`.
- **Outputs:** `feature_store` (partitioned by date), `feature_catalog` (id, name, family, definition_hash, version).
- **Detail:** full feature list in `008`. ~1000+ features/stock/day.
- **Leakage tests:** for each feature, assert it can be computed using only data with `ts <= as_of`. Shuffle-label test must collapse spurious predictive power to chance.

## Agent 7 — Pattern Discovery
- **Layer:** 4 · **Tech:** Python
- **Responsibilities:** *generate* candidate hypotheses systematically (e.g. "feature X in regime R precedes >Y% move in horizon H") and screen them, while **logging the number of comparisons made** so corrections can be applied. Dedup candidates against the Vector DB to avoid re-testing.
- **Inputs:** `feature_store`, hypothesis templates.
- **Outputs:** candidate hypotheses → `experiments` (MongoDB) + embeddings → Vector DB `patterns`.
- **Critical:** this agent is the main source of multiple-testing risk. It MUST report `n_comparisons` for every batch so `007`'s FDR/DSR machinery can deflate results. No candidate is ever promoted from this agent alone.

## Agent 8 — Research Analyst
- **Layer:** 4 · **Tech:** Python + LLM
- **Responsibilities:** take pre-registered RQs and Pattern Discovery candidates, run the formal test protocol (baseline vs augmented, ablation, SHAP, multiple-testing correction), and write a structured verdict with effect size, confidence, and caveats. LLM is used for *summarizing and narrating* results, never for deciding significance (that's the stats code).
- **Inputs:** registered hypotheses, `feature_store`, model outputs.
- **Outputs:** `research_findings` (Postgres `signals` + MongoDB `research`), discoveries → Vector DB.
- **Guardrail:** the LLM cannot override a statistical verdict. If stats say "no edge," the report says "no edge."

## Agent 9 — Backtester
- **Layer:** 5 · **Tech:** Python (VectorBT) + C++ event engine
- **Responsibilities:** turn a validated signal into a strategy and backtest it honestly — event-driven with realistic costs/slippage, walk-forward, Monte Carlo, regime splits. Compute Sharpe, Sortino, max drawdown, profit factor, and **Deflated Sharpe**.
- **Inputs:** strategy spec, `feature_store`, `bars`.
- **Outputs:** `backtests` (Postgres) with full metrics + run manifest.
- **Detail:** `010`.

## Agent 10 — Risk Manager
- **Layer:** cross-cutting · **Tech:** Python
- **Responsibilities:** enforce position/portfolio/strategy/system limits in backtest and paper; flag black-swan exposure; veto trades that breach limits.
- **Inputs:** proposed orders/positions, current portfolio, limit config.
- **Outputs:** approve/scale/reject decisions; risk metrics to `audit`.
- **Detail:** `012`.

## Agent 11 — Paper Trader  ← **first-class, build early**
- **Layer:** 6 · **Tech:** Python (+ optional C++ matching)
- **Responsibilities:** consume signals on **live (or replayed) market data**, simulate order placement and fills with realistic slippage/latency/fees, maintain a ledger + positions, compute live P&L and attribution. This is the forward-validation engine that gates any future live step.
- **Inputs:** signals, live/replayed `bars`/quotes, fill model config, risk approvals.
- **Outputs:** `paper_orders`, `paper_fills`, `paper_positions`, `paper_pnl`, attribution reports.
- **Detail:** `011`.

## Agent 12 — Live Trader  ← **DEFERRED / OUT OF SCOPE**
- Documented only as a stub. Must remain unbuilt until **G5** passes and compliance is addressed.

## Agent 13 — Performance Auditor
- **Layer:** cross · **Tech:** Python
- **Responsibilities:** continuously compare realized (paper) performance to backtest expectations; detect degradation, regime breaks, and overfitting tells (live-vs-backtest Sharpe gap). Maintain the "graveyard" of decayed signals.
- **Outputs:** audit metrics, decay alerts, `performance_audit` records.

## Agent 14 — Report Generator
- **Layer:** cross · **Tech:** Python + LLM
- **Responsibilities:** produce the daily/weekly research report — what was tested, what passed/failed, ranked candidates with caveats, paper P&L, risk status. Honest framing required (report nulls prominently).
- **Outputs:** Markdown/HTML/PDF reports; pushes summaries via n8n.

## Agent 15 — Anomaly Detector
- **Layer:** cross · **Tech:** Python
- **Responsibilities:** watch every pipeline for data anomalies (stale feeds, schema drift, distribution shifts, impossible values, ephemeris/JPL divergence) and raise alerts before bad data poisons research.
- **Outputs:** anomaly events on the bus; quarantine flags on suspect data.

## Agent 0 — Orchestrator
- **Layer:** cross · **Tech:** Python + n8n
- **Responsibilities:** schedule and sequence agents (DAG), enforce gates (won't run downstream agents if a gate is red), manage retries/backoff, own the run manifests, and surface system state. n8n handles cron + ops notifications; Python owns stateful research DAGs.
- **DAG (daily):** `[1,2,3,4] → 5 → 6 → 15(checks) → 7 → 8 → 9 → 11 → 13 → 14`.

---

## Message bus event taxonomy

```
data.bars.updated            {symbols, interval, range}
data.options.updated         {underlyings, snapshot_ts}
data.economic.updated        {series, range}
astro.ephemeris.updated      {range}
gann.cycles.updated          {anchors}
features.built               {date, n_features, dataset_hash}
research.hypothesis.tested    {hypothesis_id, verdict, p_adj, effect}
backtest.completed           {strategy_id, dsr, sharpe}
paper.fill                   {order_id, price, qty}
risk.veto                    {order_id, reason}
anomaly.raised               {source, severity, detail}
```

Agents subscribe only to what they need; the Orchestrator subscribes to all `*.completed`/`*.failed`.
