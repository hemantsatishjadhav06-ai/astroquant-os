-- 002_hypertables.sql — run AFTER tables are created (Alembic) to convert time-series tables.
-- Idempotent-ish: create_hypertable with if_not_exists.

SELECT create_hypertable('bars', 'ts', if_not_exists => TRUE, migrate_data => TRUE);

-- Continuous aggregate: roll 1-minute bars up to 5-minute (illustrative; refine as needed).
-- Requires bars to contain 1m rows. Materialized view refreshes incrementally.
CREATE MATERIALIZED VIEW IF NOT EXISTS bars_5m
WITH (timescaledb.continuous) AS
SELECT
    symbol_id,
    source,
    time_bucket('5 minutes', ts) AS bucket,
    first(open, ts)  AS open,
    max(high)        AS high,
    min(low)         AS low,
    last(close, ts)  AS close,
    sum(volume)      AS volume
FROM bars
WHERE interval = '1m'
GROUP BY symbol_id, source, bucket
WITH NO DATA;

-- Refresh policy: keep the last ~7 days continuously fresh (tune for your ingest cadence).
SELECT add_continuous_aggregate_policy('bars_5m',
    start_offset => INTERVAL '7 days',
    end_offset   => INTERVAL '1 minute',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE);
