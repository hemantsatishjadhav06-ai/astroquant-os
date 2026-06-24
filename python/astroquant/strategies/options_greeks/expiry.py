"""
NSE/BSE expiry calendar + the Gamma-cliff rule (spec §8).

As of 2026-06 (VERIFY weekly — these shifted in Sep 2025 and adjust for trading holidays):
    NIFTY 50      weekly Tuesday,   monthly last Tuesday
    SENSEX (BSE)  weekly Thursday,  monthly last Thursday
    BANK NIFTY    no weekly,        monthly last Tuesday
    Stocks (NSE)  no weekly,        monthly last Thursday
The Gamma cliff: near-ATM Gamma goes vertical on expiry day — v1 forbids new net-short-Gamma
entries in the expiry-day final hour.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

# weekday(): Mon=0 … Sun=6. Tuesday=1, Thursday=3.
WEEKLY_DOW: dict[str, int] = {"NIFTY": 1, "FINNIFTY": 1, "SENSEX": 3, "BANKEX": 3}
MONTHLY_DOW: dict[str, int] = {
    "NIFTY": 1, "FINNIFTY": 1, "BANKNIFTY": 1, "SENSEX": 3, "BANKEX": 3,
}
_DEFAULT_MONTHLY_DOW = 3  # stocks: last Thursday


def _next_weekday(d: date, dow: int) -> date:
    return d + timedelta(days=(dow - d.weekday()) % 7)


def _last_weekday_of_month(year: int, month: int, dow: int) -> date:
    last = date(year, month, monthrange(year, month)[1])
    return last - timedelta(days=(last.weekday() - dow) % 7)


def has_weekly(symbol: str) -> bool:
    return symbol.upper() in WEEKLY_DOW


def next_weekly_expiry(symbol: str, from_date: date) -> date:
    """Soonest weekly expiry on/after ``from_date`` (falls back to monthly if no weekly)."""
    s = symbol.upper()
    if s not in WEEKLY_DOW:
        return next_monthly_expiry(s, from_date)
    return _next_weekday(from_date, WEEKLY_DOW[s])


def next_monthly_expiry(symbol: str, from_date: date) -> date:
    dow = MONTHLY_DOW.get(symbol.upper(), _DEFAULT_MONTHLY_DOW)
    exp = _last_weekday_of_month(from_date.year, from_date.month, dow)
    if exp >= from_date:
        return exp
    ny, nm = (from_date.year + (from_date.month == 12), from_date.month % 12 + 1)
    return _last_weekday_of_month(ny, nm, dow)


def is_expiry_day(symbol: str, d: date) -> bool:
    return d == next_weekly_expiry(symbol, d)


def dte(symbol: str, from_date: date, kind: str = "weekly") -> int:
    """Calendar days to the chosen expiry (weekly|monthly)."""
    exp = next_weekly_expiry(symbol, from_date) if kind == "weekly" else next_monthly_expiry(symbol, from_date)
    return max(0, (exp - from_date).days)


def gamma_cliff_block(symbol: str, d: date, *, final_hour: bool = False) -> bool:
    """True when a new net-short-Gamma entry must be blocked (expiry-day final hour, spec §8)."""
    return is_expiry_day(symbol, d) and final_hour
