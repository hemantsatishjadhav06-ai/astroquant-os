"""
Relationship studies for the Market Genome Project (docs/007 integrity applies here too).

Each study tests whether a *condition* (a feature/derived series) is related to an *outcome*
(next-day direction / volatility / reversal) using a correlation effect size with a **permutation
p-value**, then a **Benjamini–Hochberg** correction across the whole battery so that testing many
relationships doesn't manufacture a false discovery. The result is a `Finding` per study.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

import numpy as np

from astroquant.agents.base import get_logger
from astroquant.collectors.sources.market_sources import get_source
from astroquant.features.factory import FeatureFactory, FeatureMatrix
from astroquant.research.stats import benjamini_hochberg

log = get_logger("genome.studies")

# (id, question, predictor_key, outcome_key). Keys resolve to arrays in `_build_arrays`.
STUDIES: list[tuple[str, str, str, str]] = [
    ("G-001", "Does Moon illumination affect next-day volatility?", "moon_illum", "volatility"),
    ("G-002", "Does Moon phase (waxing/waning) predict next-day direction?", "moon_phase_sin", "direction"),
    ("G-003", "Does Mercury retrograde shift next-day returns?", "mercury_retro", "return"),
    ("G-004", "Does the count of retrograde planets affect volatility?", "retro_count", "volatility"),
    ("G-005", "Do Gann time-cycles (proximity) predict reversals?", "gann_cycle_prox", "reversal"),
    ("G-006", "Does distance to the nearest Gann Sq9 level predict direction?", "gann_dist_res", "direction"),
    ("G-007", "Does the Sun–Saturn/Jupiter separation relate to returns?", "jup_sat_sep", "return"),
    ("G-008", "Does RSI(14) predict next-day reversals? (method control)", "rsi_14", "reversal"),
    ("G-009", "Is there a weekday (Monday) effect on returns? (method control)", "is_monday", "return"),
    ("G-010", "Does short-term momentum predict next-day direction? (method control)", "mom_10", "direction"),
]


@dataclass
class Finding:
    id: str
    question: str
    predictor: str
    outcome: str
    n: int
    effect: float            # signed correlation
    abs_effect: float
    p_raw: float
    q_value: float = 1.0     # BH across the battery
    verdict: str = "untested"  # relationship | no_relationship

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GenomeReport:
    symbol: str
    source: str
    n_studies: int
    n_relationships: int
    findings: list[Finding]
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def _column(fm: FeatureMatrix, name: str) -> np.ndarray:
    return fm.X[:, fm.feature_names.index(name)]


def _build_arrays(fm: FeatureMatrix) -> dict[str, np.ndarray]:
    fwd = fm.fwd_return
    ret_1d = _column(fm, "ret_1d")
    weekdays = np.array([date.fromisoformat(d).weekday() for d in fm.dates])
    arrays: dict[str, np.ndarray] = {
        # outcomes
        "direction": fm.y.astype(float),
        "return": fwd,
        "volatility": np.abs(fwd),                                  # next-day realised |return|
        "reversal": (np.sign(fwd) != np.sign(ret_1d)).astype(float),
        # derived predictors
        "is_monday": (weekdays == 0).astype(float),
    }
    # any feature column is a valid predictor by name
    for name in fm.feature_names:
        arrays[name] = _column(fm, name)
    return arrays


def _corr(x: np.ndarray, y: np.ndarray) -> float:
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _permutation_p(x: np.ndarray, y: np.ndarray, effect: float, n_perm: int, seed: int) -> float:
    """Two-sided permutation p-value: shuffle y, recompute |corr|, fraction ≥ observed."""
    rng = np.random.default_rng(seed)
    obs = abs(effect)
    count = 0
    for _ in range(n_perm):
        if abs(_corr(x, rng.permutation(y))) >= obs:
            count += 1
    return (count + 1) / (n_perm + 1)


def run_genome(
    symbol: str = "NIFTY",
    source: str = "nse",
    *,
    start: date = date(2016, 1, 1),
    end: date = date(2024, 12, 31),
    n_perm: int = 200,
    seed: int = 7,
    alpha: float = 0.05,
) -> GenomeReport:
    """Run the full battery of relationship studies on one symbol and return graded findings."""
    kwargs = {"fallback_synthetic": True} if source in ("nse", "bse") else {}
    bars = get_source(source, **kwargs).history(symbol, "1d", start, end)
    fm = FeatureFactory(warmup=25, use_astro=True, use_gann=True).build(bars)
    arrays = _build_arrays(fm)

    findings: list[Finding] = []
    for sid, q, pred, out in STUDIES:
        if pred not in arrays or out not in arrays:
            continue
        x, y = arrays[pred], arrays[out]
        eff = _corr(x, y)
        p = _permutation_p(x, y, eff, n_perm, seed)
        findings.append(Finding(id=sid, question=q, predictor=pred, outcome=out,
                                n=len(x), effect=round(eff, 4), abs_effect=round(abs(eff), 4), p_raw=round(p, 4)))

    # Benjamini–Hochberg across the whole battery — the multiple-testing denominator.
    if findings:
        q = benjamini_hochberg([f.p_raw for f in findings], alpha=alpha)
        for f, qq in zip(findings, q):
            f.q_value = round(float(qq), 4)
            f.verdict = "relationship" if f.q_value < alpha else "no_relationship"

    findings.sort(key=lambda f: (f.verdict != "relationship", -f.abs_effect))
    n_rel = sum(1 for f in findings if f.verdict == "relationship")
    log.info("genome[%s]: %d studies, %d relationships survived FDR", symbol, len(findings), n_rel)
    return GenomeReport(
        symbol=symbol, source=source, n_studies=len(findings), n_relationships=n_rel,
        findings=findings,
        meta={"start": start.isoformat(), "end": end.isoformat(), "n_perm": n_perm,
              "n_bars": len(bars), "n_samples": int(len(fm.y))},
    )
