"""
Options Greeks Engine (Δ / Θ / Γ) — a volatility-and-Greeks decision layer (spec 2026-06-24).

Turns AstroQuant OS directional/timing signals into structured, risk-bounded options positions on
Indian index & stock options. Encodes the one rule that governs options P&L: **you cannot be long
Gamma and long Theta at the same time** — every trade is an explicit bet on realized vs. implied
volatility, with Delta carrying the directional view.

    signal (dir + conviction) + option chain (IV, IV-rank) → vol regime → structure → risk-sized intents

Indian index options are European / cash-settled, so Black–Scholes (European) pricing is used.
Research/paper only — no live execution. See module docstrings and the feature spec for details.
"""
from astroquant.strategies.options_greeks.decision import VolRegime, decide_structure
from astroquant.strategies.options_greeks.engine import OptionsSignal, generate_options_signal
from astroquant.strategies.options_greeks.greeks import bs_price, greeks, implied_vol

__all__ = [
    "bs_price", "greeks", "implied_vol",
    "VolRegime", "decide_structure",
    "OptionsSignal", "generate_options_signal",
]
