"""Tests for the full NSE + BSE + MCX instrument universe."""
from astroquant.db.session import get_engine, init_db
from astroquant.universe import (
    get_stock,
    list_sectors,
    load_universe,
    persist_universe,
    resolve_yahoo,
    search,
    universe_stats,
)


def test_universe_is_large_and_multi_exchange():
    stats = universe_stats()
    assert stats["total"] > 5000                       # full masters, not the curated 50
    bx = stats["by_exchange"]
    assert bx.get("NSE", 0) > 1500 and bx.get("BSE", 0) > 2000 and bx.get("MCX", 0) >= 10


def test_known_symbols_present():
    u = {m.symbol for m in load_universe()}
    assert {"RELIANCE", "TCS", "INFY", "NIFTY", "GOLD"} <= u


def test_yahoo_resolution_per_exchange():
    assert resolve_yahoo("RELIANCE", "NSE") == "RELIANCE.NS"
    assert resolve_yahoo("NIFTY") == "^NSEI"
    assert resolve_yahoo("GOLD", "MCX") == "GC=F"        # MCX → Yahoo commodity proxy
    bse = get_stock("RELIANCE", "BSE")
    assert bse.exchange == "BSE" and bse.yahoo_ticker.endswith(".BO")   # numeric scrip code


def test_nifty50_sector_overlay():
    assert get_stock("TCS").sector == "IT"
    sec = list_sectors()
    assert "Banking" in sec and "IT" in sec


def test_search():
    res = search("RELI", limit=10)
    assert any(m.symbol == "RELIANCE" for m in res)
    nse_only = search("", exchange="MCX", limit=5)
    assert nse_only and all(m.exchange == "MCX" for m in nse_only)


def test_persist_universe_capped():
    eng = get_engine("sqlite:///:memory:")
    init_db(eng)
    assert persist_universe(eng, limit=25) == 25
