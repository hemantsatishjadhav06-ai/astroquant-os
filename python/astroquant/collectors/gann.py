"""
Agent 5 — Gann Collector  (docs/004 §Agent 5, docs/013 roadmap).

Pure-Python implementation of W.D. Gann's geometric constructs:

  * **Square of Nine** price levels — projects support/resistance by rotating the square root
    of a price around the wheel. One 360° rotation adds 2 to the square root, so a level θ degrees
    around the wheel is ``(sqrt(price) ± θ/180)²``. Cardinal (0/90/180/270) and ordinal
    (45/135/225/315) angles are the classic turning levels.
  * **Gann angles / fan** — the 1×1 ("45° line", one price-unit per time-unit) and its faster/slower
    cousins (2×1, 1×2, 3×1, 1×3 …) projected forward from an anchor pivot.
  * **Time cycles / anniversary dates** — Gann's calendar counts (30/45/60/90/120/144/180/270/360 days
    and yearly anniversaries) projected from an anchor pivot date; candidate turning windows.

Everything is a deterministic function of its inputs (no look-ahead): the anchor pivot must be a
*known, past* swing high/low — the Feature Factory enforces that the anchor date ≤ as-of date.

The docs flag a future C++/pybind11 fast-path; this Python engine is the reference implementation and
stays the swappable contract behind ``GannCollector``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from astroquant.agents.base import Agent, Health, RunContext, RunResult, content_hash, get_logger
from astroquant.db.models import GannCycle

log = get_logger("collector.gann")

# Classic Square-of-Nine wheel angles (degrees). Cardinals are the strongest turning levels.
CARDINAL_ANGLES = [90.0, 180.0, 270.0, 360.0]
ORDINAL_ANGLES = [45.0, 135.0, 225.0, 315.0]

# Gann's recurring calendar counts (days). 144 = 12² (a "master" number); 365 = anniversary.
GANN_TIME_CYCLES = [30, 45, 60, 90, 120, 144, 180, 270, 360, 365]

# Gann fan slopes as (price_units, time_units). 1x1 is the backbone 45° line.
GANN_FAN_RATIOS: dict[str, tuple[int, int]] = {
    "8x1": (8, 1), "4x1": (4, 1), "3x1": (3, 1), "2x1": (2, 1),
    "1x1": (1, 1),
    "1x2": (1, 2), "1x3": (1, 3), "1x4": (1, 4), "1x8": (1, 8),
}


@dataclass
class GannLevel:
    angle_deg: float
    kind: str            # "support" | "resistance"
    price: float


@dataclass
class GannCycleHit:
    anchor_date: str
    cycle_len: int       # calendar days
    target_date: str


@dataclass
class GannFanPoint:
    ratio: str           # e.g. "1x1"
    days_out: int
    price_up: float      # rising fan line from the pivot
    price_down: float    # falling fan line from the pivot


def square_of_nine(price: float, angles: list[float] | None = None) -> list[GannLevel]:
    """Project Square-of-Nine support/resistance levels around ``price``.

    A level θ° around the wheel is ``(sqrt(price) ± θ/180)²`` — '+' for resistance (above),
    '-' for support (below). Requires price > 0.
    """
    if price <= 0:
        raise ValueError("Square of Nine requires a positive price")
    root = math.sqrt(price)
    wheel = angles if angles is not None else sorted(CARDINAL_ANGLES + ORDINAL_ANGLES)
    out: list[GannLevel] = []
    for a in wheel:
        step = a / 180.0
        out.append(GannLevel(angle_deg=a, kind="resistance", price=round((root + step) ** 2, 4)))
        down_root = root - step
        if down_root > 0:  # below the wheel centre is meaningless
            out.append(GannLevel(angle_deg=a, kind="support", price=round(down_root ** 2, 4)))
    return out


def gann_fan(
    anchor_price: float, points_per_day: float, days_out: int,
    ratios: dict[str, tuple[int, int]] | None = None,
) -> list[GannFanPoint]:
    """Project Gann fan lines from a pivot. ``points_per_day`` scales the 1×1 line to the
    instrument (e.g. NIFTY ~ a few points/day). price_up/price_down are the fan values after
    ``days_out`` days."""
    r = ratios or GANN_FAN_RATIOS
    out: list[GannFanPoint] = []
    for name, (pu, tu) in r.items():
        slope = points_per_day * (pu / tu)          # price units per day along this ray
        delta = slope * days_out
        out.append(GannFanPoint(
            ratio=name, days_out=days_out,
            price_up=round(anchor_price + delta, 4),
            price_down=round(anchor_price - delta, 4),
        ))
    return out


def time_cycles(anchor: date, cycles: list[int] | None = None) -> list[GannCycleHit]:
    """Project Gann calendar counts forward from an anchor pivot date."""
    cs = cycles or GANN_TIME_CYCLES
    return [
        GannCycleHit(anchor.isoformat(), c, (anchor + timedelta(days=c)).isoformat())
        for c in cs
    ]


class GannCollector:
    name = "gann_collector"
    version = "0.1.0"

    def __init__(self, points_per_day: float = 1.0) -> None:
        self.points_per_day = points_per_day

    # --- pure computations (unit-testable without a DB) ---

    def levels_for_price(self, price: float) -> list[GannLevel]:
        return square_of_nine(price)

    def fan_for_pivot(self, anchor_price: float, days_out: int) -> list[GannFanPoint]:
        return gann_fan(anchor_price, self.points_per_day, days_out)

    def cycles_for_anchor(self, anchor: date) -> list[GannCycleHit]:
        return time_cycles(anchor)

    def cycle_rows(self, symbol_id: int, anchor: date, anchor_type: str = "swing") -> list[GannCycle]:
        """ORM rows for persistence into gann_cycles (docs/006)."""
        return [
            GannCycle(
                symbol_id=symbol_id, anchor_date=anchor, cycle_len=hit.cycle_len,
                anchor_type=anchor_type, target_date=date.fromisoformat(hit.target_date),
            )
            for hit in self.cycles_for_anchor(anchor)
        ]

    # --- agent entrypoint ---

    def run(self, ctx: RunContext) -> RunResult:
        anchor = ctx.start or date.today()
        anchor_price = float(ctx.config.get("anchor_price", 100.0))
        days_out = int(ctx.config.get("days_out", 90))
        levels = self.levels_for_price(anchor_price)
        cycles = self.cycles_for_anchor(anchor)
        self.fan_for_pivot(anchor_price, days_out)
        n_rows = len(levels) + len(cycles)
        res = RunResult(
            agent=self.name, status="ok", rows_written=n_rows,
            metrics={"levels": len(levels), "cycles": len(cycles), "anchor_price": anchor_price},
            output_hashes={"sq9": content_hash([(l.angle_deg, l.kind, l.price) for l in levels])},
        )
        res.write_manifest(ctx)
        log.info("gann: %d Sq9 levels + %d time-cycles from anchor %s @ %.2f",
                 len(levels), len(cycles), anchor, anchor_price)
        return res

    def healthcheck(self) -> Health:
        try:
            assert square_of_nine(144.0)  # sqrt(144)=12 -> deterministic wheel
            return Health(ok=True, detail="gann engine ready (pure-python reference)")
        except Exception as e:  # pragma: no cover
            return Health(ok=False, detail=str(e))


# Protocol conformance at import time.
_: Agent = GannCollector()  # type: ignore[assignment]
