"""Tests for the per-stock deep analysis + analyst narrative (offline: synthetic source)."""
from astroquant.analysis import analyze_stock, generate_narrative, llm_available


def test_analyze_stock_structure():
    r = analyze_stock("NIFTY", source="synthetic", years=4, n_permutations=6)
    for section in ("market", "technical", "gann", "astro", "backtest", "scores"):
        assert getattr(r, section)
    assert r.technical["trend"] in ("Uptrend", "Downtrend", "Sideways")
    assert r.scores["stance"] in ("Constructive", "Neutral", "Cautious")
    assert r.backtest["verdict"] in ("edge", "conditional_edge", "no_edge_found")
    # Gann levels straddle price; astro snapshot present
    assert r.gann["nearest_resistance"] > r.market["last_close"] > r.gann["nearest_support"]
    assert len(r.astro["planets"]) == 9


def test_no_backtest_path():
    r = analyze_stock("NIFTY", source="synthetic", years=3, do_backtest=False)
    assert r.backtest == {}
    assert r.scores["stance"] in ("Constructive", "Neutral", "Cautious")


def test_narrative_is_rich_and_keyless():
    assert llm_available() is None                 # no key in test env → built-in narrative
    r = analyze_stock("NIFTY", source="synthetic", years=4, n_permutations=6)
    md = generate_narrative(r)
    assert "Deep Dive" in md and "Disclaimer" in md
    assert "Technical" in md and "Gann" in md and "Backtest" in md


def test_determinism():
    a = analyze_stock("NIFTY", source="synthetic", years=4, n_permutations=6)
    b = analyze_stock("NIFTY", source="synthetic", years=4, n_permutations=6)
    assert a.scores == b.scores and a.market == b.market
