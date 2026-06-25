"""
FastAPI service for the Autonomous Alpha Discovery Lab.

Endpoints
  GET  /healthz            liveness probe (Render health check)
  GET  /                   live HTML dashboard (run the lab, see the leaderboard)
  POST /lab/run            run a discovery round -> LabReport JSON
  GET  /discoveries        the discoveries ledger from the DB (JSON)
  GET  /astro/{date}       sidereal planetary positions for a date (engine demo)

Run locally:  PYTHONPATH=python uvicorn astroquant.api.app:app --reload
Run on Render: uvicorn astroquant.api.app:app --host 0.0.0.0 --port $PORT   (after pip install -e .)

NOTE ON SECRETS: this service reads all configuration from environment variables
(AQ_DB_URL, AQ_BROKER, …). Never hard-code API keys/tokens; set them as Render env vars.
"""
from __future__ import annotations

from datetime import date

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from astroquant.agents.base import get_logger
from astroquant.api.dashboard import DASHBOARD_HTML
from astroquant.lab import DiscoveryLab

log = get_logger("api")
app = FastAPI(title="AstroQuant OS — Autonomous Alpha Discovery Lab", version="0.3.0")

_STATE: dict = {"last_report": None}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "astroquant-os", "version": "0.2.0"}


@app.get("/astro/{d}")
def astro(d: str) -> dict:
    from astroquant.collectors.astronomy import AstronomyCollector

    rows = AstronomyCollector().planets_for_date(date.fromisoformat(d))
    return {"date": d, "planets": [r.__dict__ for r in rows]}


@app.post("/lab/run")
def lab_run(
    symbols: str = Query("NIFTY,BANKNIFTY"),
    source: str = Query("nse", pattern="^(nse|bse|synthetic|yfinance)$"),
    start: str = Query("2019-01-01"),
    end: str = Query("2024-12-31"),
    rounds: int = Query(1, ge=1, le=3),
    permutations: int = Query(10, ge=4, le=40),
) -> JSONResponse:
    """Run the Collect→Hypotheses→Backtest→Validate→Rank→Learn loop and return the leaderboard."""
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()][:5]
    lab = DiscoveryLab(
        syms, source=source, start=date.fromisoformat(start), end=date.fromisoformat(end),
        persist=True, k_folds=4, n_permutations=permutations,
    )
    report = lab.run(rounds=rounds, learn=(rounds > 1))
    _STATE["last_report"] = report
    log.info("api: lab run complete — %d tested, %d survivors", report.total_tested, report.n_survivors)
    return JSONResponse(report.to_dict())


@app.get("/discoveries")
def discoveries(limit: int = Query(50, ge=1, le=500)) -> dict:
    try:
        from astroquant.db import repo
        from astroquant.db.session import get_engine, init_db, session_scope

        eng = get_engine()
        init_db(eng)
        with session_scope(eng) as s:
            return {"discoveries": repo.list_signals(s, limit=limit)}
    except Exception as e:  # noqa: BLE001
        return {"discoveries": [], "error": str(e)}


@app.post("/genome/run")
def genome_run(
    symbol: str = Query("NIFTY"),
    source: str = Query("nse", pattern="^(nse|bse|synthetic|yfinance)$"),
    start: str = Query("2017-01-01"),
    end: str = Query("2024-12-31"),
) -> JSONResponse:
    """Market Genome (Idea 2): test condition→outcome relationships, return graded findings + graph."""
    from astroquant.genome import KnowledgeGraph, run_genome

    rep = run_genome(symbol, source=source, start=date.fromisoformat(start), end=date.fromisoformat(end))
    g = KnowledgeGraph.from_report(rep)
    out = rep.to_dict()
    out["mermaid"] = g.to_mermaid()
    out["graph"] = g.to_dict()
    return JSONResponse(out)


@app.post("/fund/evolve")
def fund_evolve(
    symbol: str = Query("NIFTY"),
    source: str = Query("nse", pattern="^(nse|bse|synthetic|yfinance)$"),
    start: str = Query("2016-01-01"),
    end: str = Query("2024-12-31"),
    generations: int = Query(4, ge=1, le=10),
    pop: int = Query(8, ge=4, le=24),
) -> JSONResponse:
    """Self-Evolving Hedge Fund (Idea 3): evolve → validate → paper portfolio + risk report."""
    from astroquant.fund import run_fund

    res = run_fund(symbol, source=source, start=date.fromisoformat(start), end=date.fromisoformat(end),
                   generations=generations, pop_size=pop)
    return JSONResponse(res.to_dict())


