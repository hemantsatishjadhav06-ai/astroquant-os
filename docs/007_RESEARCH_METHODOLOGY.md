# Document 007 — Research Methodology

**This is the intellectual heart of AstroQuant OS.** Its entire purpose is to stop the platform from
fooling itself. If you implement everything else perfectly and skip this, you will "discover" edges
that don't exist and lose money proving it. Claude Code must treat the controls below as mandatory
infrastructure, not optional analysis.

---

## 0. The one-sentence mandate
> Find statistically significant, out-of-sample, post-cost predictive ability that survives correction
> for the number of things we tried — and report honest nulls when we don't.

---

## 1. Pre-registration (do this before touching test data)

Every research question is registered **before** the test set is examined. A registered hypothesis record contains:

```json
{
  "id": "RQ-004",
  "statement": "Astro+Gann features add out-of-sample predictive power beyond technical+market features for next-day NIFTY direction.",
  "family_tested": ["astro", "gann"],
  "baseline_families": ["technical", "market"],
  "label": "sign(next_day_return(NIFTY))",
  "horizon": "1d",
  "universe": "NIFTY index",
  "metric": "out-of-sample AUC and strategy Sharpe (post-cost)",
  "train": "2010-01-01..2018-12-31",
  "validation": "2019-01-01..2021-12-31",
  "test": "2022-01-01..2024-12-31",   // touched ONCE
  "success_criteria": "augmented model AUC > baseline AUC, p_adj < 0.05, positive Deflated Sharpe",
  "n_planned_comparisons": 1,
  "registered_at": "...", "registered_by": "...", "status": "registered"
}
```

Rules:
- The **test set is touched exactly once**, at the end, after the model is frozen. Repeatedly peeking at test data is the most common way researchers turn noise into "signal."
- Changing the hypothesis after seeing results = a **new** registration, and the multiple-testing counter increments.
- Stored in Postgres `signals`/hypotheses table + MongoDB `experiments`.

---

## 2. The recurring test protocol (baseline → augmented → ablation → correction → verdict)

This is *the* motif of the platform (also in `000` §5, `009`).

1. **Baseline model:** technical ∪ market features only. This is the control. Its job is to be hard to beat.
2. **Augmented model:** baseline ∪ (astro ∪ gann) [or whichever family is on trial].
3. **Out-of-sample comparison:** compare augmented vs baseline on data neither saw, using a metric tied to the hypothesis (AUC / Information Coefficient / strategy Sharpe).
4. **Ablation:** the *incremental* contribution = augmented − baseline. If astro adds nothing, the difference is ~0 (or negative after the complexity penalty).
5. **Attribution (SHAP):** if there *is* lift, SHAP shows which astro/Gann features drive it — guards against the lift being an artifact.
6. **Multiple-testing correction:** deflate for how many hypotheses/feature-combos were tried (§4).
7. **Verdict:** `edge` only if incremental lift is positive, out-of-sample, post-cost, and survives correction. Else `no_edge_found` (a valid result, recorded in `discoveries`).

---

## 3. Splitting time series correctly (no leakage)

