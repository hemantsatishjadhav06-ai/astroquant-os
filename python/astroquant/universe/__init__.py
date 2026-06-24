"""
Stock universe — the full Indian instrument database the analysis runs over.

Bundled exchange masters: **NSE equities + BSE equities + MCX commodities** (~7,000+ instruments),
each with its resolved Yahoo ticker so the free data path works for any of them. Refresh the masters
with ``scripts/fetch_universe.py``. Survivorship-aware by design (entries can carry an active flag).
"""
from astroquant.universe.catalog import (
    INDICES,
    StockMeta,
    get_stock,
    list_sectors,
    load_universe,
    persist_universe,
    resolve_yahoo,
    search,
    universe_stats,
)

__all__ = [
    "StockMeta", "INDICES", "load_universe", "get_stock", "resolve_yahoo",
    "list_sectors", "persist_universe", "universe_stats", "search",
]
