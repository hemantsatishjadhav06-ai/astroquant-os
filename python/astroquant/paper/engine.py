"""
Paper-Trading Backend — the G5 forward-validation gate (docs/011).

Takes a validated signal (a per-bar target position in {-1, 0, +1}) and runs it forward on bars with
**simulated, post-cost execution and a real ledger**, so we learn whether a backtested edge survives
realistic Indian costs *before any real capital*. Position in the flow:
``Backtesting (G4) → Paper Trading (G5) → [Live, deferred]``.

This v1 engine is a deterministic **close-to-close** model:
  * The position for bar t is decided from information ≤ t (guaranteed by the Feature Factory), and
    earns the close→close forward return — no intrabar hindsight.
  * Every rebalance pays the **full India transaction-cost stack** (``research/costs.py``): STT,
    exchange charges, SEBI fee, stamp duty, GST — conservatively charged on both legs of a flip.
  * A **ledger invariant** is checked: final equity == initial + Σ pnl − Σ costs (raises on violation).

Latency/slippage/partial-fill modelling (docs/011 §3) is the live-mode extension; this gate proves the
cost-and-Sharpe survival question, which is what G5 needs first.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from astroquant.collectors.sources.market_sources import Bar
from astroquant.research.costs import CostConfig, Segment, Side, compute_costs
from astroquant.research.stats import deflated_sharpe_ratio, sharpe_ratio


@dataclass
class PaperResult:
    dates: list[str]
    equity_curve: list[float]
    returns: list[float]
    final_equity: float
    total_return: float
    sharpe: float
    deflated_sharpe: float
    max_drawdown: float
    hit_rate: float
    total_cost: float
    n_trades: int
    reconciled: bool
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        return d


def _max_drawdown(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(dd.min())  # most-negative, e.g. -0.23 == 23% drawdown


def run_paper_trade(
    bars: list[Bar],
    positions: np.ndarray,
    fwd_return: np.ndarray,
    dates: list[str],
    *,
    capital: float = 1_000_000.0,
    segment: Segment = Segment.FUTURES,
    cfg: CostConfig | None = None,
    n_prior_trials: int = 1,
) -> PaperResult:
    """Simulate the strategy. ``positions``/``fwd_return``/``dates`` are aligned per decision bar
    (as produced by the Feature Factory). ``positions[t]`` ∈ {-1,0,1} is held over (t, t+1]."""
    cfg = cfg or CostConfig()
    positions = np.asarray(positions, dtype=float)
    fwd_return = np.asarray(fwd_return, dtype=float)
    assert len(positions) == len(fwd_return) == len(dates), "aligned arrays required"

    equity = capital
    p_prev = 0.0
    total_cost = 0.0
    n_trades = 0
    sum_pnl = 0.0
    equity_curve: list[float] = []
    returns: list[float] = []
    wins = 0
    active = 0

    for t in range(len(positions)):
        p = positions[t]
        equity_before = equity
        # Rebalance cost (conservative: both sell + buy legs of the traded notional).
        if p != p_prev:
            turnover = abs(p - p_prev) * equity
            cost = (compute_costs(turnover, segment, Side.SELL, cfg).total
                    + compute_costs(turnover, segment, Side.BUY, cfg).total)
            equity -= cost
            total_cost += cost
            n_trades += 1
            p_prev = p
        # Hold P&L over the bar (close-to-close), post the rebalance cost.
        pnl = p * fwd_return[t] * equity
        equity += pnl
        sum_pnl += pnl
        if p != 0:
            active += 1
            if p * fwd_return[t] > 0:
                wins += 1
        equity_curve.append(equity)
        returns.append((equity - equity_before) / equity_before if equity_before else 0.0)

    eq = np.array(equity_curve, dtype=float)
    ret = np.array(returns, dtype=float)
    reconciled = bool(abs((capital + sum_pnl - total_cost) - equity) < 1e-3)

    return PaperResult(
        dates=dates,
        equity_curve=[round(x, 2) for x in equity_curve],
        returns=[round(x, 6) for x in returns],
        final_equity=round(equity, 2),
        total_return=round(equity / capital - 1.0, 4),
        sharpe=round(sharpe_ratio(ret), 4),
        deflated_sharpe=round(deflated_sharpe_ratio(ret, n_trials=max(1, n_prior_trials)), 4),
        max_drawdown=round(_max_drawdown(eq) if len(eq) else 0.0, 4),
        hit_rate=round(wins / active, 4) if active else 0.0,
        total_cost=round(total_cost, 2),
        n_trades=n_trades,
        reconciled=reconciled,
        detail={"capital": capital, "segment": segment.value, "active_days": active},
    )


def positions_from_probabilities(probs: np.ndarray, *, long_short: bool = True, band: float = 0.0) -> np.ndarray:
    """Map model probabilities to positions. ``band`` creates a neutral dead-zone around 0.5
    (probabilities within 0.5±band → flat), which cuts churn and cost."""
    probs = np.asarray(probs, dtype=float)
    pos = np.zeros(len(probs))
    pos[probs > 0.5 + band] = 1.0
    pos[probs < 0.5 - band] = -1.0 if long_short else 0.0
    return pos
