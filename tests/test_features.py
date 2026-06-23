"""Tests for Agent 6 — the Feature Factory. Focus: family tags + NO LOOK-AHEAD (docs/007 §3, §6)."""
from datetime import date

import numpy as np

from astroquant.collectors.sources.market_sources import get_source
from astroquant.features.factory import (
    AUGMENTED_FAMILIES,
    BASELINE_FAMILIES,
    FeatureFactory,
    assert_no_lookahead,
)


def _bars(n_years: int = 2):
    src = get_source("synthetic", seed=7)
    return src.history("NIFTY", "1d", date(2022, 1, 1), date(2022 + n_years, 1, 1))


def test_family_tags_present_and_split():
    fm = FeatureFactory(warmup=25, use_astro=True, use_gann=True).build(_bars())
    fams = set(fm.family_of.values())
    assert {"technical", "market", "astro", "gann"} <= fams
    base_cols = fm.family_columns(BASELINE_FAMILIES)
    aug_cols = fm.family_columns(AUGMENTED_FAMILIES)
    assert len(base_cols) < len(aug_cols)            # augmented strictly adds astro+gann
    assert len(aug_cols) == fm.X.shape[1]


def test_no_lookahead_guard():
    # Truncating the future must not change any earlier feature row.
    assert assert_no_lookahead(_bars(), warmup=25, use_astro=False) is True


def test_target_alignment_is_next_day_sign():
    bars = _bars()
    fm = FeatureFactory(warmup=25, use_astro=False, use_gann=True).build(bars)
    # y must equal the sign of the recorded forward return (1 = up).
    assert np.all(fm.y == (fm.fwd_return > 0).astype(int))
    # And there is exactly one fewer usable sample than (bars - warmup) because the last bar
    # has no known forward return.
    assert len(fm.y) == len(bars) - 25 - 1


def test_features_are_finite():
    fm = FeatureFactory(warmup=25, use_astro=True, use_gann=True).build(_bars())
    assert np.all(np.isfinite(fm.X))


def test_determinism():
    a = FeatureFactory(warmup=25, use_astro=False, use_gann=True).build(_bars())
    b = FeatureFactory(warmup=25, use_astro=False, use_gann=True).build(_bars())
    assert np.allclose(a.X, b.X)
