"""
Evolutionary strategy search for the Self-Evolving Hedge Fund.

A genetic algorithm over ``StrategyGenome``s. Fitness = **post-cost Deflated Sharpe** on the held-out
slice, *deflated by the number of strategies evaluated so far* — so breeding thousands of variants
raises the bar instead of guaranteeing a winner (docs/007 §4). Deterministic given a seed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from astroquant.agents.base import get_logger
from astroquant.features.factory import FeatureMatrix
from astroquant.fund.strategy import GENE_FAMILIES, StrategyGenome
from astroquant.paper.engine import run_paper_trade

log = get_logger("fund.evolve")

_BANDS = (0.0, 0.01, 0.02, 0.03)
_L2S = (0.3, 1.0, 3.0)


@dataclass
class EvolutionResult:
    best_label: str
    best_families: list[str]
    best_prob_band: float
    best_l2: float
    best_fitness: float
    best_deflated_sharpe: float
    best_total_return: float
    generations: int
    n_evaluated: int
    history: list[dict]            # per-generation best
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _random_genome(rng: np.random.Generator) -> StrategyGenome:
    k = int(rng.integers(1, len(GENE_FAMILIES) + 1))
    fams = tuple(sorted(rng.choice(GENE_FAMILIES, size=k, replace=False).tolist()))
    return StrategyGenome(families=fams, prob_band=float(rng.choice(_BANDS)), l2=float(rng.choice(_L2S)))


def _mutate(g: StrategyGenome, rng: np.random.Generator) -> StrategyGenome:
    fams = set(g.families)
    if rng.random() < 0.6:
        fam = str(rng.choice(GENE_FAMILIES))
        fams.symmetric_difference_update({fam})
    if not fams:
        fams = {str(rng.choice(GENE_FAMILIES))}
    band = float(rng.choice(_BANDS)) if rng.random() < 0.5 else g.prob_band
    l2 = float(rng.choice(_L2S)) if rng.random() < 0.5 else g.l2
    return StrategyGenome(families=tuple(sorted(fams)), prob_band=band, l2=l2)


def _crossover(a: StrategyGenome, b: StrategyGenome, rng: np.random.Generator) -> StrategyGenome:
    fams = {f for f in set(a.families) | set(b.families) if rng.random() < 0.5}
    if not fams:
        fams = set(a.families) or set(b.families)
    band = a.prob_band if rng.random() < 0.5 else b.prob_band
    l2 = a.l2 if rng.random() < 0.5 else b.l2
    return StrategyGenome(families=tuple(sorted(fams)), prob_band=band, l2=l2)


def evolve_strategies(
    fm: FeatureMatrix,
    *,
    generations: int = 5,
    pop_size: int = 10,
    capital: float = 1_000_000.0,
    seed: int = 7,
) -> EvolutionResult:
    rng = np.random.default_rng(seed)
    split = int(len(fm.y) * 0.6)
    fwd, dates = fm.fwd_return[split:], fm.dates[split:]
    cache: dict[str, tuple[float, float, float]] = {}
    n_eval = 0

    def fitness(g: StrategyGenome) -> tuple[float, float, float]:
        nonlocal n_eval
        fp = g.fingerprint()
        if fp in cache:
            return cache[fp]
        n_eval += 1
        pos = g.fit_positions(fm, split)
        paper = run_paper_trade([], pos, fwd, dates, capital=capital, n_prior_trials=n_eval)
        # complexity penalty discourages kitchen-sink genomes
        fit = paper.deflated_sharpe - 0.02 * len(g.families)
        cache[fp] = (fit, paper.deflated_sharpe, paper.total_return)
        return cache[fp]

    population = []
    seen: set[str] = set()
    while len(population) < pop_size:
        g = _random_genome(rng)
        if g.fingerprint() not in seen:
            seen.add(g.fingerprint())
            population.append(g)

    best: tuple[StrategyGenome, tuple[float, float, float]] | None = None
    history: list[dict] = []
    for gen in range(generations):
        scored = sorted(((g, fitness(g)) for g in population), key=lambda t: -t[1][0])
        if best is None or scored[0][1][0] > best[1][0]:
            best = scored[0]
        history.append({"generation": gen + 1, "best_fitness": round(scored[0][1][0], 4),
                        "best_label": scored[0][0].label, "evaluated": n_eval})
        log.info("fund[gen %d]: best=%s fitness=%.3f (evaluated=%d)",
                 gen + 1, scored[0][0].label, scored[0][1][0], n_eval)
        # next generation: elitism + offspring of the top half
        elites = [g for g, _ in scored[:2]]
        parents = [g for g, _ in scored[: max(2, pop_size // 2)]]
        children: list[StrategyGenome] = []
        while len(elites) + len(children) < pop_size:
            a, b = rng.choice(len(parents), size=2, replace=True)
            children.append(_mutate(_crossover(parents[a], parents[b], rng), rng))
        population = elites + children

    assert best is not None
    g, (fit, dsr, tot) = best
    return EvolutionResult(
        best_label=g.label, best_families=list(g.families), best_prob_band=g.prob_band, best_l2=g.l2,
        best_fitness=round(fit, 4), best_deflated_sharpe=round(dsr, 4), best_total_return=round(tot, 4),
        generations=generations, n_evaluated=n_eval, history=history,
        meta={"pop_size": pop_size, "note": "fitness = post-cost Deflated Sharpe deflated by #evaluated"},
    )
