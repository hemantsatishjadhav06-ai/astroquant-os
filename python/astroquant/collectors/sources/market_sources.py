"""
Market data source adapters (docs/005 §1).

A clean interface so the collector is broker-agnostic. Ships:
  - YFinanceSource  : free fallback for indices (testing / G1 cross-check source)
  - KiteSource      : stub wired for Zerodha Kite Connect (Rs 500/mo, 10yr intraday) — fill in creds
Add UpstoxSource / SmartAPISource the same way.

Every Bar is provider-stamped (`source`) so the warehouse can cross-check two sources (gate G1).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol


@dataclass
class Bar:
    symbol: str
    ts: datetime
    interval: str          # 1m / 5m / 1d
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: int | None
    source: str

    def is_valid(self) -> bool:
        return (
            self.high >= self.low
            and self.high >= self.open >= self.low
            and self.high >= self.close >= self.low
            and self.volume >= 0
        )


class MarketSource(Protocol):
    name: str
    def history(self, symbol: str, interval: str, start: date, end: date) -> list[Bar]: ...


class YFinanceSource:
    """Free fallback. Good for indices (^NSEI=NIFTY, ^NSEBANK=BANKNIFTY) and EOD cross-checks."""
    name = "yfinance"

    _MAP = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "INDIAVIX": "^INDIAVIX"}
    _INTERVAL = {"1d": "1d", "5m": "5m", "1m": "1m"}

    def history(self, symbol: str, interval: str, start: date, end: date) -> list[Bar]:
        import yfinance as yf  # lazy import; optional dependency [data]

        ticker = self._MAP.get(symbol, symbol)
        df = yf.download(
            ticker, start=start.isoformat(), end=end.isoformat(),
            interval=self._INTERVAL.get(interval, "1d"), progress=False, auto_adjust=False,
        )
        bars: list[Bar] = []
        for ts, row in df.iterrows():
            def val(col: str) -> float:
                v = row[col]
                return float(v.iloc[0] if hasattr(v, "iloc") else v)
            bars.append(Bar(
                symbol=symbol, ts=ts.to_pydatetime(), interval=interval,
                open=val("Open"), high=val("High"), low=val("Low"), close=val("Close"),
                volume=int(val("Volume")), oi=None, source=self.name,
            ))
        return bars


class SyntheticSource:
    """
    Deterministic, offline OHLCV generator (docs/005 — research/test source).

    Produces reproducible business-day bars via a seeded geometric random walk with a slow
    regime drift, so the *entire* research pipeline (features → research engine → paper trade)
    runs with **no network and no broker keys** and gives identical results across machines.
    NOT a source for findings — it is the leakage/over-fitting harness's clean room.
    """
    name = "synthetic"

    def __init__(self, base_price: float = 20000.0, annual_vol: float = 0.18, seed: int = 7) -> None:
        self.base_price = base_price
        self.annual_vol = annual_vol
        self.seed = seed

    def history(self, symbol: str, interval: str, start: date, end: date) -> list[Bar]:
        import numpy as np  # core dependency; lazy to mirror the other sources

        # Seed deterministically from (symbol, start) so every (symbol, window) is reproducible.
        seed = (hash((symbol, self.seed, start.toordinal())) & 0xFFFFFFFF)
        rng = np.random.default_rng(seed)

        days = [
            start + timedelta(days=i)
            for i in range((end - start).days + 1)
            if (start + timedelta(days=i)).weekday() < 5  # business days only
        ]
        if not days:
            return []

        daily_vol = self.annual_vol / math.sqrt(252.0)
        bars: list[Bar] = []
        price = self.base_price
        for i, d in enumerate(days):
            regime_drift = 0.0004 * math.sin(i / 40.0)  # slow bull/bear stretches
            ret = float(rng.normal(regime_drift, daily_vol))
            prev = price
            price = max(1.0, prev * math.exp(ret))
            open_, close = prev, price
            hi = max(open_, close) * (1 + abs(float(rng.normal(0, daily_vol / 3))))
            lo = min(open_, close) * (1 - abs(float(rng.normal(0, daily_vol / 3))))
            vol = int(abs(float(rng.normal(1_000_000, 250_000))))
            bars.append(Bar(
                symbol=symbol, ts=datetime(d.year, d.month, d.day),
                interval=interval, open=round(open_, 2), high=round(hi, 2),
                low=round(lo, 2), close=round(close, 2), volume=vol, oi=None, source=self.name,
            ))
        return bars


class KiteSource:
    """
    Zerodha Kite Connect adapter (stub).
    Paid plan: Rs 500/mo per API key, live + ~10yr intraday history bundled.
    Requires a static IP for ORDER placement (data endpoints unaffected) — irrelevant here,
    AstroQuant is read-only market data only (no order path, docs/011 §8).
    """
    name = "kite"

    def __init__(self, api_key: str, access_token: str) -> None:
        self.api_key = api_key
        self.access_token = access_token

    def history(self, symbol: str, interval: str, start: date, end: date) -> list[Bar]:
        # from kiteconnect import KiteConnect
        # kite = KiteConnect(api_key=self.api_key); kite.set_access_token(self.access_token)
        # token = <resolve from instrument master>; data = kite.historical_data(token, start, end, interval)
        raise NotImplementedError(
            "Wire kiteconnect + instrument-master token resolution. "
            "Use YFinanceSource for now (set AQ_BROKER=yfinance)."
        )


def get_source(name: str, **kw) -> MarketSource:
    if name == "yfinance":
        return YFinanceSource()
    if name == "synthetic":
        return SyntheticSource(**{k: kw[k] for k in ("base_price", "annual_vol", "seed") if k in kw})
    if name in ("nse", "bse", "mcx"):
        # Free real NSE/BSE/MCX data (Yahoo redistribution + proxies) with synthetic fallback offline.
        from astroquant.collectors.sources.india_sources import BSESource, MCXSource, NSESource
        fallback = bool(kw.get("fallback_synthetic", True))
        return {"nse": NSESource, "bse": BSESource, "mcx": MCXSource}[name](fallback)
    if name == "kite":
        return KiteSource(kw.get("api_key", ""), kw.get("access_token", ""))
    raise ValueError(f"unknown market source: {name}")
