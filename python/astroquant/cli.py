"""AstroQuant CLI.  Usage:  PYTHONPATH=python python3 -m astroquant.cli <command>"""
from __future__ import annotations

import uuid
from datetime import date

import typer

from astroquant.agents.base import RunContext
from astroquant.collectors.astronomy import AstronomyCollector
from astroquant.collectors.gann import GannCollector
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
    """Run the Market collector (default source from config; yfinance/synthetic fallback)."""
    cfg = get_settings()
    s = date.fromisoformat(start) if start else date.today()
    e = date.fromisoformat(end) if end else s
    col = MarketCollector(source=cfg.broker, interval="1d")
    res = col.run(RunContext(run_id=_rid(), start=s, end=e, symbols=symbols.split(",")))
    typer.echo(f"{res.status}: {res.rows_written} bars. manifest={res.manifest_path}")


@app.command()
def gann(anchor: str, price: float = 100.0, days_out: int = 90) -> None:
    """Run the Gann collector from an anchor pivot date+price (Square-of-Nine + time cycles)."""
    col = GannCollector(points_per_day=1.0)
    ctx = RunContext(run_id=_rid(), start=date.fromisoformat(anchor),
                     config={"anchor_price": price, "days_out": days_out})
    res = col.run(ctx)
    typer.echo(f"{res.status}: {res.metrics['levels']} Sq9 levels + "
               f"{res.metrics['cycles']} time-cycles. manifest={res.manifest_path}")


@app.command()
def research(
    symbol: str = "NIFTY", start: str = "2014-01-01", end: str = "2023-12-31",
    source: str = "synthetic", trials: int = 1,
) -> None:
    """Run the baseline→augmented→ablation→verdict protocol for a hypothesis (default RQ-004)."""
    from astroquant.research.pipeline import run_full_pipeline

    out = run_full_pipeline(symbol, date.fromisoformat(start), date.fromisoformat(end),
                            source=source, n_prior_trials=trials)
    r = out.report
    typer.echo(f"\n  Hypothesis RQ-004 — does astro+gann beat technical+market for next-day {symbol}?")
    typer.echo(f"  baseline AUC = {r.baseline_auc:.3f}   augmented AUC = {r.augmented_auc:.3f}   "
               f"lift = {r.incremental_lift:+.3f}")
    typer.echo(f"  shuffle-label: {'real signal' if r.shuffle_label_pass else 'no edge (null)'}   "
               f"random-feature: {'pass' if r.random_feature_pass else 'FAIL'}   "
               f"p_adj = {r.p_adj:.4f}")
    typer.echo(f"  paper-trade post-cost: return {out.paper.total_return*100:+.2f}%  "
               f"Sharpe {out.paper.sharpe:.2f}  DSR {out.paper.deflated_sharpe:.2f}  "
               f"maxDD {out.paper.max_drawdown*100:.1f}%")
    typer.secho(f"  VERDICT: {r.verdict}\n", fg=typer.colors.GREEN if r.verdict == "edge"
                else (typer.colors.YELLOW if r.verdict == "conditional_edge" else typer.colors.BLUE))


@app.command()
def pipeline(
    symbol: str = "NIFTY", start: str = "2014-01-01", end: str = "2023-12-31",
    source: str = "synthetic", out: str = "research_report.html",
) -> None:
    """Full vertical slice → writes a self-contained HTML research report you can open."""
    from astroquant.research.pipeline import run_full_pipeline
    from astroquant.research.report import write_html_report

    output = run_full_pipeline(symbol, date.fromisoformat(start), date.fromisoformat(end), source=source)
    write_html_report(output, out)
    typer.echo(f"verdict={output.report.verdict}  →  wrote {out}")


@app.command()
def lab(
    symbols: str = "NIFTY,BANKNIFTY", source: str = "synthetic",
    start: str = "2018-01-01", end: str = "2023-12-31",
    rounds: int = 1, permutations: int = 10,
) -> None:
    """Autonomous Alpha Discovery Lab: Collect→Hypotheses→Backtest→Validate→Rank→Learn→Repeat."""
    from astroquant.lab import DiscoveryLab

    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    dl = DiscoveryLab(syms, source=source, start=date.fromisoformat(start),
                      end=date.fromisoformat(end), n_permutations=permutations)
    rep = dl.run(rounds=rounds, learn=(rounds > 1))
    typer.echo(f"\n  Tested {rep.total_tested} hypotheses · {rep.n_survivors} survived "
               f"(source={source}, symbols={','.join(syms)})")
    typer.echo(f"  {'#':>2} {'hyp':>7} {'symbol':<10} {'family':<11} {'verdict':<15} "
               f"{'lift':>7} {'q':>6} {'DSR':>6}")
    for d in rep.leaderboard:
        typer.echo(f"  {d.rank:>2} {d.hypothesis_id:>7} {d.symbol:<10} "
                   f"{'+'.join(d.trial_families):<11} {d.verdict:<15} "
                   f"{d.incremental_lift:>+7.3f} {d.q_value:>6.3f} {d.dsr:>6.2f}")
    if rep.n_survivors == 0:
        typer.secho("  No validated edges — the lab refused to certify noise (correct null).",
                    fg=typer.colors.BLUE)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the FastAPI dashboard/API locally (uvicorn)."""
    import uvicorn

    uvicorn.run("astroquant.api.app:app", host=host, port=port)


@app.command()
def health() -> None:
    """Healthcheck all wired agents."""
    agents = (
        AstronomyCollector(),
        MarketCollector(source=get_settings().broker),
        GannCollector(),
    )
    for agent in agents:
        h = agent.healthcheck()
        typer.echo(f"{agent.name:<22} ok={h.ok}  {h.detail}")


if __name__ == "__main__":
    app()
