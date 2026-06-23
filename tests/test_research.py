"""
Tests for the research engine — the part that must not fool itself (docs/007).

Two complementary directions, both required:
  * On pure noise the engine must report NO EDGE and the shuffle-label guard must NOT fire.
  * On a *planted* genuine signal the engine must DETECT it (augmented beats baseline, guard fires).
A platform that only ever says "no edge" is useless; one that says "edge" on noise is dangerous.
"""
import numpy as np

from astroquant.features.factory import FeatureMatrix
from astroquant.research.engine import run_protocol
from astroquant.research.stats import (
    auc_score,
    benjamini_hochberg,
    deflated_sharpe_ratio,
    norm_cdf,
    norm_ppf,
    sharpe_ratio,
)


# ---------- statistics primitives ----------

def test_auc_perfect_and_reversed():
    y = np.array([0, 0, 1, 1])
    assert auc_score(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert auc_score(y, np.array([0.9, 0.8, 0.2, 0.1])) == 0.0
    assert abs(auc_score(y, np.array([0.5, 0.5, 0.5, 0.5])) - 0.5) < 1e-9


def test_auc_single_class_is_chance():
    assert auc_score(np.array([1, 1, 1]), np.array([0.1, 0.9, 0.5])) == 0.5


def test_norm_ppf_cdf_roundtrip():
    for p in (0.01, 0.25, 0.5, 0.84, 0.99):
        assert abs(norm_cdf(norm_ppf(p)) - p) < 1e-6


def test_benjamini_hochberg_monotone_and_bounded():
    q = benjamini_hochberg([0.001, 0.01, 0.2, 0.5])
    assert np.all(q >= np.array([0.001, 0.01, 0.2, 0.5]) - 1e-9)   # q >= p
    assert np.all(q <= 1.0)


def test_deflated_sharpe_penalises_many_trials():
    rng = np.random.default_rng(0)
    r = rng.normal(0.001, 0.01, 500)
    dsr_1 = deflated_sharpe_ratio(r, n_trials=1)
    dsr_many = deflated_sharpe_ratio(r, n_trials=1000)
    assert 0.0 <= dsr_many <= dsr_1 <= 1.0          # more trials => harder bar => lower DSR


# ---------- the protocol: null vs planted signal ----------

def _fm(X, y, fwd, fam):
    n = len(y)
    names = list(fam.keys())
    return FeatureMatrix(
        dates=[f"2020-01-{(i % 27) + 1:02d}" for i in range(n)],
        feature_names=names, X=X, y=np.asarray(y, int), fwd_return=np.asarray(fwd, float),
        close=np.full(n, 100.0), family_of=fam,
    )


def test_pure_noise_reports_no_edge():
    rng = np.random.default_rng(1)
    n = 400
    X = rng.standard_normal((n, 5))
    y = rng.integers(0, 2, n)
    fwd = rng.normal(0, 0.01, n)
    fam = {"t0": "technical", "t1": "technical", "t2": "market", "a0": "astro", "g0": "gann"}
    rep = run_protocol(_fm(X, y, fwd, fam), k_folds=4, n_permutations=20, n_prior_trials=1)
    assert rep.verdict == "no_edge_found"
    assert rep.shuffle_label_pass is False          # noise must not look like signal


def test_planted_signal_is_detected():
    rng = np.random.default_rng(2)
    n = 500
    noise = rng.standard_normal((n, 3))             # technical/market = noise
    z = rng.standard_normal(n)                      # the astro feature carries the signal
    prob = 1.0 / (1.0 + np.exp(-2.5 * z))
    y = (rng.random(n) < prob).astype(int)
    fwd = np.where(y == 1, 0.01, -0.01) + rng.normal(0, 0.004, n)
    X = np.column_stack([noise, z])
    fam = {"t0": "technical", "t1": "technical", "t2": "market", "astro0": "astro"}
    rep = run_protocol(_fm(X, y, fwd, fam), k_folds=4, n_permutations=20, n_prior_trials=1)
    assert rep.augmented_auc > rep.baseline_auc + 0.05   # astro adds real lift
    assert rep.shuffle_label_pass is True                # genuine signal beats shuffled labels
    assert rep.verdict in ("edge", "conditional_edge")


def test_sharpe_zero_for_constant_returns():
    assert sharpe_ratio(np.zeros(50)) == 0.0
