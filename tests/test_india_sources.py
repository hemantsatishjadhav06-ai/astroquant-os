"""Tests for the NSE/BSE adapters — symbol mapping + payload parsing (offline, no network)."""
from datetime import date

from astroquant.collectors.sources.india_sources import (
    NSESource,
    parse_yahoo_chart,
    to_yahoo_symbol,
)


def test_symbol_mapping():
    assert to_yahoo_symbol("RELIANCE", "NSE") == "RELIANCE.NS"
    assert to_yahoo_symbol("RELIANCE", "BSE") == "RELIANCE.BO"
    assert to_yahoo_symbol("NIFTY", "NSE") == "^NSEI"
    assert to_yahoo_symbol("SENSEX", "BSE") == "^BSESN"
    assert to_yahoo_symbol("^NSEBANK", "NSE") == "^NSEBANK"   # already a Yahoo index ticker


def test_parse_yahoo_chart_skips_nulls():
    payload = {"chart": {"result": [{
        "timestamp": [1704067200, 1704153600, 1704240000],
        "indicators": {"quote": [{
            "open": [100.0, None, 102.0],     # middle row has a null (holiday) -> skipped
            "high": [101.0, None, 103.0],
            "low": [99.0, None, 101.0],
            "close": [100.5, None, 102.5],
            "volume": [1000, None, 1200],
        }]},
    }]}}
    bars = parse_yahoo_chart("RELIANCE", "1d", "nse", payload)
    assert len(bars) == 2
    assert bars[0].source == "nse"
    assert bars[0].close == 100.5 and bars[1].close == 102.5
    assert all(b.is_valid() for b in bars)


def test_offline_fallback_to_synthetic(monkeypatch):
    # Force the live fetch to fail -> source must fall back to synthetic, stamped accordingly.
    import astroquant.collectors.sources.india_sources as mod

    def boom(*a, **k):
        raise ConnectionError("no network")

    monkeypatch.setattr(mod, "_fetch_yahoo", boom)
    bars = NSESource(fallback_synthetic=True).history("RELIANCE", "1d", date(2022, 1, 1), date(2022, 3, 1))
    assert len(bars) > 0
    assert bars[0].source == "nse:synthetic"
