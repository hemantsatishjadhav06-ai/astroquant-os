"""
Full Indian instrument universe — NSE equities + BSE equities + MCX commodities.

Loads bundled exchange masters from ``data/`` (refresh with ``scripts/fetch_universe.py``):
  * ``nse_equity.csv``  — official NSE EQUITY_L master      → Yahoo ``SYMBOL.NS``
  * ``bse_equity.csv``  — BSE active equity scrip master    → Yahoo ``<scrip_code>.BO``  (+ industry = sector)
  * ``mcx.csv``         — MCX commodity futures             → Yahoo global-commodity proxy where available
NIFTY-50 sectors are overlaid onto the matching NSE names. ~7,000+ instruments, all searchable; data is
fetched lazily per symbol via the resolved Yahoo ticker, so the catalog stays light.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).parent / "data"

# NIFTY-50 sector overlay (applied to matching NSE symbols).
_NIFTY50_SECTORS: dict[str, str] = {
    "RELIANCE": "Energy/Conglomerate", "TCS": "IT", "HDFCBANK": "Banking", "ICICIBANK": "Banking",
    "INFY": "IT", "HINDUNILVR": "FMCG", "ITC": "FMCG", "SBIN": "Banking", "BHARTIARTL": "Telecom",
    "KOTAKBANK": "Banking", "LT": "Infrastructure", "AXISBANK": "Banking", "BAJFINANCE": "NBFC",
    "ASIANPAINT": "Consumer Durables", "MARUTI": "Automobile", "HCLTECH": "IT", "SUNPHARMA": "Pharma",
    "TITAN": "Consumer Durables", "ULTRACEMCO": "Cement", "WIPRO": "IT", "NESTLEIND": "FMCG",
    "ONGC": "Energy", "NTPC": "Power", "POWERGRID": "Power", "M&M": "Automobile", "TATAMOTORS": "Automobile",
    "TATASTEEL": "Metals", "JSWSTEEL": "Metals", "ADANIENT": "Conglomerate", "ADANIPORTS": "Infrastructure",
    "COALINDIA": "Metals/Mining", "BAJAJFINSV": "NBFC", "HDFCLIFE": "Insurance", "SBILIFE": "Insurance",
    "GRASIM": "Cement", "BRITANNIA": "FMCG", "DRREDDY": "Pharma", "CIPLA": "Pharma", "DIVISLAB": "Pharma",
    "EICHERMOT": "Automobile", "HEROMOTOCO": "Automobile", "BAJAJ-AUTO": "Automobile",
    "INDUSINDBK": "Banking", "TECHM": "IT", "TATACONSUM": "FMCG", "APOLLOHOSP": "Healthcare",
    "BPCL": "Energy", "HINDALCO": "Metals", "UPL": "Chemicals", "LTIM": "IT",
}

_INDICES_RAW: list[tuple[str, str, str]] = [
    ("NIFTY", "NIFTY 50 Index", "^NSEI"), ("BANKNIFTY", "NIFTY Bank Index", "^NSEBANK"),
    ("FINNIFTY", "NIFTY Financial Services", "^CNXFIN"), ("SENSEX", "BSE SENSEX", "^BSESN"),
    ("INDIAVIX", "India VIX", "^INDIAVIX"),
]


@dataclass(frozen=True)
class StockMeta:
    symbol: str
    name: str
    sector: str = "Unknown"
    exchange: str = "NSE"        # NSE | BSE | MCX | INDEX
    instrument: str = "EQ"       # EQ | FUT | INDEX
    yahoo: str = ""              # explicit Yahoo ticker
    code: str = ""              # BSE scrip code

    @property
    def yahoo_ticker(self) -> str:
        if self.yahoo:
            return self.yahoo
        return f"{self.symbol}.NS" if self.exchange == "NSE" else self.symbol


def _read(name: str) -> list[dict]:
    p = _DATA / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _load() -> tuple[list[StockMeta], dict]:
    metas: list[StockMeta] = []
    for r in _read("nse_equity.csv"):
        s = r["symbol"].strip()
        metas.append(StockMeta(s, r["name"].strip(), _NIFTY50_SECTORS.get(s, "Equity"),
                               "NSE", "EQ", f"{s}.NS"))
    for r in _read("bse_equity.csv"):
        code, sym = r["code"].strip(), (r.get("symbol") or "").strip()
        metas.append(StockMeta(sym or code, r["name"].strip(), (r.get("industry") or "Equity").strip() or "Equity",
                               "BSE", "EQ", f"{code}.BO", code))
    for r in _read("mcx.csv"):
        metas.append(StockMeta(r["symbol"].strip(), r["name"].strip(), "Commodity",
                               "MCX", "FUT", (r.get("yahoo") or "").strip()))
    metas += [StockMeta(s, n, "Index", "INDEX", "INDEX", y) for s, n, y in _INDICES_RAW]
    by: dict = {}
    for m in metas:
        by.setdefault((m.exchange, m.symbol), m)
        by.setdefault(m.symbol, m)            # NSE loaded first → preferred for dual-listed
    return metas, by


# Back-compat exports
def load_universe(include_indices: bool = True) -> list[StockMeta]:
    metas, _ = _load()
    return metas if include_indices else [m for m in metas if m.exchange != "INDEX"]


INDICES = [StockMeta(s, n, "Index", "INDEX", "INDEX", y) for s, n, y in _INDICES_RAW]


def get_stock(symbol: str, exchange: str | None = None) -> StockMeta:
    _, by = _load()
    s = symbol.upper().strip()
    if exchange and (exchange.upper(), s) in by:
        return by[(exchange.upper(), s)]
    if s in by:
        return by[s]
    return StockMeta(s, s, "Unknown", "NSE", "EQ", f"{s}.NS")


def resolve_yahoo(symbol: str, exchange: str | None = None) -> str:
    return get_stock(symbol, exchange).yahoo_ticker


def universe_stats() -> dict:
    metas, _ = _load()
    counts: dict[str, int] = {}
    for m in metas:
        counts[m.exchange] = counts.get(m.exchange, 0) + 1
    return {"total": len(metas), "by_exchange": counts}


def search(q: str = "", exchange: str | None = None, limit: int = 50) -> list[StockMeta]:
    metas, _ = _load()
    ql = q.upper().strip()
    ex = exchange.upper() if exchange else None
    out = []
    for m in metas:
        if ex and m.exchange != ex:
            continue
        if ql and ql not in m.symbol.upper() and ql not in m.name.upper():
            continue
        out.append(m)
        if len(out) >= limit:
            break
    return out


def list_sectors() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in load_universe():
        if m.exchange == "NSE" and m.sector not in ("Equity", "Unknown"):
            out.setdefault(m.sector, []).append(m.symbol)
    return dict(sorted(out.items()))


def persist_universe(engine, *, limit: int = 500) -> int:
    """Upsert up to ``limit`` instruments into the `symbols` table (docs/006)."""
    from astroquant.db import repo
    from astroquant.db.session import session_scope

    metas = load_universe()[:limit]
    with session_scope(engine) as s:
        for m in metas:
            repo.get_or_create_symbol(s, m.symbol, m.exchange if m.exchange != "INDEX" else "NSE", m.instrument)
    return len(metas)
