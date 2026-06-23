"""
SQLAlchemy models for the core PostgreSQL/TimescaleDB tables (subset of docs/006).
Hypertables (bars, option_chain_snapshots) are created via raw SQL in sql/002_hypertables.sql
after table creation, since create_hypertable is a Timescale function.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric,
    SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Symbol(Base):
    __tablename__ = "symbols"
    # BigInteger on Postgres; INTEGER on SQLite so the local file DB autoincrements the rowid PK.
    symbol_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    exchange: Mapped[str] = mapped_column(String, nullable=False)
    instrument: Mapped[str] = mapped_column(String, nullable=False)  # EQ/FUT/OPT/INDEX
    isin: Mapped[str | None] = mapped_column(String)
    sector: Mapped[str | None] = mapped_column(String)
    lot_size: Mapped[int | None] = mapped_column(Integer)
    tick_size: Mapped[float | None] = mapped_column(Numeric)
    listing_date: Mapped[date | None] = mapped_column(Date)
    delisting_date: Mapped[date | None] = mapped_column(Date)  # kept => avoids survivorship bias
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("symbol", "exchange", "instrument"),)


class Bar(Base):
    __tablename__ = "bars"  # -> hypertable on ts
    symbol_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    interval: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, primary_key=True)
    open: Mapped[float] = mapped_column(Numeric)
    high: Mapped[float] = mapped_column(Numeric)
    low: Mapped[float] = mapped_column(Numeric)
    close: Mapped[float] = mapped_column(Numeric)
    volume: Mapped[int] = mapped_column(BigInteger)
    oi: Mapped[int | None] = mapped_column(BigInteger)
    adj_close: Mapped[float | None] = mapped_column(Numeric)


class PlanetaryData(Base):
    __tablename__ = "planetary_data"
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    body: Mapped[str] = mapped_column(String, primary_key=True)
    longitude_sidereal: Mapped[float] = mapped_column(Numeric)
    longitude_tropical: Mapped[float] = mapped_column(Numeric)
    speed: Mapped[float | None] = mapped_column(Numeric)
    is_retrograde: Mapped[bool | None] = mapped_column(Boolean)
    sign: Mapped[int | None] = mapped_column(SmallInteger)
    nakshatra: Mapped[int | None] = mapped_column(SmallInteger)
    pada: Mapped[int | None] = mapped_column(SmallInteger)
    source: Mapped[str] = mapped_column(String, default="swisseph")


class PlanetaryAspect(Base):
    __tablename__ = "planetary_aspects"
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    body_a: Mapped[str] = mapped_column(String, primary_key=True)
    body_b: Mapped[str] = mapped_column(String, primary_key=True)
    angle_deg: Mapped[float] = mapped_column(Numeric)
    aspect: Mapped[str | None] = mapped_column(String)


class GannCycle(Base):
    __tablename__ = "gann_cycles"
    symbol_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    anchor_date: Mapped[date] = mapped_column(Date, primary_key=True)
    cycle_len: Mapped[int] = mapped_column(Integer, primary_key=True)
    anchor_type: Mapped[str | None] = mapped_column(String)
    target_date: Mapped[date] = mapped_column(Date)


class EconomicData(Base):
    __tablename__ = "economic_data"
    series_id: Mapped[str] = mapped_column(String, primary_key=True)
    reference_date: Mapped[date] = mapped_column(Date, primary_key=True)
    release_date: Mapped[date] = mapped_column(Date, primary_key=True)  # vintage => no look-ahead
    value: Mapped[float | None] = mapped_column(Numeric)
    source: Mapped[str | None] = mapped_column(String)


class Hypothesis(Base):
    __tablename__ = "hypotheses"
    hypothesis_id: Mapped[str] = mapped_column(String, primary_key=True)  # e.g. RQ-004
    statement: Mapped[str | None] = mapped_column(Text)
    spec: Mapped[str | None] = mapped_column(Text)        # JSON string (full pre-registration)
    status: Mapped[str | None] = mapped_column(String)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Signal(Base):
    __tablename__ = "signals"
    signal_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    hypothesis_id: Mapped[str | None] = mapped_column(ForeignKey("hypotheses.hypothesis_id"))
    name: Mapped[str | None] = mapped_column(String)
    family: Mapped[str | None] = mapped_column(String)    # technical/market/astro/gann/news/macro
    verdict: Mapped[str | None] = mapped_column(String)   # edge/no_edge/conditional
    effect_size: Mapped[float | None] = mapped_column(Numeric)
    p_raw: Mapped[float | None] = mapped_column(Numeric)
    p_adj: Mapped[float | None] = mapped_column(Numeric)
    n_comparisons: Mapped[int | None] = mapped_column(Integer)
    dsr: Mapped[float | None] = mapped_column(Numeric)
    pbo: Mapped[float | None] = mapped_column(Numeric)
    dataset_hash: Mapped[str | None] = mapped_column(String)
    code_commit: Mapped[str | None] = mapped_column(String)
