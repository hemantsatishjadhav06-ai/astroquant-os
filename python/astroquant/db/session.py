"""
Database session/engine helpers (docs/006).

Runs anywhere: defaults to a local SQLite file so the whole platform is usable with
**no Docker and no Postgres**. In production, point AQ_DB_URL at TimescaleDB
(e.g. ``postgresql+psycopg://astroquant:astroquant@localhost:5432/astroquant``) and the
exact same repository code (db/repo.py) works unchanged — upserts use ``Session.merge``,
which is dialect-agnostic, so "re-runs heal, never duplicate" holds on both backends.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from astroquant.db.models import Base

# Local-first default. Override with AQ_DB_URL for Postgres/Timescale.
DEFAULT_DB_URL = "sqlite:///astroquant.db"


def resolve_db_url(url: str | None = None) -> str:
    """Explicit arg > AQ_DB_URL env > local SQLite default."""
    return url or os.environ.get("AQ_DB_URL") or DEFAULT_DB_URL


def get_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    resolved = resolve_db_url(url)
    connect_args = {"check_same_thread": False} if resolved.startswith("sqlite") else {}
    return create_engine(resolved, echo=echo, future=True, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    """Create core tables from the declarative metadata (idempotent)."""
    Base.metadata.create_all(bind=engine)


def get_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Transactional scope: commit on success, rollback on error, always close."""
    sm = get_sessionmaker(engine)
    session = sm()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
