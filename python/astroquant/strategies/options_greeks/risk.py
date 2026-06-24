"""
Risk sizer (spec §9) — hard, pre-trade invariants. Size by the WORST-CASE OVERNIGHT GAP, not margin.

    lots = floor(risk_cap / worst_case_loss_per_lot)         risk_cap = R% of deployable capital
The worst case combines the structure's grid max-loss with a 4–5% adverse gap, so even a "defined-risk"
book is sized against a violent open. Returns a sizing the engine can attach to order intents.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from astroquant.strategies.options_greeks.structures import Structure, lot_of


@dataclass
class RiskSizing:
    lots: int
    risk_cap: float
    worst_case_per_lot: float
    total_worst_case: float
    gap_pct: float
    within_cap: bool

    def to_dict(self) -> dict:
        return asdict(self)


def worst_case_loss_per_lot(structure: Structure, symbol: str, spot: float, gap_pct: float = 0.05) -> float:
    """Worst of the structure's capped max-loss and the loss at a ±gap overnight move."""
    lot = lot_of(symbol)
    worst_grid = abs(structure.max_loss)
    gap_loss = 0.0
    for S in (spot * (1 - gap_pct), spot * (1 + gap_pct)):
        intrinsic = sum(leg.qty * (max(0.0, S - leg.strike) if leg.opt == "C" else max(0.0, leg.strike - S))
                        for leg in structure.legs)
        pnl = lot * (intrinsic - structure.net_debit)
        gap_loss = max(gap_loss, -pnl)
    return round(max(worst_grid, gap_loss), 0)


def size_position(
    structure: Structure, symbol: str, spot: float, *,
    capital: float = 1_000_000.0, risk_pct: float = 0.015, gap_pct: float = 0.05,
) -> RiskSizing:
    risk_cap = capital * risk_pct
    wpl = worst_case_loss_per_lot(structure, symbol, spot, gap_pct)
    lots = int(math.floor(risk_cap / wpl)) if wpl > 0 else 0
    lots = max(0, lots)
    return RiskSizing(
        lots=lots, risk_cap=round(risk_cap, 0), worst_case_per_lot=wpl,
        total_worst_case=round(lots * wpl, 0), gap_pct=gap_pct,
        within_cap=(lots * wpl) <= risk_cap + 1e-6,
    )
