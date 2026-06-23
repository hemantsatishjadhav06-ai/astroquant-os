"""Tests for the DB persistence layer — idempotent upserts on SQLite (docs/004, 006)."""
from datetime import date

from astroquant.collectors.astronomy import AstronomyCollector
from astroquant.collectors.gann import GannCollector
from astroquant.db import repo
from astroquant.db.session import get_engine, init_db, session_scope


def _mem_engine():
    eng = get_engine("sqlite:///:memory:")
    init_db(eng)
    return eng


def test_planetary_upsert_is_idempotent():
    eng = _mem_engine()
    rows = AstronomyCollector().planets_for_date(date(2024, 1, 1))
    with session_scope(eng) as s:
        repo.upsert_planetary_rows(s, rows)
    with session_scope(eng) as s:
        repo.upsert_planetary_rows(s, rows)          # re-run must heal, not duplicate
    with session_scope(eng) as s:
        assert repo.count_planetary_rows(s) == len(rows)   # 9 bodies, not 18


def test_get_or_create_symbol_stable():
    eng = _mem_engine()
    with session_scope(eng) as s:
        a = repo.get_or_create_symbol(s, "NIFTY", "NSE", "INDEX")
        first_id = a.symbol_id
    with session_scope(eng) as s:
        b = repo.get_or_create_symbol(s, "NIFTY", "NSE", "INDEX")
        assert b.symbol_id == first_id              # same row, no duplicate


def test_gann_cycle_rows_persist():
    eng = _mem_engine()
    cycles = GannCollector().cycle_rows(symbol_id=1, anchor=date(2024, 1, 1))
    with session_scope(eng) as s:
        n = repo.upsert_gann_cycles(s, cycles)
    assert n == len(cycles) > 0


def test_record_signal_writes_ledger_row():
    eng = _mem_engine()
    with session_scope(eng) as s:
        sig = repo.record_signal(
            s, name="RQ-004", family="astro", verdict="no_edge",
            effect_size=0.0, p_raw=0.4, p_adj=0.4, n_comparisons=1,
        )
        assert sig.signal_id is not None
