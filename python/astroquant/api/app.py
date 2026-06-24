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


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return DASHBOARD_HTML
