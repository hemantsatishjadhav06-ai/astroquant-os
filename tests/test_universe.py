"""Tests for the stock universe database."""
from astroquant.db.session import get_engine, init_db
from astroquant.universe import (
    get_stock,
    list_sectors,
    load_universe,
    persist_universe,
)


def test_universe_loaded():
    u = load_universe()
    syms = {m.symbol for m in u}
    assert {"RELIANCE", "TCS", "HDFCBANK", "INFY", "NIFTY"} <= syms
    assert len(u) >= 50


def test_yahoo_mapping():
    assert get_stock("RELIANCE").yahoo == "RELIANCE.NS"
    assert get_stock("NIFTY").yahoo == "NIFTY"            # index keeps its alias
    assert get_stock("TCS").sector == "IT"


def test_unknown_symbol_is_handled():
    m = get_stock("SOMETHINGNEW")
    assert m.symbol == "SOMETHINGNEW" and m.yahoo == "SOMETHINGNEW.NS"


def test_sectors_grouping():
    sec = list_sectors()
    assert "Banking" in sec and "IT" in sec
    assert "HDFCBANK" in sec["Banking"]


def test_persist_universe_to_sqlite():
    eng = get_engine("sqlite:///:memory:")
    init_db(eng)
    n = persist_universe(eng)
    assert n == len(load_universe())
