"""
Options engine — turns a signal + option chain into risk-sized order intents (spec §5).

    signal (dir + conviction) + chain (IV, IV-rank) → regime → structure → risk sizing → order intents
                                                                       + Greek-based exits + a live trigger

The directional view and the IV regime are derived from the underlying's own price history (trend +
realized-vol percentile) so the engine is self-contained, or you can pass an explicit signal from the
rest of AstroQuant OS. Research/paper only — intents are *not* sent to a broker.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import date

import numpy as np

from astroquant.agents.base import get_logger
from astroquant.collectors.sources.market_sources import get_source
from astroquant.strategies.options_greeks.chain import build_synthetic_chain, get_chain
from astroquant.strategies.options_greeks.decision import decide_structure
from astroquant.strategies.options_greeks.risk import size_position
from astroquant.strategies.options_greeks.structures import lot_of, structure_from_dict

log = get_logger("options.engine")


def _direction_conviction(closes: np.ndarray) -> tuple[str, float]:
    last = float(closes[-1])
    sma20 = float(closes[-20:].mean())
    sma50 = float(closes[-50:].mean()) if len(closes) >= 50 else sma20
    mom = float(last / closes[-21] - 1) if len(closes) > 21 else 0.0
    if last > sma20 > sma50:
        direction = "long"
    elif last < sma20 < sma50:
        direction = "short"
    else:
        direction = "neutral"
    conviction = min(1.0, abs(mom) * 8 + (0.3 if direction != "neutral" else 0.0))
    return direction, round(conviction, 3)


def _vol_and_ivrank(closes: np.ndarray) -> tuple[float, float, float]:
    rets = np.diff(closes) / closes[:-1]
    if len(rets) < 40:
        rv = float(rets.std() * math.sqrt(252)) if len(rets) > 1 else 0.15
        return round(rv * 1.1, 4), 0.5, round(rv, 4)
    rv_series = np.array([rets[i - 20:i].std() * math.sqrt(252) for i in range(20, len(rets) + 1)])
    cur = float(rv_series[-1])
    window = rv_series[-252:] if len(rv_series) >= 252 else rv_series
    iv_rank = float((window <= cur).mean())
    base_iv = cur * 1.1                                    # implied typically rides above realized
    return round(base_iv, 4), round(iv_rank, 4), round(cur, 4)


@dataclass
class OptionsSignal:
    symbol: str
    as_of: str
    spot: float
    direction: str
    conviction: float
    regime: str
    iv_rank: float
    iv_atm: float
    realized_vol: float
    action: str                      # headline: BUY/SELL <structure> × N lots
    trigger: str
    decision: dict
    sizing: dict
    position_greeks: dict
    order_intents: list[dict]
    exits: dict
    chain_source: str
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def generate_options_signal(
    symbol: str = "NIFTY",
    source: str = "nse",
    *,
    capital: float = 1_000_000.0,
    risk_pct: float = 0.015,
    live_chain: bool = False,
    final_hour: bool = False,
    direction: str | None = None,
    conviction: float | None = None,
    years: int = 3,
) -> OptionsSignal:
    end = date.today()
    start = date(end.year - years, 1, 1)
    kwargs = {"fallback_synthetic": True} if source in ("nse", "bse") else {}
    bars = get_source(source, **kwargs).history(symbol, "1d", start, end)
    if len(bars) < 60:
        raise ValueError(f"not enough data for {symbol}")
    closes = np.array([b.close for b in bars], dtype=float)
    spot = float(closes[-1])

    if direction is None or conviction is None:
        direction, conviction = _direction_conviction(closes)
    base_iv, iv_rank, rv = _vol_and_ivrank(closes)

    if live_chain and source in ("nse", "bse"):
        chain = get_chain(symbol, spot, live=True, base_iv=base_iv, iv_rank=iv_rank)
        chain.iv_rank = iv_rank                            # drive regime from realized-vol percentile
    else:
        chain = build_synthetic_chain(symbol, spot, end, base_iv=base_iv, iv_rank=iv_rank)

    decision = decide_structure(chain, direction, conviction, final_hour=final_hour)
    struct = structure_from_dict(decision.structure)
    sizing = size_position(struct, symbol, spot, capital=capital, risk_pct=risk_pct)

    lots = sizing.lots
    seller = struct.net_short_gamma
    side_word = "SELL" if seller else "BUY"
    action = f"{side_word} {struct.name} × {lots} lot(s)" if lots > 0 else f"NO TRADE ({struct.name}: risk cap too small)"

    intents = []
    for leg in struct.legs:
        leg_lots = lots * abs(leg.qty)
        intents.append({
            "action": "BUY" if leg.qty > 0 else "SELL",
            "instrument": f"{symbol.upper()} {chain.expiry} {int(leg.strike)} {'CE' if leg.opt == 'C' else 'PE'}",
            "lots": leg_lots, "lot_size": lot_of(symbol), "est_premium": leg.premium,
        })
    pos_greeks = {k: round(struct.net_greeks[k] * max(lots, 0), 4) for k in struct.net_greeks}

    exits = (
        {"delta_band": "roll/close when net Δ breaches ±0.30 per lot",
         "take_profit": "close at 50–70% of max premium captured (Gamma worst at the end)",
         "kill_switch": "halt new entries + flatten net-short-Gamma on daily-loss breach"}
        if seller else
        {"invalidation": "exit if the signal level / turn-date is broken",
         "theta_stop": "exit if Theta bleed consumes a preset premium fraction without the expected move"}
    )
    trigger = (f"{symbol.upper()} {direction} signal (conviction {conviction:.2f}) in {decision.regime} vol "
               f"→ {'sell decay' if seller else 'buy convexity'}; expiry {chain.expiry} ({chain.dte} DTE)"
               + ("  ⚠ Gamma-cliff window" if final_hour else ""))

    log.info("options[%s]: %s | regime=%s iv_rank=%.2f lots=%d", symbol, action, decision.regime, iv_rank, lots)
    return OptionsSignal(
        symbol=symbol.upper(), as_of=bars[-1].ts.date().isoformat(), spot=round(spot, 2),
        direction=direction, conviction=round(conviction, 3), regime=decision.regime, iv_rank=iv_rank,
        iv_atm=chain.iv_atm, realized_vol=rv, action=action, trigger=trigger,
        decision=decision.to_dict(), sizing=sizing.to_dict(), position_greeks=pos_greeks,
        order_intents=intents, exits=exits, chain_source=chain.source,
        note="research/paper only — order intents are not sent to any broker",
    )
