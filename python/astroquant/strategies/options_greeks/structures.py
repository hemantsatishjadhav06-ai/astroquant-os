"""
Structure library (spec §6) — Greek-profiled, defined-risk option structures as pure functions.

Each builder returns a ``Structure`` with its legs, net debit/credit, **per-lot net Greeks**, and a
**max loss computed on an expiry payoff grid** (so short-vol always ships with a capped tail, spec §9).
Premiums/Greeks come from the live/synthetic chain; strikes off the chain are Black–Scholes priced.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from astroquant.strategies.options_greeks.chain import OptionChain, strike_step
from astroquant.strategies.options_greeks.greeks import bs_price, greeks

LOT_SIZE: dict[str, int] = {"NIFTY": 75, "BANKNIFTY": 35, "FINNIFTY": 65, "SENSEX": 20}


def lot_of(symbol: str) -> int:
    return LOT_SIZE.get(symbol.upper(), 1)


@dataclass
class Leg:
    opt: str            # 'C' | 'P'
    strike: float
    qty: int            # signed lots: + long, - short
    premium: float      # per-unit entry premium


@dataclass
class Structure:
    name: str
    legs: list[Leg]
    net_debit: float            # per-unit; + = debit paid, − = credit received
    net_greeks: dict            # per-lot position Greeks (delta/gamma/theta_day/vega_pt)
    max_loss: float             # rupees, per 1 lot of the structure (capped)
    max_profit: float           # rupees, per 1 lot (may be capped)
    net_short_gamma: bool
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def structure_from_dict(d: dict) -> Structure:
    """Rebuild a Structure (with Leg objects) from its serialized dict."""
    legs = [Leg(**leg) for leg in d["legs"]]
    return Structure(
        name=d["name"], legs=legs, net_debit=d["net_debit"], net_greeks=d["net_greeks"],
        max_loss=d["max_loss"], max_profit=d["max_profit"],
        net_short_gamma=d["net_short_gamma"], note=d.get("note", ""),
    )


def _quote(chain: OptionChain, strike: float, opt: str, *, r: float = 0.065) -> tuple[float, dict]:
    q = chain.get(strike, opt)
    t = max(chain.dte, 1) / 365.0
    if q is not None:
        return q.price, {"delta": q.delta, "gamma": q.gamma, "theta_day": q.theta_day, "vega_pt": q.vega_pt}
    g = greeks(chain.spot, strike, t, chain.iv_atm or 0.15, opt, r)
    return g["price"], {k: g[k] for k in ("delta", "gamma", "theta_day", "vega_pt")}


def _assemble(name: str, chain: OptionChain, specs: list[tuple[str, float, int]], note: str = "") -> Structure:
    lot = lot_of(chain.symbol)
    legs: list[Leg] = []
    g_tot = {"delta": 0.0, "gamma": 0.0, "theta_day": 0.0, "vega_pt": 0.0}
    net_debit = 0.0
    for opt, strike, qty in specs:
        prem, g = _quote(chain, strike, opt)
        legs.append(Leg(opt, strike, qty, round(prem, 2)))
        net_debit += qty * prem
        for k in g_tot:
            g_tot[k] += qty * g[k] * lot
    # expiry payoff grid → capped max loss / profit
    lo, hi = chain.spot * 0.7, chain.spot * 1.3
    grid = [lo + (hi - lo) * i / 80 for i in range(81)]
    pnls = []
    for S in grid:
        intrinsic = sum(leg.qty * (max(0.0, S - leg.strike) if leg.opt == "C" else max(0.0, leg.strike - S))
                        for leg in legs)
        pnls.append(lot * (intrinsic - net_debit))
    return Structure(
        name=name, legs=legs, net_debit=round(net_debit, 2),
        net_greeks={k: round(v, 4) for k, v in g_tot.items()},
        max_loss=round(min(pnls), 0), max_profit=round(max(pnls), 0),
        net_short_gamma=g_tot["gamma"] < 0, note=note,
    )


def long_straddle(chain: OptionChain) -> Structure:
    k = chain.atm_strike
    return _assemble("long_straddle", chain, [("C", k, 1), ("P", k, 1)],
                     "long Gamma / short Theta — profits when realized > implied (big move either way)")


def long_strangle(chain: OptionChain, width: int = 2) -> Structure:
    step = strike_step(chain.symbol, chain.spot)
    return _assemble("long_strangle", chain,
                     [("C", chain.atm_strike + width * step, 1), ("P", chain.atm_strike - width * step, 1)],
                     "long Gamma — cheaper convexity than a straddle; needs a larger move")


def atm_debit_spread(chain: OptionChain, direction: str) -> Structure:
    step = strike_step(chain.symbol, chain.spot)
    k = chain.atm_strike
    if direction == "long":
        return _assemble("atm_call_debit_spread", chain, [("C", k, 1), ("C", k + 2 * step, -1)],
                         "directional long Gamma, defined risk — move up in signal direction")
    return _assemble("atm_put_debit_spread", chain, [("P", k, 1), ("P", k - 2 * step, -1)],
                     "directional long Gamma, defined risk — move down in signal direction")


def iron_condor(chain: OptionChain, body: int = 3, wing: int = 5) -> Structure:
    step = strike_step(chain.symbol, chain.spot)
    k = chain.atm_strike
    return _assemble("iron_condor", chain, [
        ("C", k + body * step, -1), ("C", k + wing * step, 1),
        ("P", k - body * step, -1), ("P", k - wing * step, 1)],
        "short Gamma / long Theta, DEFINED tail — range-bound + falling IV (high-IV regime)")


def broken_wing(chain: OptionChain, direction: str, body: int = 2, near: int = 4, far: int = 7) -> Structure:
    step = strike_step(chain.symbol, chain.spot)
    k = chain.atm_strike
    if direction == "long":  # skew risk to the downside, lean bullish
        return _assemble("broken_wing_call", chain, [
            ("P", k - body * step, -1), ("P", k - near * step, 1),
            ("C", k + body * step, -1), ("C", k + far * step, 1)],
            "short Gamma + bullish lean, defined tail — high IV with directional view")
    return _assemble("broken_wing_put", chain, [
        ("C", k + body * step, -1), ("C", k + near * step, 1),
        ("P", k - body * step, -1), ("P", k - far * step, 1)],
        "short Gamma + bearish lean, defined tail — high IV with directional view")


def calendar(chain: OptionChain, r: float = 0.065) -> Structure:
    """Sell near-expiry ATM, buy next-expiry ATM (the long-Theta, long-Vega, Gamma-safe income play)."""
    k = chain.atm_strike
    lot = lot_of(chain.symbol)
    t_near = max(chain.dte, 1) / 365.0
    t_far = max(chain.dte + 7, 8) / 365.0
    iv = chain.iv_atm or 0.15
    near_p, far_p = bs_price(chain.spot, k, t_near, iv, "C", r), bs_price(chain.spot, k, t_far, iv, "C", r)
    gn = greeks(chain.spot, k, t_near, iv, "C", r)
    gf = greeks(chain.spot, k, t_far, iv, "C", r)
    net = {kk: round((gf[kk] - gn[kk]) * lot, 4) for kk in ("delta", "gamma", "theta_day", "vega_pt")}
    debit = far_p - near_p
    return Structure(
        name="calendar", legs=[Leg("C", k, 1, round(far_p, 2)), Leg("C", k, -1, round(near_p, 2))],
        net_debit=round(debit, 2), net_greeks=net, max_loss=round(-debit * lot, 0),
        max_profit=round(near_p * lot, 0), net_short_gamma=net["gamma"] < 0,
        note="long Theta + long Vega, ~Gamma-neutral — preferred income in a low-IV regime")


def short_strangle(chain: OptionChain, width: int = 4) -> Structure:
    step = strike_step(chain.symbol, chain.spot)
    s = _assemble("short_strangle", chain,
                  [("C", chain.atm_strike + width * step, -1), ("P", chain.atm_strike - width * step, -1)],
                  "short Gamma / long Theta — UNCAPPED tail; not a v1 default (use a condor)")
    s.max_loss = round(-lot_of(chain.symbol) * chain.spot * 0.05, 0)  # bound by a 5% gap for display
    return s
