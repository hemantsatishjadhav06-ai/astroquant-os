"""Tests for technical indicators, the chart builder, and the /chart endpoint."""
import numpy as np
import pytest

from astroquant.analysis import indicators as ind
from astroquant.analysis.chart import build_chart


def test_sma_ema_known():
    x = np.arange(1, 11, dtype=float)            # 1..10
    assert ind.sma(x, 5)[-1] == 8.0              # mean(6..10)
    assert np.isnan(ind.sma(x, 5)[3])            # warm-up
    assert abs(ind.ema(x, 5)[-1] - 8.0) < 1.5    # EMA near the recent mean


def test_rsi_bounds_and_trend():
    up = np.arange(1, 60, dtype=float)
    r = ind.rsi(up, 14)
    assert np.nanmax(r) <= 100.0 and np.nanmin(r) >= 0.0
    assert r[-1] > 90                            # pure uptrend → RSI very high


def test_bollinger_ordering():
    rng = np.random.default_rng(0)
    x = np.cumsum(rng.normal(0, 1, 100)) + 100
    mid, up, lo = ind.bollinger(x, 20, 2)
    i = -1
    assert lo[i] < mid[i] < up[i]


def test_macd_hist_identity():
    x = np.cumsum(np.random.default_rng(1).normal(0, 1, 80)) + 100
    m, s, h = ind.macd(x)
    j = ~np.isnan(h)
    assert np.allclose(h[j], (m - s)[j], equal_nan=False)


def test_build_chart_shape():
    ch = build_chart("NIFTY", source="synthetic", interval="1d", years=2)
    assert ch["n"] > 100 and len(ch["candles"]) == ch["n"]
    k = ch["candles"][0]
    assert {"time", "open", "high", "low", "close"} <= set(k)
    for key in ("sma20", "sma50", "ema20", "bb_upper", "rsi14", "macd"):
        assert ch["indicators"][key]
    assert ch["levels"]["resistances"] and ch["levels"]["supports"]


def test_chart_endpoint():
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from astroquant.api.app import app
    c = TestClient(app)
    r = c.get("/chart", params={"symbol": "NIFTY", "source": "synthetic", "interval": "1d", "years": 2})
    assert r.status_code == 200
    d = r.json()
    assert d["candles"] and d["indicators"]["sma20"] and d["volume"]
