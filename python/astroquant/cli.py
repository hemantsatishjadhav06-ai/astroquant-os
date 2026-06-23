"""AstroQuant CLI.  Usage:  PYTHONPATH=python python3 -m astroquant.cli <command>"""
from __future__ import annotations

import uuid
from datetime import date, datetime

import typer

from astroquant.agents.base import RunContext
from astroquant.collectors.astronomy import AstronomyCollector
from astroquant.collectors.market import MarketCollector
from astroquant.common.config import get_settings

app = typer.Typer(add_completion=False, help="AstroQuant OS research lab CLI")


def _rid() -> str:
    return uuid.uuid4().hex[:12]


@app.command()
def astro(start: str, end: str = "") -> None:
    """Run the Astronomy collector for a date range (YYYY-MM-DD)."""
    s = date.fromisoformat(start)
    e = date.fromisoformat(end) if end else s
    col = AstronomyCollector(ayanamsa=get_settings().ayanamsa)
    res = col.run(RunContext(run_id=_rid(), start=s, end=e))
    typer.echo(f"{res.status}: {res.rows_written} planet-rows. manifest={res.manifest_path}")


@app.command()
def market(symbols: str = "NIFTY", start: str = "", end: str = "") -> None:
    """Run the Market collector (default source from config; yfinance fallback)."""
    cfg = get_settings()
    s = date.fromisoformat(start) if start else date.today()
    e = date.fromisoformat(end) if end else s
    col = MarketCollector(source=cfg.broker, interval="1d")
    res = col.run(RunContext(run_id=_rid(), start=s, end=e, symbols=symbols.split(",")))
    typer.echo(f"{res.status}: {res.rows_written} bars. manifest={res.manifest_path}")


@app.command()
def health() -> None:
    """Healthcheck all wired agents."""
    for agent in (AstronomyCollector(), MarketCollector(source=get_settings().broker)):
        h = agent.healthcheck()
        typer.echo(f"{agent.name:<22} ok={h.ok}  {h.detail}")


if __name__ == "__main__":
    app()
