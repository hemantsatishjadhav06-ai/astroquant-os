"""
Options backtest harness (spec §11) — weekly-expiry cycles, costs included, the metrics that matter.

For each cycle: derive the signal from data **up to that day** (no look-ahead), build the chain, pick a
structure, size it, hold to the weekly expiry, settle at the expiry-day underlying, and net out the
India options cost stack (STT/exchange/GST via ``research/costs.py``). Reports net-of-cost P&L, max
drawdown, win rate, **tail loss (worst 1%)**, and realized-vs-implied capture (was the vol bet right?).

NOTE: per-strike historical IV is not freely available, so v1 derives IV from realized-vol percentile
(documented). The harness is honest about costs and look-ahead — the usual places options backtests lie.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

import numpy as np

from astroquant.agents.base import get_logger
from astroquant.collectors.sources.market_sources import get_source
from astroquant.research.costs import Segment, Side, compute_costs
from astroquant.strategies.options_greeks.chain import build_synthetic_chain
from astroquant.strategies.options_greeks.decision import decide_structure
from astroquant.strategies.options_greeks.engine import _direction_conviction, _vol_and_ivrank
from astroquant.strategies.options_greeks.risk import size_position
from astroquant.strategies.options_greeks.structures import lot_of, structure_from_dict

log = get_logger("options.backtest")


@dataclass
class OptionsBacktest:
    symbol: str
    source: str
    n_trades: int
    net_pnl: float
    total_return: float
    max_drawdown: float
    win_rate: float
    avg_win: float
    avg_loss: float
    tail_loss_1pct: float
    realized_vs_implied_capture: float
    by_regime: dict
    equity_curve: list[float]
    trades: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _intrinsic(legs, S: float) -> float:
    return sum(leg.qty * (max(0.0, S - leg.strike) if leg.opt == "C" else max(0.0, leg.strike - S))
               for leg in legs)


def run_options_backtest(
    symbol: str = "NIFTY", source: str = "synthetic", *, years: int = 6,
    capital: float = 1_000_000.0, risk_pct: float = 0.015, warmup: int = 60,
) -> OptionsBacktest:
    end = date.today()
    start = date(end.year - years, 1, 1)
    kwargs = {"fallback_synthetic": True} if source in ("nse", "bse") else {}
    bars = get_source(source, **kwargs).history(symbol, "1d", start, end)
    closes = np.array([b.close for b in bars], dtype=float)
    dts = [b.ts.date() for b in bars]
    if len(bars) < warmup + 20:
        raise ValueError(f"not enough data for {symbol}")

    trades: list[dict] = []
    equity = [capital]
    cum = 0.0
    i = warmup
    while i < len(bars) - 2:
        d, spot = dts[i], float(closes[i])
        direction, conviction = _direction_conviction(closes[: i + 1])
        base_iv, iv_rank, _ = _vol_and_ivrank(closes[: i + 1])
        chain = build_synthetic_chain(symbol, spot, d, base_iv=base_iv, iv_rank=iv_rank)
        decision = decide_structure(chain, direction, conviction)
        struct = structure_from_dict(decision.structure)
        lots = max(1, size_position(struct, symbol, spot, capital=capital, risk_pct=risk_pct).lots)

        exp_date = date.fromisoformat(chain.expiry)
        j = next((k for k in range(i + 1, len(bars)) if dts[k] >= exp_date), None)
        if j is None:
            break
        exp_spot = float(closes[j])
        lot = lot_of(symbol)
        gross = lot * lots * (_intrinsic(struct.legs, exp_spot) - struct.net_debit)
        turnover = lot * lots * sum(abs(leg.qty) * leg.premium for leg in struct.legs)
        cost = (compute_costs(turnover, Segment.OPTIONS, Side.SELL).total
                + compute_costs(turnover, Segment.OPTIONS, Side.BUY).total)
        pnl = gross - cost
        cum += pnl
        equity.append(round(capital + cum, 2))

        realized = abs(exp_spot / spot - 1.0)
        implied = base_iv * (max(chain.dte, 1) / 365.0) ** 0.5
        right = realized > implied if not struct.net_short_gamma else realized < implied
        trades.append({"date": d.isoformat(), "structure": struct.name, "regime": decision.regime,
                       "lots": lots, "pnl": round(pnl, 0), "cost": round(cost, 0),
                       "realized_move": round(realized, 4), "implied_move": round(implied, 4),
                       "vol_bet_right": bool(right)})
        i = j + 1

    if not trades:
        raise ValueError("no trades generated")
    pnls = np.array([t["pnl"] for t in trades], dtype=float)
    eq = np.array(equity, dtype=float)
    peak = np.maximum.accumulate(eq)
    mdd = float(((eq - peak) / peak).min())
    wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
    by_regime: dict[str, dict] = {}
    for t in trades:
        r = by_regime.setdefault(t["regime"], {"trades": 0, "pnl": 0.0})
        r["trades"] += 1
        r["pnl"] = round(r["pnl"] + t["pnl"], 0)

    res = OptionsBacktest(
        symbol=symbol.upper(), source=source, n_trades=len(trades),
        net_pnl=round(float(pnls.sum()), 0), total_return=round(float(pnls.sum() / capital), 4),
        max_drawdown=round(mdd, 4), win_rate=round(float((pnls > 0).mean()), 4),
        avg_win=round(float(wins.mean()) if len(wins) else 0.0, 0),
        avg_loss=round(float(losses.mean()) if len(losses) else 0.0, 0),
        tail_loss_1pct=round(float(np.percentile(pnls, 1)), 0),
        realized_vs_implied_capture=round(float(np.mean([t["vol_bet_right"] for t in trades])), 4),
        by_regime=by_regime, equity_curve=[round(x, 0) for x in equity],
        trades=trades[-12:],
        meta={"start": start.isoformat(), "end": end.isoformat(), "capital": capital,
              "note": "synthetic-IV chain; costs included; no look-ahead (signal uses data ≤ entry day)"},
    )
    log.info("options backtest[%s]: %d trades, net ₹%.0f, capture %.2f",
             symbol, res.n_trades, res.net_pnl, res.realized_vs_implied_capture)
    return res
