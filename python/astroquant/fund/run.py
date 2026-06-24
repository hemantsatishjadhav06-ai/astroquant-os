"""End-to-end runner for the Self-Evolving Hedge Fund: collect → evolve → validated paper portfolio."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from astroquant.agents.base import get_logger
from astroquant.collectors.sources.market_sources import get_source
from astroquant.features.factory import FeatureFactory
from astroquant.fund.evolve import EvolutionResult, evolve_strategies
from astroquant.fund.portfolio import RiskReport, build_portfolio
from astroquant.fund.strategy import StrategyGenome

log = get_logger("fund.run")


@dataclass
class FundResult:
    symbol: str
    source: str
    evolution: EvolutionResult
    risk: RiskReport
    meta: dict

    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "source": self.source,
                "evolution": self.evolution.to_dict(), "risk": self.risk.to_dict(), "meta": self.meta}


def run_fund(
    symbol: str = "NIFTY",
    source: str = "nse",
    *,
    start: date = date(2016, 1, 1),
    end: date = date(2024, 12, 31),
    generations: int = 5,
    pop_size: int = 10,
    capital: float = 1_000_000.0,
    validate: bool = True,
    seed: int = 7,
) -> FundResult:
    kwargs = {"fallback_synthetic": True} if source in ("nse", "bse") else {}
    bars = get_source(source, **kwargs).history(symbol, "1d", start, end)
    fm = FeatureFactory(warmup=25, use_astro=True, use_gann=True).build(bars)

    evo = evolve_strategies(fm, generations=generations, pop_size=pop_size, capital=capital, seed=seed)
    best = StrategyGenome(tuple(evo.best_families), prob_band=evo.best_prob_band, l2=evo.best_l2)
    risk = build_portfolio(fm, best, capital=capital, n_prior_trials=evo.n_evaluated, validate=validate)

    log.info("fund[%s]: evolved %s — verdict=%s DSR=%.2f", symbol, evo.best_label,
             risk.research_verdict, risk.deflated_sharpe)
    return FundResult(symbol=symbol, source=source, evolution=evo, risk=risk,
                      meta={"start": start.isoformat(), "end": end.isoformat(),
                            "n_bars": len(bars), "n_samples": int(len(fm.y))})