@app.get("/universe")
def universe(
    q: str = Query("", description="search symbol or name"),
    exchange: str = Query("", pattern="^(NSE|BSE|MCX|INDEX|)$"),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """Full Indian instrument universe (NSE + BSE + MCX), searchable. Returns counts + matches."""
    from astroquant.universe import search, universe_stats

    matches = search(q, exchange or None, limit)
    return {
        "stats": universe_stats(),
        "count": len(matches),
        "stocks": [{"symbol": m.symbol, "name": m.name, "sector": m.sector,
                    "exchange": m.exchange, "yahoo": m.yahoo_ticker} for m in matches],
    }


@app.post("/stock/analyze")
def stock_analyze(
    symbol: str = Query("RELIANCE"),
    source: str = Query("nse", pattern="^(nse|bse|synthetic|yfinance)$"),
    years: int = Query(6, ge=2, le=12),
    narrative: bool = Query(True),
) -> JSONResponse:
    """Deep dive: technical + Gann + astrology + backtest + analyst narrative for one symbol."""
    from astroquant.analysis import analyze_stock, generate_narrative, llm_available

    rep = analyze_stock(symbol, source=source, years=years, n_permutations=10)
    out = rep.to_dict()
    if narrative:
        out["narrative"] = generate_narrative(rep)
        out["narrative_source"] = llm_available() or "built-in"
    return JSONResponse(out)


@app.get("/chart")
def chart(
    symbol: str = Query("RELIANCE"),
    source: str = Query("nse", pattern="^(nse|bse|mcx|synthetic|yfinance)$"),
    interval: str = Query("1d", pattern="^(1d|1wk|1mo)$"),
    years: int = Query(2, ge=1, le=10),
) -> JSONResponse:
    """OHLC candles + technical indicators (SMA/EMA/Bollinger/RSI/MACD) + Gann levels for charting."""
    from astroquant.analysis.chart import build_chart

    return JSONResponse(build_chart(symbol, source=source, interval=interval, years=years))


@app.post("/options/signal")
def options_signal(
    symbol: str = Query("NIFTY"),
    source: str = Query("nse", pattern="^(nse|bse|synthetic|yfinance)$"),
    capital: float = Query(1_000_000.0, ge=50_000, le=1_000_000_000),
    risk_pct: float = Query(0.015, ge=0.001, le=0.1),
    live_chain: bool = Query(False),
    final_hour: bool = Query(False),
) -> JSONResponse:
    """Options Greeks Engine: current vol regime → structure → risk-sized order intents + triggers."""
    from astroquant.strategies.options_greeks import generate_options_signal

    sig = generate_options_signal(symbol, source=source, capital=capital, risk_pct=risk_pct,
                                  live_chain=live_chain, final_hour=final_hour)
    return JSONResponse(sig.to_dict())


@app.post("/options/backtest")
def options_backtest(
    symbol: str = Query("NIFTY"),
    source: str = Query("synthetic", pattern="^(nse|bse|synthetic|yfinance)$"),
    years: int = Query(6, ge=2, le=12),
) -> JSONResponse:
    """Backtest the options strategy (weekly cycles, costs included) → §11 metrics."""
    from astroquant.strategies.options_greeks.backtest import run_options_backtest

    return JSONResponse(run_options_backtest(symbol, source=source, years=years).to_dict())


@app.get("/options/chain")
def options_chain(
    symbol: str = Query("NIFTY"),
    source: str = Query("nse", pattern="^(nse|bse|synthetic|yfinance)$"),
    live: bool = Query(True),
) -> JSONResponse:
    """Collect the option chain (live NSE when reachable, else synthetic) with Greeks per strike."""
    from astroquant.collectors.sources.market_sources import get_source
    from astroquant.strategies.options_greeks.chain import get_chain

    spot = None
    if not live or source != "nse":
        kw = {"fallback_synthetic": True} if source in ("nse", "bse") else {}
        bars = get_source(source, **kw).history(symbol, "1d",
                                                __import__("datetime").date(2024, 1, 1),
                                                __import__("datetime").date.today())
        spot = bars[-1].close if bars else 20000.0
    chain = get_chain(symbol, spot, live=(live and source == "nse"))
    d = chain.to_dict()
    d["quotes"] = d["quotes"][:24]  # trim payload
    return JSONResponse(d)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return DASHBOARD_HTML