- **Never random-shuffle** time-series rows into train/test. Use **chronological** splits.
- **Embargo/purge** around split boundaries (López de Prado's purged K-fold): drop samples whose label horizon overlaps the boundary so train labels can't peek into test.
- **Walk-forward analysis** is the default evaluation: train on window → test on the next out-of-sample window → roll forward. Aggregate out-of-sample performance across folds.
- **Point-in-time joins only** (enforced by feature store `as_of_ts`). Macro vintages and news publication lags (see `005`) are part of this.

---

## 4. Multiple-hypothesis testing — the astrology trap

**The core danger:** there are countless planetary combinations, Gann cycles, thresholds, and horizons.
Test enough of them and some will look significant purely by chance (test 1000 useless signals at
p<0.05 and ~50 will "pass" by luck). Astro/Gann research is *especially* exposed because the feature
space is effectively unlimited and intuitively generative.

**Controls (all implemented in code, applied automatically):**
- **Count every comparison.** Pattern Discovery (Agent 7) reports `n_comparisons` per batch. Nothing is judged in isolation.
- **FDR control (Benjamini–Hochberg):** control the false-discovery rate across a family of tests, not just per-test α.
- **Family-wise correction (Bonferroni/Holm)** when the claim must be conservative.
- **Data-snooping tests for strategy performance:** White's **Reality Check** and Hansen's **SPA** (Superior Predictive Ability) test whether the best strategy out of many is better than chance.
- **Deflated Sharpe Ratio (Bailey & López de Prado):** adjusts an observed Sharpe for (a) the number of trials, (b) non-normal returns (skew/kurtosis), (c) sample length. Report **DSR**, not raw Sharpe, for any strategy selected from a search.
- **Minimum Backtest Length / PBO:** estimate the Probability of Backtest Overfitting (combinatorially-symmetric cross-validation). High PBO → the "edge" is likely overfit.

> Rule of thumb baked into the verdict logic: a strategy chosen from N trials must clear a Sharpe bar
> that *rises with N*. The DSR encodes this automatically. If you tried 500 planetary signals, the one
> with Sharpe 1.2 is probably noise.

---

## 5. Correlation vs causality

- Correlation found in-sample is a *hypothesis*, not a finding.
- Require: (a) out-of-sample persistence, (b) a stable mechanism story or at least regime-robustness, (c) survival under correction.
- Be ruthless about **spurious correlation** (two trending series correlate trivially) — difference/stationarize series before correlating; prefer returns over levels.
- For astro especially: a "mechanism" is not required to *use* a feature, but the bar for evidence is correspondingly higher because priors are low. State priors explicitly; let strong out-of-sample evidence move them.

---

## 6. Sanity tests the pipeline must pass (continuously)

These are automated guards run by Agent 13/15:
- **Shuffled-label test:** randomly permute labels; the pipeline must report *no* edge. If it finds one, you have leakage or a bug. Run this regularly.
- **Random-feature test:** inject pure-noise features; they must not rank as important. If they do, the importance method or CV is broken.
- **Future-shift test:** shift a powerful feature one bar into the future; performance should *improve* — confirming the harness can detect leakage, then revert.
- **Regime split:** measure performance separately across bull/bear/high-vol/low-vol/COVID-crash regimes. An edge present in only one regime is fragile; report it as such.
- **Subsample stability:** does the effect hold across random subperiods, sectors, market-cap buckets?

---

## 7. Effect size, costs, and capacity (not just p-values)

- A statistically significant edge that's smaller than transaction costs + slippage + taxes (STT, brokerage, exchange fees, GST) is **not** an edge. All performance is reported **post-cost**.
- Report **effect size and economic significance**, not only significance: expected return per trade, IC, hit rate, and especially **DSR** and **max drawdown**.
- Consider **capacity**: a tiny-universe signal that decays with size matters for any future live step (out of v1 scope but record it).

---

## 8. The discoveries ledger (honest record-keeping)

Every tested hypothesis — pass or fail — is written to `discoveries` (Vector DB + Postgres) with:
`hypothesis_id, verdict, effect_size, p_raw, p_adj, n_comparisons, dsr, pbo, regimes_tested, dataset_hash, code_commit, manifest`.

This ledger:
- prevents re-testing the same idea (dedup via embeddings),
- preserves the **denominator** (how many things were tried) so future corrections stay honest,
- makes "we found astrology doesn't add edge" a first-class, citable result.

---

## 9. How RQ-004 gets answered, concretely

1. Register RQ-004 (§1) with locked splits.
2. Build baseline (technical+market) and augmented (+astro+gann) models (`009`).
3. Walk-forward evaluate both; record per-fold out-of-sample AUC/IC.
4. Ablate: incremental lift = augmented − baseline, with confidence intervals.
5. SHAP-attribute any lift to specific astro/Gann features.
6. Turn the better model into a strategy; backtest post-cost (`010`); compute **DSR** accounting for all trials to date.
7. Apply FDR across the full RQ family.
8. Verdict written to `discoveries`. Possible honest outcomes:
   - *Edge:* astro/gann add robust, corrected, post-cost lift → promote to paper (`011`).
   - *No edge:* lift ≈ 0 or vanishes after correction → recorded as null. **This is success of the platform, even if disappointing for the hypothesis.**
   - *Conditional edge:* lift only in specific regimes → reported with explicit conditions, lower confidence.

---

## 10. Anti-patterns Claude Code must refuse to implement
- Random shuffling of time-series into train/test.
- Selecting a strategy by best in-sample Sharpe without DSR/PBO.
- Reporting raw Sharpe from a parameter sweep.
- Joining today's revised macro value onto a historical feature date.
- Using only currently-listed symbols (survivorship).
- Letting the LLM (Agent 8/14) declare significance.
- Re-using the test set more than once.

If a user request implies any of these, surface the risk and implement the correct version instead.
