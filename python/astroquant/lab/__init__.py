"""
Autonomous Alpha Discovery Lab (docs/000 §5, docs/007).

An AI research lab that continuously searches for *validated, post-cost* market edges:

    Collect → Generate Hypotheses → Backtest → Validate → Rank → Learn → Repeat

The crucial discipline (docs/007 §4 — "the astrology trap"): every hypothesis the lab tries increments
a **global comparison counter**, and that denominator deflates every p-value and Sharpe. Searching a
huge space of planetary/Gann/technical combinations and reporting the best one *without* this counter
is exactly how a lab fools itself; here it cannot.
"""
from astroquant.lab.hypothesis import HypothesisSpec, generate_hypotheses
from astroquant.lab.orchestrator import Discovery, DiscoveryLab, LabReport
from astroquant.lab.ranking import rank_discoveries

__all__ = [
    "HypothesisSpec", "generate_hypotheses",
    "Discovery", "DiscoveryLab", "LabReport", "rank_discoveries",
]
