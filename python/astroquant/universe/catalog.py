"""
Curated NSE universe (NIFTY-50 constituents + key indices) with sector metadata.

This is a *reference snapshot* — index membership changes over time; treat it as a starting universe
and load a full instrument master from your broker for exchange-wide coverage. Yahoo tickers are
derived (``.NS`` for NSE equities) so the free data path works out of the box.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockMeta:
    symbol: str
    name: str
    sector: str
    exchange: str = "NSE"
    instrument: str = "EQ"
    active: bool = True

    @property
    def yahoo(self) -> str:
        if self.instrument == "INDEX":
            return self.symbol
        return f"{self.symbol}.{'NS' if self.exchange == 'NSE' else 'BO'}"


# (symbol, name, sector) — NIFTY-50 reference constituents.
_NIFTY50: list[tuple[str, str, str]] = [
    ("RELIANCE", "Reliance Industries", "Energy/Conglomerate"),
    ("TCS", "Tata Consultancy Services", "IT"),
    ("HDFCBANK", "HDFC Bank", "Banking"),
    ("ICICIBANK", "ICICI Bank", "Banking"),
    ("INFY", "Infosys", "IT"),
    ("HINDUNILVR", "Hindustan Unilever", "FMCG"),
    ("ITC", "ITC", "FMCG"),
    ("SBIN", "State Bank of India", "Banking"),
    ("BHARTIARTL", "Bharti Airtel", "Telecom"),
    ("KOTAKBANK", "Kotak Mahindra Bank", "Banking"),
    ("LT", "Larsen & Toubro", "Infrastructure"),
    ("AXISBANK", "Axis Bank", "Banking"),
    ("BAJFINANCE", "Bajaj Finance", "NBFC"),
    ("ASIANPAINT", "Asian Paints", "Consumer Durables"),
    ("MARUTI", "Maruti Suzuki", "Automobile"),
    ("HCLTECH", "HCL Technologies", "IT"),
    ("SUNPHARMA", "Sun Pharmaceutical", "Pharma"),
    ("TITAN", "Titan Company", "Consumer Durables"),
    ("ULTRACEMCO", "UltraTech Cement", "Cement"),
    ("WIPRO", "Wipro", "IT"),
    ("NESTLEIND", "Nestle India", "FMCG"),
    ("ONGC", "Oil & Natural Gas Corp", "Energy"),
    ("NTPC", "NTPC", "Power"),
    ("POWERGRID", "Power Grid Corp", "Power"),
    ("M&M", "Mahindra & Mahindra", "Automobile"),
    ("TATAMOTORS", "Tata Motors", "Automobile"),
    ("TATASTEEL", "Tata Steel", "Metals"),
    ("JSWSTEEL", "JSW Steel", "Metals"),
    ("ADANIENT", "Adani Enterprises", "Conglomerate"),
    ("ADANIPORTS", "Adani Ports & SEZ", "Infrastructure"),
    ("COALINDIA", "Coal India", "Metals/Mining"),
    ("BAJAJFINSV", "Bajaj Finserv", "NBFC"),
    ("HDFCLIFE", "HDFC Life Insurance", "Insurance"),
    ("SBILIFE", "SBI Life Insurance", "Insurance"),
    ("GRASIM", "Grasim Industries", "Cement"),
    ("BRITANNIA", "Britannia Industries", "FMCG"),
    ("DRREDDY", "Dr. Reddy's Laboratories", "Pharma"),
    ("CIPLA", "Cipla", "Pharma"),
    ("DIVISLAB", "Divi's Laboratories", "Pharma"),
    ("EICHERMOT", "Eicher Motors", "Automobile"),
    ("HEROMOTOCO", "Hero MotoCorp", "Automobile"),
    ("BAJAJ-AUTO", "Bajaj Auto", "Automobile"),
    ("INDUSINDBK", "IndusInd Bank", "Banking"),
    ("TECHM", "Tech Mahindra", "IT"),
    ("TATACONSUM", "Tata Consumer Products", "FMCG"),
    ("APOLLOHOSP", "Apollo Hospitals", "Healthcare"),
    ("BPCL", "Bharat Petroleum", "Energy"),
    ("HINDALCO", "Hindalco Industries", "Metals"),
    ("UPL", "UPL", "Chemicals"),
    ("LTIM", "LTIMindtree", "IT"),
]

_INDICES: list[tuple[str, str, str]] = [
    ("NIFTY", "NIFTY 50 Index", "Index"),
    ("BANKNIFTY", "NIFTY Bank Index", "Index"),
    ("FINNIFTY", "NIFTY Financial Services", "Index"),
    ("INDIAVIX", "India VIX", "Volatility"),
]

STOCKS: list[StockMeta] = [StockMeta(s, n, sec) for s, n, sec in _NIFTY50]
INDICES: list[StockMeta] = [StockMeta(s, n, sec, instrument="INDEX") for s, n, sec in _INDICES]
_BY_SYMBOL = {m.symbol: m for m in STOCKS + INDICES}


def load_universe(include_indices: bool = True) -> list[StockMeta]:
    return STOCKS + INDICES if include_indices else list(STOCKS)


def get_stock(symbol: str) -> StockMeta:
    s = symbol.upper().strip()
    if s in _BY_SYMBOL:
        return _BY_SYMBOL[s]
    # unknown symbol → assume a plain NSE equity so the data path still works
    return StockMeta(s, s, "Unknown")


def list_sectors() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in STOCKS:
        out.setdefault(m.sector, []).append(m.symbol)
    return dict(sorted(out.items()))


def persist_universe(engine) -> int:
    """Upsert the catalog into the `symbols` table (docs/006). Returns rows written."""
    from astroquant.db import repo
    from astroquant.db.session import session_scope

    n = 0
    with session_scope(engine) as s:
        for m in load_universe():
            repo.get_or_create_symbol(s, m.symbol, m.exchange, m.instrument)
            n += 1
    return n
