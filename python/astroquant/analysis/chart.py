"""
Chart data builder — OHLCV candles + technical-indicator overlays + Gann levels for one symbol.

Feeds the interactive candlestick chart in the dashboard (TradingView Lightweight Charts). All series
are date-aligned ('YYYY-MM-DD'); indicator warm-up nans are dropped so the front-end gets clean points.
"""
from __future__ import annotations

from datetime import date

import numpy as np

from astroquant.analysis import indicators as ind
from astroquant.collectors.gann import square_of_nine
from astroquant.collectors.sources.market_sources import get_source

_RANGE_YEARS = {"6m": 1, "1y": 1, "2y": 2, "5y": 5}


def _series(dates: list[str], arr: np.ndarray) -> list[dict]:
    return [{"time": d, "value": round(float(v), 4)} for d, v in zip(dates, arr) if v == v]  # v==v drops nan


def build_chart(symbol: str, source: str = "nse", interval: str = "1d", years: int = 2) -> dict:
    end = date.today()
    start = date(end.year - max(1, years), 1, 1)
    kwargs = {"fallback_synthetic": True} if source in ("nse", "bse", "mcx") else {}
    bars = get_source(source, **kwargs).history(symbol, interval, start, end)
    if len(bars) < 30:
        raise ValueError(f"not enough data for {symbol} ({len(bars)} bars)")

    dates = [b.ts.date().isoformat() for b in bars]
    o = np.array([b.open for b in bars]); h = np.array([b.high for b in bars])
    low = np.array([b.low for b in bars]); c = np.array([b.close for b in bars])
    v = np.array([b.volume for b in bars], dtype=float)

    candles = [{"time": dates[i], "open": round(float(o[i]), 2), "high": round(float(h[i]), 2),
                "low": round(float(low[i]), 2), "close": round(float(c[i]), 2)} for i in range(len(bars))]
    volume = [{"time": dates[i], "value": int(v[i]),
               "color": "#2f7a5f" if c[i] >= o[i] else "#7a3b3b"} for i in range(len(bars))]

    macd_line, macd_sig, macd_hist = ind.macd(c)
    bb_mid, bb_up, bb_lo = ind.bollinger(c)
    indicators = {
        "sma20": _series(dates, ind.sma(c, 20)), "sma50": _series(dates, ind.sma(c, 50)),
        "ema20": _series(dates, ind.ema(c, 20)),
        "bb_upper": _series(dates, bb_up), "bb_lower": _series(dates, bb_lo), "bb_mid": _series(dates, bb_mid),
        "rsi14": _series(dates, ind.rsi(c, 14)),
        "macd": _series(dates, macd_line), "macd_signal": _series(dates, macd_sig),
        "macd_hist": _series(dates, macd_hist),
    }

    last = float(c[-1])
    levels = square_of_nine(last)
    win = c[-90:] if len(c) >= 90 else c
    chart_levels = {
        "resistances": sorted([round(l.price, 2) for l in levels if l.price > last])[:3],
        "supports": sorted([round(l.price, 2) for l in levels if 0 < l.price < last], reverse=True)[:3],
        "pivot_high": round(float(win.max()), 2), "pivot_low": round(float(win.min()), 2),
        "last_close": round(last, 2),
    }
    return {"symbol": symbol.upper(), "source": bars[-1].source, "interval": interval,
            "n": len(bars), "candles": candles, "volume": volume,
            "indicators": indicators, "levels": chart_levels}
