"""
Decision logic (spec §7): deterministic (vol regime, conviction, direction) → structure, with the
Greek-aware gates enforced. Exit logic lives in the engine; this module only selects + gates entries.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

from astroquant.strategies.options_greeks import structures as st
from astroquant.strategies.options_greeks.chain import OptionChain


class VolRegime(str, Enum):
    CHEAP = "CHEAP"        # iv_rank <= 0.30 → prefer BUYING vol  (long Gamma / short Theta)
    NEUTRAL = "NEUTRAL"    # prefer Theta-positive, Gamma-safe (calendars / spreads)
    RICH = "RICH"          # iv_rank >= 0.70 → prefer SELLING vol (long Theta / short Gamma)


def classify_regime(iv_rank: float) -> VolRegime:
    if iv_rank >= 0.70:
        return VolRegime.RICH
    if iv_rank <= 0.30:
        return VolRegime.CHEAP
    return VolRegime.NEUTRAL


@dataclass
class Decision:
    regime: str
    direction: str
    conviction: float
    iv_rank: int
    structure: dict
    accepted: bool
    gate_failures: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _select(chain: OptionChain, regime: VolRegime, direction: str, conviction: float) -> st.Structure:
    """The raw §7 mapping (before gates)."""
    if regime == VolRegime.CHEAP and conviction >= 0.6 and direction != "neutral":
        return st.atm_debit_spread(chain, direction)
    if regime == VolRegime.CHEAP and direction == "neutral":
        return st.long_strangle(chain)
    if regime == VolRegime.RICH and direction == "neutral":
        return st.iron_condor(chain)                       # defined-risk, not a naked strangle (v1)
    if regime == VolRegime.RICH and direction != "neutral":
        return st.broken_wing(chain, direction)
    if regime == VolRegime.NEUTRAL and direction != "neutral":
        return st.atm_debit_spread(chain, direction)       # directional, long-Gamma, defined risk
    return st.calendar(chain)                              # neutral + no conviction → income


def decide_structure(
    chain: OptionChain, direction: str, conviction: float, *, final_hour: bool = False,
) -> Decision:
    """Select a structure for the signal and enforce the spec §7 gates (with safe fallbacks)."""
    direction = direction if direction in ("long", "short", "neutral") else "neutral"
    regime = classify_regime(chain.iv_rank)
    structure = _select(chain, regime, direction, conviction)
    rationale = [f"IV rank {chain.iv_rank:.2f} → {regime.value} regime",
                 f"direction={direction}, conviction={conviction:.2f} → {structure.name}"]
    gate_failures: list[str] = []

    # Gate 1: never SELL vol when iv_rank < 0.50 → fall back to a Gamma-safe income/long structure.
    if structure.net_short_gamma and chain.iv_rank < 0.50:
        gate_failures.append("blocked SELL-vol: iv_rank < 0.50")
        structure = st.calendar(chain) if direction == "neutral" else st.atm_debit_spread(chain, direction)
        rationale.append(f"gate → switched to {structure.name} (no short-Gamma in cheap vol)")

    # Gate 2: never hold net-short-Gamma into the expiry-day final hour (Gamma cliff, §8).
    if structure.net_short_gamma and final_hour:
        gate_failures.append("blocked short-Gamma into expiry final hour (Gamma cliff)")
        structure = st.long_strangle(chain) if direction == "neutral" else st.atm_debit_spread(chain, direction)
        rationale.append(f"gate → switched to {structure.name} (buy convexity, not sell it, into the cliff)")

    accepted = not (structure.net_short_gamma and (chain.iv_rank < 0.50 or final_hour))
    return Decision(
        regime=regime.value, direction=direction, conviction=round(conviction, 3),
        iv_rank=round(chain.iv_rank, 4), structure=structure.to_dict(),
        accepted=accepted, gate_failures=gate_failures, rationale=rationale,
    )
