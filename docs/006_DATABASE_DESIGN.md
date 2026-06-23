# Document 006 — Database Design

**Audience:** Claude Code. Concrete schema across PostgreSQL + TimescaleDB, MongoDB, and Vector DB.
Use Alembic for migrations. All timestamps are UTC (`timestamptz`); store an explicit `exchange_tz`
where market-local time matters. Natural keys drive upserts (idempotency, per `000` §6).

---

## PostgreSQL (structured)

### Reference & market
```sql
-- Instrument master (one row per logical symbol; provider tokens mapped separately)
CREATE TABLE symbols (
    symbol_id      BIGSERIAL PRIMARY KEY,
    symbol         TEXT NOT NULL,            -- e.g. 'RELIANCE'
    exchange       TEXT NOT NULL,            -- NSE/BSE/MCX
    instrument     TEXT NOT NULL,            -- EQ / FUT / OPT / INDEX
    isin           TEXT,
    sector         TEXT,
    lot_size       INT,
    tick_size      NUMERIC,
    listing_date   DATE,
    delisting_date DATE,                     -- NULL if active (needed to avoid survivorship bias)
    is_active      BOOLEAN DEFAULT TRUE,
    UNIQUE (symbol, exchange, instrument)
);

CREATE TABLE symbol_tokens (                 -- per-provider instrument tokens
    symbol_id  BIGINT REFERENCES symbols(symbol_id),
    source     TEXT NOT NULL,                -- kite/upstox/smartapi/truedata
    token      TEXT NOT NULL,
    expiry     DATE,
    strike     NUMERIC,
    opt_type   TEXT,                         -- CE/PE/NULL
    PRIMARY KEY (source, token, expiry, strike, opt_type)
);

CREATE TABLE trading_calendar (
    exchange   TEXT NOT NULL,
    session_date DATE NOT NULL,
    is_holiday BOOLEAN DEFAULT FALSE,
    open_time  TIME, close_time TIME,
    PRIMARY KEY (exchange, session_date)
);

CREATE TABLE corporate_actions (
    symbol_id BIGINT REFERENCES symbols(symbol_id),
    ex_date   DATE NOT NULL,
    action    TEXT NOT NULL,                 -- split/bonus/dividend
    ratio_num NUMERIC, ratio_den NUMERIC,
    amount    NUMERIC,
    PRIMARY KEY (symbol_id, ex_date, action)
);
```

### Astronomy
```sql
CREATE TABLE planetary_data (
    obs_date            DATE NOT NULL,
    body                TEXT NOT NULL,       -- Sun..Saturn, Rahu, Ketu
    longitude_sidereal  NUMERIC NOT NULL,    -- Lahiri
    longitude_tropical  NUMERIC NOT NULL,
    speed               NUMERIC,             -- deg/day (sign => retrograde)
    is_retrograde       BOOLEAN,
    sign                SMALLINT,            -- rasi 1..12
    nakshatra           SMALLINT,            -- 1..27
    pada                SMALLINT,            -- 1..4
    is_combust          BOOLEAN,
    source              TEXT DEFAULT 'swisseph',
    PRIMARY KEY (obs_date, body)
);

CREATE TABLE planetary_aspects (
    obs_date  DATE NOT NULL,
    body_a    TEXT NOT NULL,
    body_b    TEXT NOT NULL,
    angle_deg NUMERIC NOT NULL,              -- 0..180 separation (store raw for ML)
    aspect    TEXT,                          -- conjunction/opposition/etc (nullable)
    PRIMARY KEY (obs_date, body_a, body_b)
);

CREATE TABLE moon_phase (
    obs_date DATE PRIMARY KEY,
    tithi    SMALLINT, paksha TEXT,
    phase_angle NUMERIC, illumination NUMERIC
);

CREATE TABLE dasha_periods (
    anchor      TEXT NOT NULL,               -- which chart/epoch this dasha is anchored to
    level       SMALLINT NOT NULL,           -- 1=maha,2=antar...
    lord        TEXT NOT NULL,
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    PRIMARY KEY (anchor, level, start_date)
);
```

