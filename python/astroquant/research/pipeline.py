"""
End-to-end research pipeline (docs/007 §9, docs/013): collect → features → research → paper-trade.

This is the platform's vertical slice executed as one reproducible call — the same path the CLI
``pipeline`` command and ``scripts/run_research.py`` use. It answers a registered hypothesis
(default RQ-004) and forward-validates the resulting strategy through the paper-trading gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from astroquant.agents.base import get_logger
from astroquant.collectors.sources.market_sources import Bar, get_source
from astroquant.features.factory import AUGMENTED_FAMILIES, FeatureFactory, FeatureMatrix
from astroquant.paper.engine import PaperResult, positions_from_probabilities, run_paper_trade
from astroquant.research.engine import ResearchReport, run_protocol
from astroquant.research.model import LogisticModel

log = get_logger("research.pipeline")


@dataclass
class PipelineOutput:
    meta: dict
    bars: list[Bar]
    fm: FeatureMatrix
    report: ResearchReport
    paper: PaperResult


def run_full_pipeline(
    symbol: str = "NIFTY",
    start: date = date(2014, 1, 1),
    end: date = date(2023, 12, 31),
    *,
    source: str = "synthetic",
    seed: int = 7,
    hypothesis_id: str = "RQ-004",
    n_prior_trials: int = 1,
    capital: float = 1_000_000.0,
    k_folds: int = 5,
    n_permutations: int = 30,
) -> PipelineOutput:
    src = get_source(source, seed=seed) if source == "synthetic" else get_source(source)
    bars = src.history(symbol, "1d", start, end)
    log.info("pipeline: %d bars for %s (%s..%s) from %s", len(bars), symbol, start, end, source)

    ff = FeatureFactory(warmup=25, use_astro=True, use_gann=True)
    fm = ff.build(bars)

    report = run_protocol(
        fm, hypothesis_id, k_folds=k_folds, n_permutations=n_permutations,
        n_prior_trials=n_prior_trials, seed=42,
    )

    # Forward-validate: fit the augmented model on the first 60% (train), trade the held-out 40%.
    split = int(len(fm.y) * 0.6)
    X_aug = fm.subset(AUGMENTED_FAMILIES)
    model = LogisticModel(l2=1.0, lr=0.2, n_iter=400).fit(X_aug[:split], fm.y[:split])
    probs = model.predict_proba(X_aug[split:])
    positions = positions_from_probabilities(probs, long_short=True, band=0.02)
    paper = run_paper_trade(
        bars, positions, fm.fwd_return[split:], fm.dates[split:],
        capital=capital, n_prior_trials=n_prior_trials,
    )

    meta = {
        "symbol": symbol, "source": source, "start": start.isoformat(), "end": end.isoformat(),
        "n_bars": len(bars), "n_samples": int(len(fm.y)), "n_features": int(fm.X.shape[1]),
        "oos_trade_days": int(len(positions)), "seed": seed,
    }
    return PipelineOutput(meta=meta, bars=bars, fm=fm, report=report, paper=paper)
