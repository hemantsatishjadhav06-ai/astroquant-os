"""
Hypothesis generation (docs/007 §1 pre-registration).

A ``HypothesisSpec`` is a *registered* research question: which family is on trial, against which
baseline, on which symbol, with which decision threshold. The generator enumerates the search space;
its size is the multiple-testing denominator the orchestrator carries forward.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from astroquant.features.factory import BASELINE_FAMILIES

# The families we put "on trial" (each is a separate, pre-registered question).
DEFAULT_TRIAL_SETS: tuple[tuple[str, ...], ...] = (
    ("astro",),
    ("gann",),
    ("astro", "gann"),
)
EXCHANGE_FOR_SOURCE = {"nse": "NSE", "bse": "BSE"}


@dataclass(frozen=True)
class HypothesisSpec:
    id: str
    symbol: str
    exchange: str
    source: str
    trial_families: tuple[str, ...]
    baseline_families: tuple[str, ...] = BASELINE_FAMILIES
    prob_band: float = 0.02
    horizon: int = 1
    statement: str = ""

    @property
    def augmented_families(self) -> tuple[str, ...]:
        # baseline ∪ trial, order-preserving, de-duplicated
        return tuple(dict.fromkeys(self.baseline_families + self.trial_families))

    @property
    def family_label(self) -> str:
        return "+".join(self.trial_families)


def generate_hypotheses(
    symbols: list[str],
    source: str = "nse",
    *,
    exchange: str | None = None,
    trial_sets: tuple[tuple[str, ...], ...] = DEFAULT_TRIAL_SETS,
    prob_bands: tuple[float, ...] = (0.0, 0.02),
    start_index: int = 1,
) -> list[HypothesisSpec]:
    """Enumerate (symbol × family-on-trial × decision-band) hypotheses."""
    exch = exchange or EXCHANGE_FOR_SOURCE.get(source, "NSE")
    base = "+".join(BASELINE_FAMILIES)
    specs: list[HypothesisSpec] = []
    i = start_index
    for sym in symbols:
        for tf in trial_sets:
            for band in prob_bands:
                specs.append(HypothesisSpec(
                    id=f"H-{i:04d}", symbol=sym, exchange=exch, source=source,
                    trial_families=tf, prob_band=band,
                    statement=(f"Do {'+'.join(tf)} features add out-of-sample, post-cost predictive "
                               f"power beyond {base} for next-day {sym} direction (band={band})?"),
                ))
                i += 1
    return specs