### Gann
```sql
CREATE TABLE gann_cycles (
    symbol_id   BIGINT REFERENCES symbols(symbol_id),
    anchor_date DATE NOT NULL,
    anchor_type TEXT,                        -- pivot_high/pivot_low
    cycle_len   INT NOT NULL,                -- 45/90/180/360/720
    target_date DATE NOT NULL,
    PRIMARY KEY (symbol_id, anchor_date, cycle_len)
);

CREATE TABLE gann_levels (
    symbol_id BIGINT REFERENCES symbols(symbol_id),
    calc_date DATE NOT NULL,
    ref_price NUMERIC NOT NULL,
    level_kind TEXT,                         -- so9_cardinal/so9_diagonal
    price_level NUMERIC NOT NULL,
    PRIMARY KEY (symbol_id, calc_date, level_kind, price_level)
);

CREATE TABLE gann_angles (
    symbol_id BIGINT REFERENCES symbols(symbol_id),
    anchor_date DATE NOT NULL,
    angle_kind TEXT,                         -- 1x1/2x1/1x2...
    slope_per_day NUMERIC,
    PRIMARY KEY (symbol_id, anchor_date, angle_kind)
);
```

### Macro
```sql
CREATE TABLE economic_data (
    series_id      TEXT NOT NULL,
    reference_date DATE NOT NULL,            -- the period the value refers to
    value          NUMERIC,
    release_date   DATE NOT NULL,            -- when it became public (VINTAGE — prevents look-ahead)
    source         TEXT,                     -- fred/worldbank/rbi/mospi
    PRIMARY KEY (series_id, reference_date, release_date)
);
```

### Research / signals / strategies / backtests
```sql
CREATE TABLE hypotheses (
    hypothesis_id TEXT PRIMARY KEY,          -- e.g. RQ-004
    statement     TEXT, spec JSONB,          -- the full pre-registration record
    status        TEXT,                      -- registered/tested/...
    registered_at TIMESTAMPTZ
);

CREATE TABLE signals (
    signal_id     BIGSERIAL PRIMARY KEY,
    hypothesis_id TEXT REFERENCES hypotheses(hypothesis_id),
    name          TEXT, family TEXT,         -- technical/market/astro/gann/news/macro
    definition    JSONB,
    verdict       TEXT,                      -- edge/no_edge/conditional
    effect_size   NUMERIC, p_raw NUMERIC, p_adj NUMERIC,
    n_comparisons INT, dsr NUMERIC, pbo NUMERIC,
    dataset_hash  TEXT, code_commit TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE strategies (
    strategy_id BIGSERIAL PRIMARY KEY,
    name TEXT, signal_id BIGINT REFERENCES signals(signal_id),
    spec JSONB, status TEXT
);

CREATE TABLE backtests (
    backtest_id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT REFERENCES strategies(strategy_id),
    start_date DATE, end_date DATE,
    sharpe NUMERIC, sortino NUMERIC, max_dd NUMERIC,
    profit_factor NUMERIC, win_rate NUMERIC,
    dsr NUMERIC, pbo NUMERIC,
    metrics JSONB, manifest_path TEXT, code_commit TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Paper trading
```sql
CREATE TABLE paper_orders (
    order_id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT, symbol_id BIGINT,
    signal_ts TIMESTAMPTZ, order_ts TIMESTAMPTZ,
    side TEXT, qty INT, type TEXT, limit_price NUMERIC, status TEXT
);
CREATE TABLE paper_fills (
    fill_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES paper_orders(order_id),
    fill_ts TIMESTAMPTZ, price NUMERIC, qty INT,
    slippage NUMERIC, costs NUMERIC, cost_model_version TEXT
);
CREATE TABLE paper_positions (
    strategy_id BIGINT, symbol_id BIGINT,
    qty INT, avg_price NUMERIC, realized_pnl NUMERIC, unrealized_pnl NUMERIC,
    as_of TIMESTAMPTZ, PRIMARY KEY (strategy_id, symbol_id, as_of)
);
CREATE TABLE paper_pnl (
    strategy_id BIGINT, as_of DATE,
    equity NUMERIC, daily_pnl NUMERIC, drawdown NUMERIC,
    PRIMARY KEY (strategy_id, as_of)
);
CREATE TABLE performance_audit (
    strategy_id BIGINT, as_of DATE,
    live_sharpe NUMERIC, backtest_sharpe NUMERIC, gap NUMERIC, flag TEXT,
    PRIMARY KEY (strategy_id, as_of)
);
```

---

## TimescaleDB (time-series hypertables)

```sql
CREATE TABLE bars (
    symbol_id BIGINT NOT NULL,
    ts        TIMESTAMPTZ NOT NULL,
    interval  TEXT NOT NULL,                 -- 1m/5m/1d
    open NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC,
    volume BIGINT, oi BIGINT,
    adj_close NUMERIC,                       -- corporate-action adjusted
    source TEXT NOT NULL,
    PRIMARY KEY (symbol_id, ts, interval, source)
);
SELECT create_hypertable('bars', 'ts');
-- continuous aggregates roll 1m -> 5m -> daily; refresh policies for incremental updates.

