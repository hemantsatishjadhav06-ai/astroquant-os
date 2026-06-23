"""
Research integrity guards (docs/007 §6). These are the automated 'are we fooling ourselves?'
checks that must run continuously. Implemented model-agnostic via a scoring callable.

- shuffle_label_test: permute labels; a correct pipeline must collapse to ~chance.
- random_feature_test: inject noise feature; it must NOT rank as important.

These are the platform's first line of defense against leakage and spurious 'astro edge'.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class SanityResult:
    name: str
    passed: bool
    detail: str
    statistic: float


def shuffle_label_test(
    score_fn: Callable[[np.ndarray, np.ndarray], float],
    X: np.ndarray,
    y: np.ndarray,
    *,
    real_score: float,
    n_permutations: int = 50,
    seed: int = 42,
    alpha: float = 0.05,
) -> SanityResult:
    """
    Permutation test: train/score on shuffled labels n times. If the real score is not
    clearly above the shuffled distribution (empirical p >= alpha), the 'edge' is likely
    leakage/noise — FAIL (which is the safe outcome to surface).
    """
    rng = np.random.default_rng(seed)
    shuffled_scores = np.empty(n_permutations)
    for i in range(n_permutations):
        y_perm = rng.permutation(y)
        shuffled_scores[i] = score_fn(X, y_perm)
    # empirical p-value: fraction of shuffled runs that match/beat the real score
    p = float((np.sum(shuffled_scores >= real_score) + 1) / (n_permutations + 1))
    passed = bool(p < alpha)
    return SanityResult(
        name="shuffle_label_test", passed=passed,
        detail=(f"real={real_score:.4f}, shuffled_mean={shuffled_scores.mean():.4f}, "
                f"empirical_p={p:.4f}, alpha={alpha}"),
        statistic=p,
    )


def random_feature_test(
    importance_fn: Callable[[np.ndarray], np.ndarray],
    X: np.ndarray,
    *,
    seed: int = 42,
    percentile_cap: float = 50.0,
) -> SanityResult:
    """
    Append a pure-noise feature and compute importances. The noise feature's importance
    must fall below the given percentile of real-feature importances, else the importance
    method / CV is broken — FAIL.
    """
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((X.shape[0], 1))
    X_aug = np.hstack([X, noise])
    imps = importance_fn(X_aug)
    noise_imp = imps[-1]
    real_imps = imps[:-1]
    cap = float(np.percentile(real_imps, percentile_cap))
    passed = bool(noise_imp <= cap)
    return SanityResult(
        name="random_feature_test", passed=passed,
        detail=f"noise_importance={noise_imp:.4f}, real_p{int(percentile_cap)}={cap:.4f}",
        statistic=float(noise_imp),
    )
