"""
The Discovery Lab orchestrator — the continuous loop (docs/000 §5).

    Collect → Generate Hypotheses → Backtest → Validate → Rank → Learn → Repeat

Each hypothesis is run through the full research protocol (walk-forward, ablation, sanity guards,
multiple-testing deflation) and forward-validated through the paper-trading gate. Every test
increments a global comparison counter that deflates all subsequent statistics. Results are written
to the discoveries/`signals` ledger so the denominator (how many things were tried) is never lost.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

from astroquant.agents.base import get_logger
from astroquant.collectors.sources.market_sources import get_source
from astroquant.features.factory import FeatureFactory, FeatureMatrix
from astroquant.lab.hypothesis import HypothesisSpec, generate_hypotheses
from astroquant.lab.ranking import rank_discoveries
from astroquant.paper.engine import positions_from_probabilities, run_paper_trade
from astroquant.research.engine import run_protocol
from astroquant.research.model import LogisticModel

log = get_logger("lab.orchestrator")


@dataclass
class Discovery:
    hypothesis_id: str
    symbol: str
    source: str
    trial_families: list[str]
    statement: str
    verdict: str
    baseline_auc: float
    augmented_auc: float
    incremental_lift: float
    p_raw: float
    p_adj: float
    dsr: float
    sharpe: float
    max_drawdown: float
    total_return: float
    n_comparisons: int
    q_value: float = 1.0
    survived: bool = False
    rank: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LabReport:
    rounds: int
    symbols: list[str]
    source: str
    total_tested: int
    n_survivors: int
    leaderboard: list[Discovery]
    all_discoveries: list[Discovery]
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


class DiscoveryLab:
    def __init__(
        self,
        symbols: list[str],
        source: str = "nse",
        *,
        start: date = date(2016, 1, 1),
        end: date = date(2024, 12, 31),
        persist: bool = True,
        db_url: str | None = None,
        k_folds: int = 4,
        n_permutations: int = 12,
        seed: int = 7,
    ) -> None:
        self.symbols = symbols
        self.source = source
        self.start = start
        self.end = end
        self.k_folds = k_folds
        self.n_permutations = n_permutations
        self.seed = seed
        self._bars: dict[str, list] = {}
        self._fm: dict[str, FeatureMatrix] = {}
        self._counter = 0                       # global multiple-testing denominator
        self._engine = None
        if persist:
            try:
                from astroquant.db.session import get_engine, init_db

                self._engine = get_engine(db_url)
                init_db(self._engine)
            except Exception as e:  # noqa: BLE001 — persistence is best-effort
                log.warning("lab: persistence disabled (%s)", e)

    # --- Collect (cached per symbol) ---
    def _collect(self, spec: HypothesisSpec) -> tuple[list, FeatureMatrix]:
        if spec.symbol not in self._fm:
            kwargs = {"fallback_synthetic": True} if self.source in ("nse", "bse") else {}
            src = get_source(self.source, **kwargs)
            bars = src.history(spec.symbol, "1d", self.start, self.end)
            self._bars[spec.symbol] = bars
            self._fm[spec.symbol] = FeatureFactory(warmup=25, use_astro=True, use_gann=True).build(bars)
            log.info("lab: collected %d bars + features for %s", len(bars), spec.symbol)
        return self._bars[spec.symbol], self._fm[spec.symbol]

    # --- Backtest + Validate one hypothesis ---
    def evaluate(self, spec: HypothesisSpec) -> Discovery:
        bars, fm = self._collect(spec)
        self._counter += 1
        report = run_protocol(
            fm, spec.id,
            baseline_families=spec.baseline_families, augmented_families=spec.augmented_families,
            k_folds=self.k_folds, n_permutations=self.n_permutations,
            n_prior_trials=self._counter, seed=42,
        )
        # Forward-validate: train on first 60%, paper-trade the held-out 40% post-cost.
        split = int(len(fm.y) * 0.6)
        X = fm.subset(spec.augmented_families)
        model = LogisticModel(l2=1.0, lr=0.2, n_iter=400).fit(X[:split], fm.y[:split])
        probs = model.predict_proba(X[split:])
        pos = positions_from_probabilities(probs, long_short=True, band=spec.prob_band)
        paper = run_paper_trade(bars, pos, fm.fwd_return[split:], fm.dates[split:],
                                n_prior_trials=self._counter)

        disc = Discovery(
            hypothesis_id=spec.id, symbol=spec.symbol, source=self.source,
            trial_families=list(spec.trial_families), statement=spec.statement,
            verdict=report.verdict, baseline_auc=report.baseline_auc,
            augmented_auc=report.augmented_auc, incremental_lift=report.incremental_lift,
            p_raw=report.p_raw, p_adj=report.p_adj, dsr=paper.deflated_sharpe,
            sharpe=paper.sharpe, max_drawdown=paper.max_drawdown, total_return=paper.total_return,
            n_comparisons=self._counter,
        )
        self._persist(disc)
        return disc

    def _persist(self, d: Discovery) -> None:
        if not self._engine:
            return
        try:
            from astroquant.db import repo
            from astroquant.db.session import session_scope

            with session_scope(self._engine) as s:
                repo.record_signal(
                    s, name=d.hypothesis_id, family=",".join(d.trial_families),
                    verdict=d.verdict, effect_size=d.incremental_lift,
                    p_raw=d.p_raw, p_adj=d.p_adj, n_comparisons=d.n_comparisons, dsr=d.dsr,
                )
        except Exception as e:  # noqa: BLE001
            log.warning("lab: failed to persist %s (%s)", d.hypothesis_id, e)

    # --- Learn: refocus the next round on the most promising family ---
    def _learn_next(self, ranked: list[Discovery]) -> list[HypothesisSpec]:
        best = {}
        for d in ranked:
            key = "+".join(d.trial_families)
            best.setdefault(key, []).append(d.incremental_lift)
        if not best:
            return []
        top_family = max(best, key=lambda k: sum(best[k]) / len(best[k]))
        tf = tuple(top_family.split("+"))
        log.info("lab[learn]: refocusing on family '%s' with finer decision bands", top_family)
        return generate_hypotheses(
            self.symbols, self.source, trial_sets=(tf,),
            prob_bands=(0.0, 0.01, 0.02, 0.03), start_index=self._counter + 1,
        )

    # --- the loop ---
    def run(self, rounds: int = 1, learn: bool = True,
            hypotheses: list[HypothesisSpec] | None = None) -> LabReport:
        specs = hypotheses or generate_hypotheses(self.symbols, self.source)
        all_disc: list[Discovery] = []
        for r in range(rounds):
            log.info("lab: === round %d/%d — %d hypotheses ===", r + 1, rounds, len(specs))
            for spec in specs:
                all_disc.append(self.evaluate(spec))
            ranked = rank_discoveries(all_disc)
            if learn and r < rounds - 1:
                specs = self._learn_next(ranked)
                if not specs:
                    break
        leaderboard = rank_discoveries(all_disc)
        survivors = [d for d in leaderboard if d.survived]
        return LabReport(
            rounds=rounds, symbols=self.symbols, source=self.source,
            total_tested=self._counter, n_survivors=len(survivors),
            leaderboard=leaderboard[:10], all_discoveries=leaderboard,
            meta={"start": self.start.isoformat(), "end": self.end.isoformat(),
                  "k_folds": self.k_folds, "n_permutations": self.n_permutations,
                  "note": "every statistic is deflated by total_tested (the comparison denominator)"},
        )
