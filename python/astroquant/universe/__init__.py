"""
Stock universe — the detailed reference database the analysis runs over.

A curated catalog of major NSE names (NIFTY-50 + key indices) with sector/exchange/Yahoo metadata.
Survivorship-aware by design: entries carry an ``active`` flag so delisted names can be retained later
(docs/006). Extend `catalog.py` or load a fuller master from your broker for the whole exchange.
"""
from astroquant.universe.catalog import (
    INDICES,
    STOCKS,
    StockMeta,
    get_stock,
    list_sectors,
    load_universe,
    persist_universe,
)

__all__ = [
    "StockMeta", "STOCKS", "INDICES", "load_universe", "get_stock",
    "list_sectors", "persist_universe",
]
