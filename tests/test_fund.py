"""Tests for Idea 3 — the Self-Evolving Hedge Fund (evolution + gated paper portfolio)."""
from datetime import date

import pytest

from astroquant.collectors.sources.market_sources import get_source
from astroquant.features.factory import FeatureFactory
from astroquant.fund import build_portfolio, evolve_strategies, run_fund
from astroquant.fund.strategy import StrategyGenome


@pytest.fixture(scope="module")
def fm():
    bars = get_source("synthetic", seed=7).history("NIFTY", "1d", date(2018, 1, 1), date(2021, 12, 31))
    return FeatureFactory(warmup=25, use_astro=True, use_gann=True).build(bars)


def test_strategy_decodes_positions(fm):
    g = StrategyGenome(("technical", "gann"), prob_band=0.02, l2=1.0)
    split = int(len(fm.y) * 0.6)
    pos = g.fit_positions(fm, split)
    assert len(pos) == len(fm.y) - split
    assert set(pos.tolist()) <= {-1.0, 0.0, 1.0}


def test_evolution_runs_and_is_deterministic(fm):
    a = evolve_strategies(fm, generations=3, pop_size=6, seed=1)
    b = evolve_strategies(fm, generations=3, pop_size=6, seed=1)
    assert a.n_evaluated > 0
    assert len(a.history) == 3
    assert a.best_label == b.best_label and a.best_fitness == b.best_fitness   # deterministic


def test_portfolio_is_paper_gated_and_reconciled(fm):
    g = StrategyGenome(("technical", "market"), prob_band=0.02, l2=1.0)
    r = build_portfolio(fm, g, validate=False)
    assert r.reconciled is True
    assert r.deploy_gate.startswith("PAPER ONLY")        # never live
    assert len(r.equity_curve) > 0
    assert r.exposure >= 0.0


def test_portfolio_validation_gate(fm):
    g = StrategyGenome(("astro", "gann"), prob_band=0.02, l2=1.0)
    r = build_portfolio(fm, g, validate=True, n_permutations=6, k_folds=3)
    # The rigorous engine gates deploy; on synthetic noise it must not certify an edge.
    assert r.research_verdict in ("edge", "conditional_edge", "no_edge_found")
    assert r.research_verdict == "no_edge_found"


def test_run_fund_end_to_end():
    res = run_fund("NIFTY", source="synthetic", start=date(2018, 1, 1), end=date(2021, 12, 31),
                   generations=2, pop_size=6, validate=False)
    assert res.evolution.n_evaluated > 0
    assert res.risk.deploy_gate.startswith("PAPER ONLY")
