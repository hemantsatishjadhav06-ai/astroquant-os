"""
Self-Evolving Hedge Fund (Idea 3) — AI creates, backtests, improves, and (paper-)deploys strategies.

    create strategy → backtest → improve (evolve) → paper-trade → [live: DEFERRED, gated]

An evolutionary search over StrategyGenomes (which feature families, decision band, regularisation).
Fitness is the **post-cost Deflated Sharpe Ratio**, deflated by the number of strategies tried — so
the search cannot win by trying thousands of variants (docs/007 §4). The winner is then re-validated by
the rigorous research engine before a paper portfolio + risk report is produced.

SAFETY: "deploy" here means promote to **paper trading only** (the G5 gate, docs/011). This module
never places real orders.
"""
from astroquant.fund.evolve import EvolutionResult, evolve_strategies
from astroquant.fund.portfolio import RiskReport, build_portfolio
from astroquant.fund.run import FundResult, run_fund
from astroquant.fund.strategy import StrategyGenome

__all__ = [
    "StrategyGenome", "evolve_strategies", "EvolutionResult",
    "build_portfolio", "RiskReport", "run_fund", "FundResult",
]
