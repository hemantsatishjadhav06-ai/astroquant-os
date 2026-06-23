"""Tests for the Autonomous Alpha Discovery Lab (hypothesis gen, orchestrator loop, ranking)."""
from datetime import date

from astroquant.features.factory import BASELINE_FAMILIES
from astroquant.lab import DiscoveryLab, generate_hypotheses, rank_discoveries
from astroquant.lab.orchestrator import Discovery


def test_generate_hypotheses_space():
    specs = generate_hypotheses(["NIFTY", "BANKNIFTY"], source="nse")
    # 2 symbols × 3 trial sets × 2 bands = 12
    assert len(specs) == 12
    s = specs[0]
    assert s.exchange == "NSE"
    # augmented = baseline ∪ trial, de-duplicated and order-preserving
    assert set(s.augmented_families) == set(BASELINE_FAMILIES) | set(s.trial_families)
    assert all(h.id.startswith("H-") for h in specs)


def test_lab_runs_and_counts_denominator():
    lab = DiscoveryLab(["NIFTY"], source="synthetic", start=date(2019, 1, 1),
                       end=date(2022, 12, 31), persist=False, k_folds=3, n_permutations=6)
    rep = lab.run(rounds=1, learn=False)
    # 1 symbol × 3 trial sets × 2 bands = 6 hypotheses => denominator 6
    assert rep.total_tested == 6
    assert len(rep.all_discoveries) == 6
    assert len(rep.leaderboard) == 6
    # On a random-walk synthetic series, nothing should survive the corrected gate.
    assert rep.n_survivors == 0
    # every discovery carries its cumulative comparison count
    assert max(d.n_comparisons for d in rep.all_discoveries) == 6


def test_lab_is_deterministic():
    def run():
        return DiscoveryLab(["NIFTY"], source="synthetic", start=date(2019, 1, 1),
                            end=date(2021, 12, 31), persist=False, k_folds=3, n_permutations=5
                            ).run(rounds=1, learn=False)
    a, b = run(), run()
    assert [d.incremental_lift for d in a.leaderboard] == [d.incremental_lift for d in b.leaderboard]


def _disc(hid, verdict, lift, p, dsr):
    return Discovery(hypothesis_id=hid, symbol="NIFTY", source="synthetic", trial_families=["astro"],
                     statement="", verdict=verdict, baseline_auc=0.5, augmented_auc=0.5 + lift,
                     incremental_lift=lift, p_raw=p, p_adj=p, dsr=dsr, sharpe=1.0,
                     max_drawdown=-0.1, total_return=0.2, n_comparisons=1)


def test_ranking_marks_survivors():
    discs = [
        _disc("H-1", "edge", 0.05, 0.001, 0.8),        # should survive
        _disc("H-2", "no_edge_found", 0.00, 0.9, 0.1),  # should not
        _disc("H-3", "conditional_edge", 0.03, 0.30, 0.6),  # q too high after BH
    ]
    ranked = rank_discoveries(discs)
    by = {d.hypothesis_id: d for d in ranked}
    assert by["H-1"].survived is True
    assert by["H-2"].survived is False
    assert ranked[0].hypothesis_id == "H-1"           # survivor sorts first
    assert ranked[0].rank == 1
