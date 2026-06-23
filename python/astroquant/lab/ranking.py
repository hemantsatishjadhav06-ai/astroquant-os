"""
Ranking + survivorship (docs/007 §2 step 6–7, §4).

Applies a Benjamini–Hochberg FDR correction **across the whole batch** of discoveries (not per-test),
marks which survive the gate, and orders the leaderboard. A discovery "survives" only if it is an
edge/conditional verdict whose batch-corrected q-value < 0.05, with a Deflated Sharpe above 0.5 and
positive incremental lift — i.e. it cleared every honest hurdle simultaneously.
"""
from __future__ import annotations

from astroquant.research.stats import benjamini_hochberg


def rank_discoveries(discoveries: list) -> list:
    """Mutates each discovery's q_value/survived/rank and returns them sorted (best first)."""
    if not discoveries:
        return []
    q = benjamini_hochberg([d.p_raw for d in discoveries])
    for d, qq in zip(discoveries, q):
        d.q_value = round(float(qq), 4)
        d.survived = bool(
            d.verdict in ("edge", "conditional_edge")
            and d.q_value < 0.05
            and d.dsr > 0.5
            and d.incremental_lift > 0.0
        )
    order = sorted(discoveries, key=lambda d: (not d.survived, -d.dsr, -d.incremental_lift))
    for i, d in enumerate(order, 1):
        d.rank = i
    return order
