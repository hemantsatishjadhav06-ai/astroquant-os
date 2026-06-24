"""
Strategy representation for the Self-Evolving Hedge Fund.

A ``StrategyGenome`` is a compact, mutable-by-evolution description of a trading rule:
which feature families it may use, its decision threshold (neutral band), and model regularisation.
It decodes deterministically into next-day positions via the shared LogisticModel + paper sizing.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from astroquant.features.factory import FeatureMatrix
from astroquant.paper.engine import positions_from_probabilities
from astroquant.research.model import LogisticModel

# The gene pool of feature families a strategy may switch on.
GENE_FAMILIES: tuple[str, ...] = ("technical", "market", "astro", "gann")


@dataclass(frozen=True)
class StrategyGenome:
    families: tuple[str, ...]
    prob_band: float = 0.02
    l2: float = 1.0

    def fingerprint(self) -> str:
        raw = f"{sorted(self.families)}|{self.prob_band:.3f}|{self.l2:.3f}"
        return hashlib.sha256(raw.encode()).hexdigest()[:10]

    @property
    def label(self) -> str:
        return "+".join(self.families)

    def fit_positions(self, fm: FeatureMatrix, split: int) -> np.ndarray:
        """Train on [:split], return next-day positions for the held-out [split:] slice."""
        fams = self.families or ("technical",)
        X = fm.subset(fams)
        model = LogisticModel(l2=self.l2, lr=0.2, n_iter=400).fit(X[:split], fm.y[:split])
        probs = model.predict_proba(X[split:])
        return positions_from_probabilities(probs, long_short=True, band=self.prob_band)
