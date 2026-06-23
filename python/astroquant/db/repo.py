"""
Repository layer — idempotent upserts wiring the collectors into the warehouse (docs/004, 006).

Every write is by-primary-key via ``Session.merge`` so a re-run of any collector *heals*
(updates in place) and never duplicates — the idempotency contract from docs/004 §"Runs MUST
be idempotent". Works identically on SQLite (local) and Postgres/Timescale (prod).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from astroquant.collectors.astronomy import AspectRow, PlanetRow
from astroquant.collectors.sources.market_sources import Bar as SourceBar
from astroquant.db.models import (
    Bar,
    GannCycle,
    PlanetaryAspect,
    PlanetaryData,
    Signal,
    Symbol,
)


def get_or_create_symbol(
    session: Session, symbol: str, exchange: str = "NSE", instrument: str = "INDEX"
) -> Symbol:
    existing = session.execute(
        select(Symbol).where(
            Symbol.symbol == symbol,
            Symbol.exchange == exchange,
            Symbol.instrument == instrument,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    sym = Symbol(symbol=symbol, exchange=exchange, instrument=instrument, is_active=True)
    session.add(sym)
    session.flush()  # assign symbol_id
    return sym


def upsert_planetary_rows(session: Session, rows: list[PlanetRow]) -> int:
    for r in rows:
        session.merge(
            PlanetaryData(
                obs_date=date.fromisoformat(r.obs_date),
                body=r.body,
                longitude_sidereal=r.longitude_sidereal,
                longitude_tropical=r.longitude_tropical,
                speed=r.speed,
                is_retrograde=r.is_retrograde,
                sign=r.sign,
                nakshatra=r.nakshatra,
                pada=r.pada,
                source="swisseph",
            )
        )
    return len(rows)


def upsert_aspect_rows(session: Session, rows: list[AspectRow]) -> int:
    for a in rows:
        session.merge(
            PlanetaryAspect(
                obs_date=date.fromisoformat(a.obs_date),
                body_a=a.body_a,
                body_b=a.body_b,
                angle_deg=a.angle_deg,
                aspect=None,
            )
        )
    return len(rows)


def upsert_bars(session: Session, symbol_id: int, bars: list[SourceBar]) -> int:
    for b in bars:
        session.merge(
            Bar(
                symbol_id=symbol_id,
                ts=b.ts,
                interval=b.interval,
                source=b.source,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=b.volume,
                oi=b.oi,
                adj_close=None,
            )
        )
    return len(bars)


def upsert_gann_cycles(session: Session, cycles: list[GannCycle]) -> int:
    for c in cycles:
        session.merge(c)
    return len(cycles)


def record_signal(session: Session, **fields) -> Signal:
    """Append a research verdict to the signals ledger (docs/007 §8 discoveries)."""
    sig = Signal(**fields)
    session.add(sig)
    session.flush()
    return sig


def count_planetary_rows(session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(PlanetaryData)).scalar_one())
