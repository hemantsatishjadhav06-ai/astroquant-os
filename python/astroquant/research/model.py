"""
A small, deterministic, dependency-light classifier for the research engine (docs/009).

L2-regularised logistic regression trained by gradient descent on standardised features. We keep
the model deliberately simple and transparent: the platform's job is to measure whether *features*
add edge, not to win a Kaggle contest with a black box. Standardisation statistics are fit on the
TRAIN slice only and applied to TEST — no leakage across the split.
"""
from __future__ import annotations

import numpy as np


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


class LogisticModel:
    def __init__(self, l2: float = 1.0, lr: float = 0.1, n_iter: int = 400, seed: int = 42) -> None:
        self.l2 = l2
        self.lr = lr
        self.n_iter = n_iter
        self.seed = seed
        self.w: np.ndarray | None = None
        self.b: float = 0.0
        self.mu_: np.ndarray | None = None
        self.sd_: np.ndarray | None = None

    def _standardize_fit(self, X: np.ndarray) -> np.ndarray:
        self.mu_ = X.mean(axis=0)
        self.sd_ = X.std(axis=0) + 1e-9
        return (X - self.mu_) / self.sd_

    def _standardize(self, X: np.ndarray) -> np.ndarray:
        assert self.mu_ is not None and self.sd_ is not None
        return (X - self.mu_) / self.sd_

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticModel":
        Xs = self._standardize_fit(np.asarray(X, dtype=float))
        y = np.asarray(y, dtype=float)
        n, d = Xs.shape
        self.w = np.zeros(d)
        self.b = 0.0
        for _ in range(self.n_iter):
            p = sigmoid(Xs @ self.w + self.b)
            err = p - y
            grad_w = Xs.T @ err / n + self.l2 * self.w / n
            grad_b = float(err.mean())
            self.w -= self.lr * grad_w
            self.b -= self.lr * grad_b
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        assert self.w is not None
        return sigmoid(self._standardize(np.asarray(X, dtype=float)) @ self.w + self.b)

    def importances(self) -> np.ndarray:
        """|standardised coefficient| as a transparent importance proxy."""
        assert self.w is not None
        return np.abs(self.w)
