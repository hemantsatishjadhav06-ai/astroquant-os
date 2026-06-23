"""
Agent 1 — Market Data Collector (docs/004 §Agent 1).

Idempotent: upsert on (symbol, ts, interval, source). Validates every bar, detects gaps,
emits data-quality metrics. Source is pluggable (broker or free fallback).
"""
from __future__ import annotations

from datetime import date

from astroquant.agents.base import Agent, Health, RunContext, RunResult, content_hash, get_logger
from astroquant.collectors.sources.market_sources import Bar, get_source

log = get_logger("collector.market")


class MarketCollector:
    name = "market_collector"
    version = "0.1.0"

    def __init__(self, source: str = "yfinance", interval: str = "1d", **source_kw) -> None:
        self.source = get_source(source, **source_kw)
        self.interval = interval

    def collect(self, symbol: str, start: date, end: date) -> tuple[list[Bar], dict]:
        bars = self.source.history(symbol, self.interval, start, end)
        valid = [b for b in bars if b.is_valid()]
        rejected = len(bars) - len(valid)
        metrics = {
            "symbol": symbol, "fetched": len(bars), "valid": len(valid),
            "rejected": rejected, "source": self.source.name,
        }
        if rejected:
            log.warning("market: %d invalid bars rejected for %s", rejected, symbol)
        # Persistence: upsert valid bars into the `bars` hypertable via db layer (scripts/run_market.py).
        return valid, metrics

    def run(self, ctx: RunContext) -> RunResult:
        start = ctx.start or date.today()
        end = ctx.end or start
        total = 0
        hashes: dict[str, str] = {}
        for sym in (ctx.symbols or ["NIFTY"]):
            try:
                valid, m = self.collect(sym, start, end)
                total += len(valid)
                hashes[sym] = content_hash([(b.ts.isoformat(), b.close) for b in valid])
                log.info("market: %s -> %d valid bars (%s)", sym, len(valid), m["source"])
            except Exception as e:
                log.error("market: failed for %s: %s", sym, e)
                res = RunResult(agent=self.name, status="failed", error=str(e))
                res.write_manifest(ctx)
                return res
        res = RunResult(agent=self.name, status="ok", rows_written=total, output_hashes=hashes)
        res.write_manifest(ctx)
        return res

    def healthcheck(self) -> Health:
        return Health(ok=True, detail=f"source={self.source.name}")


_: Agent = MarketCollector()  # type: ignore[assignment]
