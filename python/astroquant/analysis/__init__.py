"""
Per-stock deep analysis — the unified view that combines all three ideas for a single name:
technical + Gann + astrology + a rigorous backtest, plus an LLM-ready analyst narrative.
"""
from astroquant.analysis.narrative import generate_narrative, llm_available
from astroquant.analysis.stock import StockReport, analyze_stock

__all__ = ["StockReport", "analyze_stock", "generate_narrative", "llm_available"]