CREATE TABLE option_chain_snapshots (
    underlying_id BIGINT NOT NULL,
    snapshot_ts   TIMESTAMPTZ NOT NULL,
    expiry DATE, strike NUMERIC, opt_type TEXT,  -- CE/PE
    ltp NUMERIC, oi BIGINT, oi_change BIGINT,
    iv NUMERIC, volume BIGINT, bid NUMERIC, ask NUMERIC,
    source TEXT,
    PRIMARY KEY (underlying_id, snapshot_ts, expiry, strike, opt_type, source)
);
SELECT create_hypertable('option_chain_snapshots', 'snapshot_ts');
```

**Feature store** (point-in-time correct): a wide partitioned table or columnar files (Parquet) keyed
`(as_of_ts, symbol_id)` plus a `feature_catalog`. For research speed, persist as date-partitioned
Parquet read by polars; mirror catalog/metadata in Postgres.

```sql
CREATE TABLE feature_catalog (
    feature_id TEXT PRIMARY KEY,
    name TEXT, family TEXT,                  -- technical/market/astro/gann/news/macro
    definition JSONB, definition_hash TEXT, version TEXT
);
```

---

## MongoDB (unstructured)
- **`news`**: `{_id, url, source, published_ts, ingested_ts, title, body, symbols[], lang}` (publish vs ingest time both stored — `005` §5).
- **`news_sentiment`** (or Postgres): `{symbol, date, net_sentiment, score, article_count, model, model_version}`.
- **`research`**: free-form research notes, narrative findings, LLM write-ups (linked to `hypothesis_id`).
- **`experiments`**: every candidate from Pattern Discovery — params, n_comparisons, raw results, status.
- **`events`**: pipeline/run event log.

## Vector DB (pgvector → Qdrant)
- **`knowledge`**: embedded reference material (methodology, domain notes) for retrieval.
- **`discoveries`**: embedded verdicts (pass *and* fail) — preserves the denominator, prevents re-testing.
- **`patterns`**: embedded candidate hypotheses for dedup before testing.

---

## Cross-store integrity rules
- Every `backtests`/`signals` row references a `dataset_hash` + `code_commit` reproducible from a manifest.
- Feature rows carry `as_of_ts`; training joins enforce `as_of_ts <= label_origin_ts`.
- Macro joins use `release_date <= as_of`. News joins use `published_ts < bar_ts`.
- Delisted symbols are retained; universe construction is date-aware.
