"""
Agent 6 — Feature Factory  (docs/004 §Agent 6, docs/007 §3, docs/009).

Turns raw bars + the (deterministic) ephemeris + Gann geometry into a **point-in-time** feature
matrix with **family tags** (``technical`` / ``market`` / ``astro`` / ``gann``). Family tags are
what let the Research Engine run the baseline→augmented→ablation protocol (docs/007 §2): the
baseline uses {technical, market}; the augmented model adds {astro, gann}.

NON-NEGOTIABLE leakage rules (docs/007 §3, §6), enforced by construction and by tests:
  * Every feature at row t is a function of information available **at or before the close of day t**.
  * The label at row t is ``sign(return from close_t to close_{t+1})`` — it belongs to t+1, so the
    final bar (whose forward return is unknown) is dropped.
  * Truncating the input series must not change any earlier feature row (the ``no_lookahead`` test).

The ephemeris is a legitimate exception to "no future data": planetary positions for any date are
known years in advance, so using ``astro(date_t)`` is point-in-time valid. We still only ever read
the ephemeris **as of the bar's own date**.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from astroquant.collectors.astronomy import AstronomyCollector
from astroquant.collectors.gann import square_of_nine
from astroquant.collectors.sources.market_sources import Bar

# Which family each feature belongs to (drives baseline vs augmented splits in the research engine).
FEATURE_FAMILY: dict[str, str] = {
    # technical (price-derived)
    "ret_1d": "technical", "ret_5d": "technical", "mom_10": "technical",
    "vol_10": "technical", "rsi_14": "technical", "dist_sma_20": "technical",
    "gap_open": "technical",
    # market microstructure
    "volume_z": "market",
    # astro (ephemeris-derived; deterministic, point-in-time valid)
    "moon_illum": "astro", "moon_phase_sin": "astro", "moon_phase_cos": "astro",
    "sun_lon_sin": "astro", "sun_lon_cos": "astro", "mercury_retro": "astro",
    "retro_count": "astro", "jup_sat_sep": "astro",
    # gann (geometry-derived)
    "gann_dist_res": "gann", "gann_dist_sup": "gann", "gann_cycle_prox": "gann",
}

BASELINE_FAMILIES = ("technical", "market")
AUGMENTED_FAMILIES = ("technical", "market", "astro", "gann")
GANN_TIME_CYCLES = (30, 45, 60, 90, 120, 144, 180, 270, 360)


@dataclass
class FeatureMatrix:
    dates: list[str]
    feature_names: list[str]
    X: np.ndarray                       # (n_samples, n_features)
    y: np.ndarray                       # (n_samples,) 1 = next-day up, 0 = down
    fwd_return: np.ndarray              # (n_samples,) realised next-day return (for post-cost P&L)
    close: np.ndarray                   # (n_samples,) close at decision time t
    family_of: dict[str, str] = field(default_factory=dict)

    def family_columns(self, families: tuple[str, ...]) -> list[int]:
        return [i for i, n in enumerate(self.feature_names) if self.family_of[n] in families]

    def subset(self, families: tuple[str, ...]) -> np.ndarray:
        cols = self.family_columns(families)
        return self.X[:, cols]


def _rsi(closes: np.ndarray, period: int = 14) -> float:
    """Wilder RSI on the last ``period`` deltas of ``closes`` (uses only past data)."""
    if len(closes) <= period:
        return 50.0
    deltas = np.diff(closes[-(period + 1):])
    gains = np.clip(deltas, 0, None).mean()
    losses = -np.clip(deltas, None, 0).mean()
    if losses == 0:
        return 100.0
    rs = gains / losses
    return float(100.0 - 100.0 / (1.0 + rs))


def _cycle_proximity(days_since_pivot: int) -> float:
    """1.0 when exactly on a Gann calendar count, decaying linearly to 0 within ±7 days."""
    best = 0.0
    for c in GANN_TIME_CYCLES:
        dist = abs(days_since_pivot - c)
        best = max(best, max(0.0, 1.0 - dist / 7.0))
    return best


class FeatureFactory:
    name = "feature_factory"
    version = "0.1.0"

    def __init__(self, warmup: int = 25, use_astro: bool = True, use_gann: bool = True) -> None:
        self.warmup = warmup
        self.use_astro = use_astro
        self.use_gann = use_gann
        self._astro = AstronomyCollector() if use_astro else None

    def _astro_features(self, iso_date: str) -> dict[str, float]:
        from datetime import date as _date

        d = _date.fromisoformat(iso_date)
        rows = {p.body: p for p in self._astro.planets_for_date(d)}  # type: ignore[union-attr]
        mp = self._astro.moon_phase_for_date(d)                      # type: ignore[union-attr]
        phase = math.radians(mp.phase_angle)
        sun_lon = math.radians(rows["Sun"].longitude_sidereal)
        retro_count = sum(1 for r in rows.values() if r.is_retrograde)
        jup, sat = rows["Jupiter"].longitude_sidereal, rows["Saturn"].longitude_sidereal
        diff = abs(jup - sat) % 360.0
        sep = min(diff, 360.0 - diff) / 180.0
        return {
            "moon_illum": mp.illumination,
            "moon_phase_sin": math.sin(phase), "moon_phase_cos": math.cos(phase),
            "sun_lon_sin": math.sin(sun_lon), "sun_lon_cos": math.cos(sun_lon),
            "mercury_retro": 1.0 if rows["Mercury"].is_retrograde else 0.0,
            "retro_count": float(retro_count),
            "jup_sat_sep": sep,
        }

    def build(self, bars: list[Bar]) -> FeatureMatrix:
        if len(bars) < self.warmup + 2:
            raise ValueError(f"need at least {self.warmup + 2} bars, got {len(bars)}")
        bars = sorted(bars, key=lambda b: b.ts)
        closes = np.array([b.close for b in bars], dtype=float)
        opens = np.array([b.open for b in bars], dtype=float)
        vols = np.array([b.volume for b in bars], dtype=float)

        active = [n for n in FEATURE_FAMILY if (
            (self.use_astro or FEATURE_FAMILY[n] != "astro")
            and (self.use_gann or FEATURE_FAMILY[n] != "gann")
        )]

        rows_X: list[list[float]] = []
        rows_y: list[int] = []
        fwd: list[float] = []
        dates: list[str] = []
        close_at_t: list[float] = []

        # t ranges over decision points; need t+1 for the label, so stop before the last bar.
        for t in range(self.warmup, len(bars) - 1):
            past = closes[: t + 1]                       # info known at close of day t
            r = np.diff(past[-11:]) / past[-11:-1]       # last 10 daily returns
            feats: dict[str, float] = {
                "ret_1d": float(past[-1] / past[-2] - 1.0),
                "ret_5d": float(past[-1] / past[-6] - 1.0),
                "mom_10": float(past[-1] / past[-11] - 1.0),
                "vol_10": float(np.std(r)),
                "rsi_14": _rsi(past, 14) / 100.0,
                "dist_sma_20": float(past[-1] / past[-20:].mean() - 1.0),
                "gap_open": float(opens[t] / closes[t - 1] - 1.0),
                "volume_z": float((vols[t] - vols[t - 20:t].mean()) / (vols[t - 20:t].std() + 1e-9)),
            }
            if self.use_astro:
                feats.update(self._astro_features(bars[t].ts.date().isoformat()))
            if self.use_gann:
                pivot_hi = float(closes[max(0, t - 20): t + 1].max())
                pivot_lo = float(closes[max(0, t - 20): t + 1].min())
                res = [lv.price for lv in square_of_nine(pivot_hi) if lv.price > closes[t]]
                sup = [lv.price for lv in square_of_nine(pivot_lo) if 0 < lv.price < closes[t]]
                nearest_res = min(res) if res else closes[t] * 1.1
                nearest_sup = max(sup) if sup else closes[t] * 0.9
                days_since_pivot = int(t - int(np.argmax(closes[max(0, t - 20): t + 1])) - max(0, t - 20))
                feats["gann_dist_res"] = float((nearest_res - closes[t]) / closes[t])
                feats["gann_dist_sup"] = float((closes[t] - nearest_sup) / closes[t])
                feats["gann_cycle_prox"] = _cycle_proximity(abs(days_since_pivot))

            rows_X.append([feats[n] for n in active])
            ret_next = float(closes[t + 1] / closes[t] - 1.0)
            rows_y.append(1 if ret_next > 0 else 0)
            fwd.append(ret_next)
            dates.append(bars[t].ts.date().isoformat())
            close_at_t.append(float(closes[t]))

        return FeatureMatrix(
            dates=dates, feature_names=active,
            X=np.array(rows_X, dtype=float), y=np.array(rows_y, dtype=int),
            fwd_return=np.array(fwd, dtype=float), close=np.array(close_at_t, dtype=float),
            family_of={n: FEATURE_FAMILY[n] for n in active},
        )


def assert_no_lookahead(bars: list[Bar], warmup: int = 25, use_astro: bool = False) -> bool:
    """Leakage guard (docs/007 §6): truncating the future must not change past feature rows.

    Build on the full series and on a series truncated by ``k`` bars; every overlapping feature
    row must be identical. Any difference means a feature peeked into the future. Returns True.
    """
    ff = FeatureFactory(warmup=warmup, use_astro=use_astro, use_gann=True)
    full = ff.build(bars)
    truncated = ff.build(bars[:-5])
    m = len(truncated.X)
    if not np.allclose(full.X[:m], truncated.X, rtol=1e-9, atol=1e-9):
        raise AssertionError("look-ahead detected: feature rows changed when future bars were removed")
    return True
