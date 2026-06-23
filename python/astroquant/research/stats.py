"""
Self-contained statistics for the research engine (docs/007 §4) — no scipy/sklearn dependency,
so the integrity controls run anywhere numpy runs.

Implements the multiple-testing machinery that stops the platform fooling itself:
  * AUC (rank-based, ties handled)
  * Benjamini–Hochberg FDR adjustment
  * Probabilistic & Deflated Sharpe Ratio (Bailey & López de Prado)
"""
from __future__ import annotations

import math

import numpy as np

GAMMA = 0.5772156649015329  # Euler–Mascheroni


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation, |err| < 1.15e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("norm_ppf domain is (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def auc_score(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Area under ROC via the Mann–Whitney U statistic (rank-based, tie-aware).

    Returns 0.5 for a degenerate single-class label vector (AUC undefined → no skill)."""
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    n_pos = int((y_true == 1).sum())
    n_neg = int((y_true == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ranks for ties
    s_sorted = scores[order]
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        if j > i:
            avg = (ranks[order[i]] + ranks[order[j]]) / 2.0
            for k in range(i, j + 1):
                ranks[order[k]] = avg
        i = j + 1
    sum_pos = ranks[y_true == 1].sum()
    auc = (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def benjamini_hochberg(pvalues: list[float] | np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Return BH-adjusted p-values (q-values). Controls FDR across a family of tests (docs/007 §4)."""
    p = np.asarray(pvalues, dtype=float)
    n = len(p)
    if n == 0:
        return p
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / (np.arange(1, n + 1))
    # enforce monotonicity from the largest q downward
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(adj, 0, 1)
    return out


def sharpe_ratio(returns: np.ndarray, periods_per_year: int = 252) -> float:
    r = np.asarray(returns, dtype=float)
    if r.std(ddof=1) == 0 or len(r) < 2:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(periods_per_year))


def probabilistic_sharpe_ratio(returns: np.ndarray, sr_benchmark: float = 0.0) -> float:
    """PSR: probability the true (non-annualised) Sharpe exceeds ``sr_benchmark`` (Bailey & LdP)."""
    r = np.asarray(returns, dtype=float)
    n = len(r)
    if n < 3 or r.std(ddof=1) == 0:
        return 0.0
    sr = r.mean() / r.std(ddof=1)            # per-period Sharpe
    skew = float(((r - r.mean()) ** 3).mean() / r.std() ** 3)
    kurt = float(((r - r.mean()) ** 4).mean() / r.std() ** 4)
    denom = math.sqrt(1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2)
    if denom == 0:
        return 0.0
    return norm_cdf((sr - sr_benchmark) * math.sqrt(n - 1) / denom)


def deflated_sharpe_ratio(returns: np.ndarray, n_trials: int, var_trials: float | None = None) -> float:
    """
    Deflated Sharpe Ratio (Bailey & López de Prado 2014): the PSR evaluated against the
    *expected maximum* Sharpe attainable by chance after ``n_trials`` independent trials.

    A strategy selected from many trials must clear a bar that rises with N — this encodes
    docs/007 §4's rule that "the best of 500 planetary signals is probably noise".
    """
    r = np.asarray(returns, dtype=float)
    n = len(r)
    if n < 3 or r.std(ddof=1) == 0 or n_trials < 1:
        return 0.0
    sr = r.mean() / r.std(ddof=1)
    # Variance of the trial Sharpe estimates; default to the sampling variance ~1/(n-1).
    v = var_trials if var_trials is not None else 1.0 / (n - 1)
    if n_trials == 1:
        sr0 = 0.0
    else:
        z1 = norm_ppf(1 - 1.0 / n_trials)
        z2 = norm_ppf(1 - 1.0 / (n_trials * math.e))
        sr0 = math.sqrt(v) * ((1 - GAMMA) * z1 + GAMMA * z2)
    return probabilistic_sharpe_ratio(r, sr_benchmark=sr0)
