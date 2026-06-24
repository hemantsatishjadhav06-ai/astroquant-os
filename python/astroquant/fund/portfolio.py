"""
Paper portfolio + risk report for the Self-Evolving Hedge Fund.

Takes the evolved winner, re-validates it with the **rigorous research engine** (so the deploy
decision is gated by the integrity protocol, not just the evolution fitness), then builds a post-cost
paper portfolio and a risk report.

DEPLOY GATE: this produces a *paper* portfolio only (docs/011 G5). No real orders are ever placed.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np

from astroquant.features.factory import FeatureMatrix
from astroquant.fund.strategy import StrategyGenome
from astroquant.paper.engine import run_paper_trade
from astroquant.research.engine import BASELINE_FAMILIES, run_protocol


@dataclass
class RiskReport:
    strategy_label: str
    total_return: float
    sharpe: float
    deflated_sharpe: float
    max_drawdown: float
    volatility_annual: float
    var_95: float                 # historical 1-day 95% VaR, as a positive loss fraction
    exposure: float               # fraction of days in the market
    n_trades: int
    research_verdict: str         # from the rigorous engine
    incremental_lift: float
    reconciled: bool
    deploy_gate: str = "PAPER ONLY (G5) — no live orders"
    equity_curve: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def build_portfolio(
    fm: FeatureMatrix,
    genome: StrategyGenome,
    *,
    capital: float = 1_000_000.0,
    n_prior_trials: int = 1,
    validate: bool = True,
    k_folds: int = 4,
    n_permutations: int = 12,
) -> RiskReport:
    split = int(len(fm.y) * 0.6)
    pos = genome.fit_positions(fm, split)
    paper = run_paper_trade([], pos, fm.fwd_return[split:], fm.dates[split:],
                            capital=capital, n_prior_trials=n_prior_trials)

    verdict, lift = "not_validated", 0.0
    if validate:
        rep = run_protocol(
            fm, "FUND-BEST",
            baseline_families=BASELINE_FAMILIES,
            augmented_families=tuple(dict.fromkeys(BASELINE_FAMILIES + tuple(genome.families))),
            k_folds=k_folds, n_permutations=n_permutations, n_prior_trials=n_prior_trials,
        )
        verdict, lift = rep.verdict, rep.incremental_lift

    ret = np.array(paper.returns, dtype=float)
    vol_annual = float(ret.std(ddof=1) * math.sqrt(252)) if len(ret) > 1 else 0.0
    var_95 = float(-np.percentile(ret, 5)) if len(ret) else 0.0
    exposure = float(np.mean(np.asarray(pos) != 0)) if len(pos) else 0.0

    return RiskReport(
        strategy_label=genome.label, total_return=paper.total_return, sharpe=paper.sharpe,
        deflated_sharpe=paper.deflated_sharpe, max_drawdown=paper.max_drawdown,
        volatility_annual=round(vol_annual, 4), var_95=round(var_95, 4),
        exposure=round(exposure, 4), n_trades=paper.n_trades,
        research_verdict=verdict, incremental_lift=round(lift, 4), reconciled=paper.reconciled,
        equity_curve=paper.equity_curve,
    )
