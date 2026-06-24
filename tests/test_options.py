"""Tests for the Options Greeks Engine (Δ/Θ/Γ) — pricing, structures, gates, sizing, backtest."""
from datetime import date

from astroquant.strategies.options_greeks import generate_options_signal
from astroquant.strategies.options_greeks.backtest import run_options_backtest
from astroquant.strategies.options_greeks.chain import build_synthetic_chain, iv_rank_from_series
from astroquant.strategies.options_greeks.decision import VolRegime, classify_regime, decide_structure
from astroquant.strategies.options_greeks.expiry import is_expiry_day, next_weekly_expiry
from astroquant.strategies.options_greeks.greeks import bs_price, greeks, implied_vol
from astroquant.strategies.options_greeks.risk import size_position
from astroquant.strategies.options_greeks.structures import iron_condor, long_straddle, structure_from_dict


# ---------- Greeks ----------

def test_greeks_atm_and_put_call():
    c = greeks(20000, 20000, 30 / 365, 0.15, "C")
    p = greeks(20000, 20000, 30 / 365, 0.15, "P")
    assert 0.45 < c["delta"] < 0.6 and -0.6 < p["delta"] < -0.4   # ATM ~ ±0.5
    assert c["gamma"] > 0 and c["theta_day"] < 0                   # long option: +Γ, −Θ
    assert abs(c["gamma"] - p["gamma"]) < 1e-6                     # same gamma


def test_implied_vol_roundtrip():
    price = bs_price(20000, 20100, 21 / 365, 0.22, "C")
    assert abs(implied_vol(price, 20000, 20100, 21 / 365, "C") - 0.22) < 1e-3


# ---------- expiry ----------

def test_expiry_weekdays():
    nifty = next_weekly_expiry("NIFTY", date(2026, 6, 24))
    sensex = next_weekly_expiry("SENSEX", date(2026, 6, 24))
    assert nifty.weekday() == 1            # Tuesday
    assert sensex.weekday() == 3           # Thursday
    assert is_expiry_day("NIFTY", nifty)


# ---------- chain + regime ----------

def test_chain_and_regime():
    ch = build_synthetic_chain("NIFTY", 20000, date(2026, 6, 24), base_iv=0.15, iv_rank=0.2)
    assert ch.atm_strike == 20000 and len(ch.quotes) > 10
    assert classify_regime(0.2) == VolRegime.CHEAP
    assert classify_regime(0.8) == VolRegime.RICH
    assert classify_regime(0.5) == VolRegime.NEUTRAL
    assert iv_rank_from_series([0.1, 0.2, 0.3, 0.4], 0.25) == 0.5


# ---------- structures ----------

def test_structure_greek_signs_and_caps():
    ch = build_synthetic_chain("NIFTY", 20000, date(2026, 6, 24), base_iv=0.15)
    straddle = long_straddle(ch)
    condor = iron_condor(ch)
    assert straddle.net_greeks["gamma"] > 0 and not straddle.net_short_gamma   # buyer: long Γ
    assert condor.net_short_gamma and condor.net_greeks["gamma"] < 0           # seller: short Γ
    assert condor.max_loss < 0 and condor.max_loss > -1e9                      # DEFINED (finite) tail
    assert structure_from_dict(condor.to_dict()).name == "iron_condor"


# ---------- decision gates ----------

def test_regime_selects_correct_side():
    cheap = build_synthetic_chain("NIFTY", 20000, date(2026, 6, 24), base_iv=0.12, iv_rank=0.15)
    rich = build_synthetic_chain("NIFTY", 20000, date(2026, 6, 24), base_iv=0.30, iv_rank=0.85)
    assert decide_structure(cheap, "neutral", 0.5).structure["name"] == "long_strangle"   # buy vol
    assert decide_structure(rich, "neutral", 0.5).structure["name"] == "iron_condor"       # sell vol (defined)


def test_gamma_cliff_gate_blocks_short_gamma():
    rich = build_synthetic_chain("NIFTY", 20000, date(2026, 6, 24), base_iv=0.30, iv_rank=0.85)
    d = decide_structure(rich, "neutral", 0.5, final_hour=True)
    assert not d.structure["net_short_gamma"]                 # forced off short-Gamma into the cliff
    assert any("Gamma cliff" in g for g in d.gate_failures)


def test_never_sell_vol_in_cheap():
    # A short-gamma pick can't survive iv_rank < 0.50 (gate 1).
    cheap = build_synthetic_chain("NIFTY", 20000, date(2026, 6, 24), base_iv=0.12, iv_rank=0.2)
    d = decide_structure(cheap, "short", 0.9)
    assert not d.structure["net_short_gamma"]


# ---------- risk sizing ----------

def test_risk_sizing_caps():
    ch = build_synthetic_chain("NIFTY", 20000, date(2026, 6, 24), base_iv=0.15)
    s = size_position(iron_condor(ch), "NIFTY", 20000, capital=1_000_000, risk_pct=0.015)
    assert s.lots >= 0 and s.within_cap
    assert s.worst_case_per_lot > 0


# ---------- engine + backtest ----------

def test_options_signal_and_determinism():
    a = generate_options_signal("NIFTY", source="synthetic")
    b = generate_options_signal("NIFTY", source="synthetic")
    assert a.action == b.action and a.order_intents == b.order_intents
    assert a.regime in ("CHEAP", "NEUTRAL", "RICH")
    assert "delta" in a.position_greeks


def test_options_backtest_metrics():
    bt = run_options_backtest("NIFTY", source="synthetic", years=5)
    assert bt.n_trades > 10
    assert len(bt.equity_curve) == bt.n_trades + 1
    assert 0.0 <= bt.win_rate <= 1.0
    assert 0.0 <= bt.realized_vs_implied_capture <= 1.0
    assert set(bt.by_regime).issubset({"CHEAP", "NEUTRAL", "RICH"})
