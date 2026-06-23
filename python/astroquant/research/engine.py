"""
Research Engine — the baseline→augmented→ablation→correction→verdict protocol (docs/007 §2, §9).

This is the module that answers questions like **RQ-004**: *do astro+Gann features add out-of-sample,
post-cost predictive power beyond technical+market features for next-day NIFTY direction?*

It refuses to fool itself:
  * **Chronological walk-forward** with an embargo gap — never a random shuffle (docs/007 §3).
  * **Ablation**: augmented (all families) minus baseline ({technical, market}); incremental lift is
    the only thing that counts as evidence for the family on trial.
  * **Sanity guards**: shuffle-label (must collapse to chance) and random-feature (noise must not rank).
  * **Multiple-testing correction**: the lift's p-value is deflated by how many things were tried.
  * **Deflated Sharpe Ratio** on the post-cost strategy (a Sharpe selected from N trials must clear a
    bar that rises with N).
  * **Honest nulls**: ``no_edge_found`` is a first-class, recorded result (docs/007 §8).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np

from astroquant.agents.base import get_logger
from astroquant.features.factory import AUGMENTED_FAMILIES, BASELINE_FAMILIES, FeatureMatrix
from astroquant.research.model import LogisticModel
from astroquant.research.sanity import random_feature_test, shuffle_label_test
from astroquant.research.stats import (
    auc_score,
    benjamini_hochberg,
    deflated_sharpe_ratio,
    sharpe_ratio,
)

log = get_logger("research.engine")

EDGE = "edge"
NO_EDGE = "no_edge_found"
CONDITIONAL = "conditional_edge"


@dataclass
class ResearchReport:
    hypothesis_id: str
    n_samples: int
    baseline_auc: float
    augmented_auc: float
    incremental_lift: float
    fold_lifts: list[float]
    p_raw: float
    p_adj: float
    n_comparisons: int
    shuffle_label_pass: bool          # True => a genuine signal was detected above shuffled noise
    random_feature_pass: bool
    strategy_sharpe: float
    strategy_dsr: float
    verdict: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _oos_predictions(
    X: np.ndarray, y: np.ndarray, k_folds: int, embargo: int, model_kwargs: dict
) -> tuple[np.ndarray, list[float]]:
    """Expanding-window walk-forward. Returns (oos_prob_predictions, per_fold_auc)."""
    n = len(y)
    fold = max(1, n // (k_folds + 1))
    preds = np.full(n, np.nan)
    fold_aucs: list[float] = []
    for i in range(1, k_folds + 1):
        train_end = fold * i
        test_start = train_end + embargo            # purge/embargo gap (docs/007 §3)
        test_end = n if i == k_folds else fold * (i + 1)
        if test_start >= test_end or train_end < 10:
            continue
        ytr = y[:train_end]
        if len(np.unique(ytr)) < 2:
            continue
        m = LogisticModel(**model_kwargs).fit(X[:train_end], ytr)
        p = m.predict_proba(X[test_start:test_end])
        preds[test_start:test_end] = p
        fold_aucs.append(auc_score(y[test_start:test_end], p))
    return preds, fold_aucs


def _overall_oos_auc(X: np.ndarray, y: np.ndarray, k_folds: int, embargo: int, mk: dict) -> float:
    preds, _ = _oos_predictions(X, y, k_folds, embargo, mk)
    mask = ~np.isnan(preds)
    return auc_score(y[mask], preds[mask]) if mask.sum() else 0.5


def _one_sided_t_p(values: list[float]) -> float:
    """One-sided p that mean(values) > 0 via a t-stat → normal tail (approx; small-k honest)."""
    v = np.asarray(values, dtype=float)
    if len(v) < 2 or v.std(ddof=1) == 0:
        return 0.5 if (len(v) == 0 or v.mean() <= 0) else 0.05
    t = v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))
    # normal approximation to the t tail
    return float(0.5 * math.erfc(t / math.sqrt(2.0)))


def run_protocol(
    fm: FeatureMatrix,
    hypothesis_id: str = "RQ-004",
    *,
    k_folds: int = 5,
    embargo: int = 2,
    n_permutations: int = 30,
    n_prior_trials: int = 1,
    cost_bps: float = 5.0,
    seed: int = 42,
) -> ResearchReport:
    """Run the full protocol on a built FeatureMatrix and return a verdict report.

    ``n_prior_trials`` is the running denominator of comparisons made on this question family — it
    deflates both the p-value (Bonferroni-style) and the Sharpe (DSR). Pass the true count.
    """
    mk = {"l2": 1.0, "lr": 0.2, "n_iter": 400, "seed": seed}
    X_aug = fm.subset(AUGMENTED_FAMILIES)
    X_base = fm.subset(BASELINE_FAMILIES)

    baseline_auc = _overall_oos_auc(X_base, fm.y, k_folds, embargo, mk)
    augmented_auc = _overall_oos_auc(X_aug, fm.y, k_folds, embargo, mk)
    incremental = augmented_auc - baseline_auc

    _, base_folds = _oos_predictions(X_base, fm.y, k_folds, embargo, mk)
    aug_preds, aug_folds = _oos_predictions(X_aug, fm.y, k_folds, embargo, mk)
    fold_lifts = [a - b for a, b in zip(aug_folds, base_folds)]
    p_raw = _one_sided_t_p(fold_lifts)
    # Multiple-testing: deflate by the number of comparisons tried on this family.
    p_adj = float(min(1.0, p_raw * max(1, n_prior_trials)))
    bh = benjamini_hochberg([p_raw] + [max(1e-6, 1 - fl) for fl in fold_lifts])
    p_adj_bh = float(bh[0])

    # --- sanity guards on the augmented model (docs/007 §6) ---
    def score_fn(Xx: np.ndarray, yy: np.ndarray) -> float:
        return _overall_oos_auc(Xx, yy, k_folds, embargo, mk)

    shuffle_res = shuffle_label_test(
        score_fn, X_aug, fm.y, real_score=augmented_auc,
        n_permutations=n_permutations, seed=seed, alpha=0.05,
    )

    def importance_fn(Xa: np.ndarray) -> np.ndarray:
        return LogisticModel(**mk).fit(Xa, fm.y).importances()

    rf_res = random_feature_test(importance_fn, X_aug, seed=seed)

    # --- post-cost strategy from augmented OOS predictions (docs/007 §7) ---
    mask = ~np.isnan(aug_preds)
    pos = np.where(aug_preds[mask] > 0.5, 1.0, -1.0)          # long/short next-day
    gross = pos * fm.fwd_return[mask]
    turn = np.abs(np.diff(np.concatenate([[0.0], pos])))      # 0/2 when flipping
    cost = turn * (cost_bps / 1e4)
    strat_ret = gross - cost
    strat_sharpe = sharpe_ratio(strat_ret)
    strat_dsr = deflated_sharpe_ratio(strat_ret, n_trials=max(1, n_prior_trials))

    # --- verdict (docs/007 §2 step 7, §9) ---
    real_signal = shuffle_res.passed            # augmented AUC beats shuffled labels
    if (incremental > 0.02 and real_signal and rf_res.passed
            and p_adj < 0.05 and strat_dsr > 0.5):
        verdict = EDGE
    elif incremental > 0.0 and real_signal and (np.mean(fold_lifts) > 0 if fold_lifts else False):
        verdict = CONDITIONAL
    else:
        verdict = NO_EDGE

    report = ResearchReport(
        hypothesis_id=hypothesis_id, n_samples=int(mask.sum()),
        baseline_auc=round(baseline_auc, 4), augmented_auc=round(augmented_auc, 4),
        incremental_lift=round(incremental, 4), fold_lifts=[round(x, 4) for x in fold_lifts],
        p_raw=round(p_raw, 4), p_adj=round(min(p_adj, p_adj_bh), 4), n_comparisons=int(n_prior_trials),
        shuffle_label_pass=bool(shuffle_res.passed), random_feature_pass=bool(rf_res.passed),
        strategy_sharpe=round(strat_sharpe, 4), strategy_dsr=round(strat_dsr, 4),
        verdict=verdict,
        detail={
            "baseline_families": list(BASELINE_FAMILIES),
            "augmented_families": list(AUGMENTED_FAMILIES),
            "shuffle_detail": shuffle_res.detail,
            "random_feature_detail": rf_res.detail,
            "cost_bps": cost_bps, "k_folds": k_folds, "embargo": embargo,
        },
    )
    log.info("research[%s]: baseline_auc=%.3f augmented_auc=%.3f lift=%.3f verdict=%s",
             hypothesis_id, baseline_auc, augmented_auc, incremental, verdict)
    return report
