"""Tests for the paper-trading gate (docs/011): ledger invariants + post-cost realism."""
import numpy as np

from astroquant.paper.engine import positions_from_probabilities, run_paper_trade
from astroquant.research.costs import CostConfig, Segment


def _dates(n):
    return [f"2023-{(i % 12) + 1:02d}-01" for i in range(n)]


def test_ledger_reconciles():
    rng = np.random.default_rng(0)
    n = 200
    pos = rng.choice([-1.0, 0.0, 1.0], n)
    fwd = rng.normal(0, 0.01, n)
    res = run_paper_trade(bars=[], positions=pos, fwd_return=fwd, dates=_dates(n))
    assert res.reconciled is True                 # equity == capital + Σpnl − Σcost
    assert len(res.equity_curve) == n


def test_costs_reduce_return_vs_zero_cost():
    rng = np.random.default_rng(1)
    n = 250
    pos = rng.choice([-1.0, 1.0], n)              # flip often => lots of cost
    fwd = rng.normal(0.0005, 0.01, n)
    with_cost = run_paper_trade([], pos, fwd, _dates(n), segment=Segment.FUTURES)
    zero_cfg = CostConfig(
        stt_futures_sell=0, stamp_futures_buy=0, exch_futures=0, sebi_fee=0,
        gst=0, brokerage_flat=0,
    )
    no_cost = run_paper_trade([], pos, fwd, _dates(n), segment=Segment.FUTURES, cfg=zero_cfg)
    assert with_cost.total_cost > 0
    assert no_cost.total_cost == 0
    assert with_cost.final_equity < no_cost.final_equity


def test_flat_positions_no_trades_no_pnl():
    n = 50
    res = run_paper_trade([], np.zeros(n), np.full(n, 0.02), _dates(n))
    assert res.n_trades == 0
    assert res.total_cost == 0
    assert abs(res.total_return) < 1e-9


def test_positions_from_probabilities_band():
    probs = np.array([0.9, 0.1, 0.51, 0.49, 0.5])
    pos = positions_from_probabilities(probs, long_short=True, band=0.05)
    assert pos[0] == 1.0 and pos[1] == -1.0
    assert pos[2] == 0.0 and pos[3] == 0.0 and pos[4] == 0.0   # inside the dead-zone


def test_determinism():
    rng = np.random.default_rng(3)
    pos = rng.choice([-1.0, 1.0], 100)
    fwd = rng.normal(0, 0.01, 100)
    a = run_paper_trade([], pos, fwd, _dates(100))
    b = run_paper_trade([], pos, fwd, _dates(100))
    assert a.final_equity == b.final_equity and a.sharpe == b.sharpe
