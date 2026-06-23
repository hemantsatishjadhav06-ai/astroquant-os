# Document 001 — Founder Vision

## Mission
Build a rigorous research laboratory that lets *data* decide whether non-standard signals —
Vedic-astronomical, Gann, sentiment, options-flow, cycle, and macro — carry real predictive edge in
Indian markets, instead of assuming the answer in either direction.

## Vision
A reproducible, self-auditing platform where any claim ("Jupiter–Saturn angle predicts sector
rotation," "Gann 90-day cycles call reversals") is tested with the same statistical discipline a
hedge-fund research desk would demand — and where an honest "no edge" is as valuable as a discovery.

## Market opportunity
- Indian retail quant is exploding but is dominated by overfit backtests and untested "astro/Gann" lore.
- There is genuine, underexploited value in *cleanly testing* sentiment, options-flow, and cycle signals on NSE/BSE/MCX.
- The differentiated asset here is **methodological credibility**, not another indicator.

## Competitive landscape
- Retail tools (TradingView scripts, astro-trading courses): assume signals work; no out-of-sample rigor.
- Institutional quant: rigorous but closed, and uninterested in astro/Gann.
- AstroQuant's niche: institutional rigor applied to the exact hypotheses retail believes but never properly tests.

## Success metrics
- A working pipeline that produces reproducible, corrected, out-of-sample verdicts.
- A growing `discoveries` ledger of tested hypotheses (pass and fail) with full provenance.
- At least one signal family cleanly characterized (edge / no-edge / conditional) with DSR and regime analysis.
- Paper-trading forward results consistent with backtests over 6–12 months.

## Failure conditions (named so they can be avoided)
- "Discovering" edges that vanish out-of-sample (overfitting) — mitigated by `007`.
- Look-ahead/survivorship/vintage bugs — mitigated by `005`/`006` rules + Agent 15.
- Scope creep into live trading before gates pass.
- A 3,000-page spec that never ships — mitigated by the lean build order in `013`.

## Economic moat
Reproducibility + an accumulating, denominator-preserving discoveries ledger. Over time the platform
*knows what's already been tested and ruled out*, which compounds: each new test is cheaper and the
multiple-testing accounting stays honest. That institutional memory is hard to copy.

## Long-term roadmap (beyond v1)
Broaden universe and horizons → add execution-quality research → (only behind compliance + G5) a
narrow, well-characterized live allocation → optionally, a credible research product/newsletter built
on the ledger's authority.

---

# Document 002 — Product Requirements (PRD)

## Primary user
A single technically-capable researcher (you) operating the lab; later, a small team. Not a consumer app.

## Scope boundaries (v1)
- **In:** data collection, warehouse, feature factory, research engine, backtesting, paper trading, reporting, audit.
- **Out:** live order placement, client advisory, mobile app, monetized product surface. (All deferred.)

## Core features
1. **Automated daily data refresh** across market, options, astro, Gann, news, macro.
2. **Point-in-time feature store** (1000+ features/symbol/day, family-tagged).
3. **Hypothesis registry** with pre-registration and locked train/val/test splits.
4. **Research engine** running the baseline→augmented→ablation→correction→verdict protocol.
5. **Backtester** with event-driven realism, walk-forward, Monte Carlo, DSR/PBO.
6. **Paper-trading backend** (first-class) with realistic fills, costs, ledger, attribution.
7. **Risk manager** enforcing limits across backtest and paper.
8. **Daily research report** with honest framing (nulls shown), ranked candidates, paper P&L, risk status.
9. **Anomaly detection** across all feeds.
10. **Full reproducibility** via run manifests, dataset hashes, code commits, seeds.

## Research features
- Register/track RQs; auto-apply FDR/DSR across the RQ family.
- Feature ablation + SHAP attribution to isolate astro/Gann contribution (answers RQ-004).
- Regime and subsample stability analysis.
- Discoveries ledger with dedup (Vector DB) to prevent re-testing.

## Trading features (research/paper only)
- Strategy spec → backtest → paper, all gated.
- Post-cost performance everywhere (India charges modeled).
- No live execution path in v1.

## AI features
- LLM-assisted research narration (Agent 8/14) — summarizes, never decides significance.
- Sentiment extraction (bullish/bearish/neutral) with versioned models.
- Optional LLM-assisted hypothesis generation, always funneled through the correction machinery.

## Dashboard / reporting features
- Daily/weekly Markdown/HTML/PDF reports (pushed via n8n).
- Equity curves, drawdown, attribution by family/symbol/strategy.
- Live-vs-backtest tracking; decay alerts.

## Non-functional requirements
- Reproducibility, idempotency, point-in-time correctness (hard requirements, per `000` §6).
- Operability: a single operator can run, monitor, and debug the system.
- Cost-consciousness: prefer free/low-cost data where research-grade; document where paid data is worth it.
