# Document 005 — Data Platform

**Audience:** Claude Code. This document specifies every data source, what to pull, how to store it,
and the gotchas. Pair with `006` (schema) and `004` (collector agents).

> **Verify-before-build note:** API rate limits, pricing, historical-depth, and endpoint shapes for
> Indian brokers change frequently. **VERIFIED baseline (June 2026, see `VERIFICATION_ADDENDUM.md`):**
> Kite Connect is ₹500/mo per API key with live + ~10yr intraday history bundled (recommended primary);
> Upstox & Angel One SmartAPI are free (good secondary/cross-check); deep tick history still needs a
> paid vendor. Confirm current specifics against each provider's live docs before finalizing configs.

---

## 1. Market data (NSE / BSE / indices / futures / VIX)

### Provider options
| Provider | Strengths | Watch-outs |
|---|---|---|
| **Zerodha Kite Connect** | Mature, well-documented, reliable WebSocket ticks, broad instrument coverage. | Paid monthly per app; historical-data API has depth limits per request; requires a Zerodha account. |
| **Upstox Developer API** | Free tier exists; good REST + WebSocket; decent historical. | Rate limits; coverage/depth nuances. |
| **Angel One SmartAPI** | Free; full instrument master; WebSocket streaming. | Throttling; you manage the instrument master yourself. |
| **TrueData / GDFL** (paid vendors) | Clean, deep tick/1-min history — best for research backfill. | Subscription cost. |
| **NSE/BSE official + Nifty Indices** | Authoritative EOD, index constituents, VIX. | Scraping fragile; respect terms; use for cross-checks. |

**Recommendation for a research platform:** use one broker API (Kite or Upstox) for live/recent data
and a paid vendor (TrueData/GDFL) or careful broker-history backfill for deep history. Always store a
`source` column and cross-check daily bar counts between two sources (this is the G1 gate).

### What to store
- **Bars:** OHLCV at 1-minute, 5-minute, and daily for the symbol universe.
- **Indices:** NIFTY 50, BANKNIFTY, FINNIFTY, sector indices, INDIA VIX.
- **Futures:** continuous + per-expiry series with OI.
- **Corporate actions:** splits, bonuses, dividends → for adjusted-price computation (store both raw and adjusted; never silently overwrite).
- **Symbol master:** instrument tokens per provider, lot sizes, tick sizes, listing/delisting dates (delisting dates are essential to avoid **survivorship bias** — see `007`).

### Gotchas
- **Survivorship bias:** include delisted/merged symbols in history. A universe of only currently-listed stocks systematically overstates backtest returns.
- **Adjusted vs raw prices:** features and labels must be consistent. Decide and document. Generally: compute returns on adjusted prices; display raw.
- **Holidays & half-days:** maintain an NSE/BSE trading calendar table; never assume Mon–Fri.
- **Token churn:** instrument tokens change across expiries; key your storage on stable symbols, map tokens per source.

---

## 2. Options data

- **Pull:** full chains for index underlyings (NIFTY, BANKNIFTY, FINNIFTY) and a set of liquid stock underlyings — strike, expiry, type (CE/PE), LTP, OI, change-in-OI, IV, volume, bid/ask.
- **Derive (in Feature Factory, not collector):** PCR (OI-based and volume-based), max-pain strike, IV skew/smile snapshots, ATM IV, OI build-up classification (long/short build-up, covering).
- **Cadence:** intraday snapshots (configurable; 5-min is a reasonable default) + an authoritative EOD snapshot.
- **Storage:** `option_chain_snapshots` hypertable keyed `(underlying, expiry, strike, type, snapshot_ts)`.
- **Gotcha:** IV definitions differ by source (which model, which rate). Record the source's IV and optionally recompute your own (Black-76 for index options) for consistency.

---

## 3. Astronomy / astrology data (the engine, not "astrology software")

**Principle (from your own brief):** do **not** start from astrology software. Compute from astronomy
(Swiss Ephemeris), then derive Vedic constructs explicitly and reproducibly.

### Library
- **Swiss Ephemeris** (C) via **pyswisseph** binding or a thin C++ wrapper (`pybind11`).
- Set **sidereal mode with Lahiri ayanamsa** (`SE_SIDM_LAHIRI`) for Vedic longitudes; also store tropical for cross-checking.
- Cross-check a sample against **NASA JPL Horizons** (independent ground truth).

### Compute & store (daily; intraday optional for Moon)
- **Longitudes** (sidereal + tropical), **speed** (for retrograde detection), per body: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Rahu (mean+true node), Ketu.
- **Sign (rasi)**, **nakshatra + pada**, **retrograde flag**, **combustion flag**.
- **Moon phase / tithi**, **paksha**.
- **Aspects/angles:** pairwise separation in degrees; flag classical aspect angles (conjunction 0°, opposition 180°, etc.) — store the raw angle so ML can use continuous features, not just boolean aspects.
- **Vimshottari dasha / antardasha** timelines (function of Moon's nakshatra at an epoch; for *market* timing you'll typically anchor to index inception or use transit-based features rather than a natal chart — document your choice explicitly).

### Why this matters methodologically
Astro features are **deterministic functions of time**, so they carry zero data-collection look-ahead.
But that very determinism makes them dangerously easy to overfit: with enough planetary combinations,
some will *appear* predictive by chance. This is exactly why `007`'s multiple-testing correction is
non-negotiable for this family.

---

## 4. Gann data

Computed by Agent 5 (C++). Store separately from market data (`gann_*` tables, see `006`).
- **Time cycles:** 45/90/180/360/720-day projections from designated pivots.
- **Square of Nine:** numeric grid; levels at cardinal/diagonal angles around a reference price.
- **Gann angles:** 1×1 etc. as price-per-time slopes from an anchor.
- **Price-time squaring:** dates where accumulated price range "squares" elapsed time.

**Treat all Gann outputs as candidate features only.** No Gann construct is a signal until `009`/`010` say so.

---

## 5. News & sentiment

### Sources
- **GDELT Project** — global event/news graph, free, good for macro/event coverage and tone scoring; useful for India-relevant global events.
- **NewsAPI** — headline/article retrieval (note: free tier has delay + limited history; paid for production).
- **Indian-specific:** consider RSS/feeds from major Indian financial outlets and exchange filings (corporate announcements) for company-level news; respect each source's terms.

### Pipeline
1. **Ingest** raw articles → MongoDB `news` (url, source, ts, title, body, symbols_mentioned).
2. **Entity-link** to symbols (ticker/company-name matching).
3. **Sentiment** via an LLM or a finance-tuned classifier → `bullish | bearish | neutral` + score + rationale. Store model + version (sentiment is model-dependent; reproducibility requires versioning).
4. **Aggregate** to `news_sentiment` (symbol, date, net_sentiment, article_count, dispersion).
5. **Feature Factory** turns these into features (sentiment momentum, surprise vs baseline, volume of coverage).

### Gotchas
- **Timestamp discipline:** use *publication* time, and lag it (news at 14:00 cannot inform a feature for that day's open). Map every article to the next tradable bar after publication.
- **Look-ahead via revisions/backfill:** if a source backfills articles, you can accidentally "know" news before it was public. Store ingestion time separately from publication time.
- **Sentiment drift:** if you change the sentiment model, re-tag historically or version features so old and new aren't mixed.

---

## 6. Economic / macro data

- **FRED** (St. Louis Fed) — USDINR, crude, gold, US yields, DXY, many global series; supports data **vintages** (ALFRED) which you should use.
- **World Bank** — GDP, annual macro indicators.
- **RBI / MOSPI** — India CPI/WPI, repo rate, India 10Y G-Sec, IIP. (Often manual/structured downloads; build careful parsers and store release dates.)

### Critical rule: store vintages / release dates
Macro series are **revised**. The value you'd have known on date *T* is the *then-current vintage*, not
today's revised figure. `economic_data` must carry `(series_id, reference_date, value, release_date)`,
and features must join on `release_date <= as_of`. Skipping this is one of the most common silent
look-ahead bugs in macro-driven research.

---

## 7. Storage routing (which datastore gets what)

| Data | Store | Table/Collection |
|---|---|---|
| 1m/5m/daily bars, option snapshots | **TimescaleDB** hypertables | `bars`, `option_chain_snapshots` |
| Symbols, calendars, corp actions, signals, backtests, strategies, planetary_data, gann_*, economic_data | **PostgreSQL** | see `006` |
| Raw news, research notes, events, experiments | **MongoDB** | `news`, `research`, `experiments` |
| Embeddings: knowledge, discoveries, patterns | **Vector DB (pgvector→Qdrant)** | `knowledge`, `discoveries`, `patterns` |

---

## 8. Data-quality contract (enforced by Agent 15)

Every collector must, before commit:
- reject impossible values (negative volume, high<low, IV<0, longitude∉[0,360));
- detect and log gaps against the trading calendar;
- cross-check at least daily counts against a second source where one exists;
- record per-run quality metrics (rows, gaps_healed, anomalies) into the manifest.

Bad data is quarantined (flagged, not deleted) and surfaced in the daily report. **Garbage data is the
fastest way to "discover" a fake astrological edge** — Agent 15 is your first line of defense.
