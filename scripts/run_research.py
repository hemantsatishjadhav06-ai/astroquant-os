"""
End-to-end research demo (docs/007 §9, docs/013 vertical slice).

Runs the full chain with NO database, NO API keys, NO network:
    synthetic NIFTY bars → Feature Factory (technical+market+astro+gann)
    → Research Engine (baseline→augmented→ablation→sanity→correction→verdict)
    → Paper-Trading gate (post-cost equity curve)
    → self-contained HTML report.

Run:  PYTHONPATH=python python3 scripts/run_research.py [out.html]
"""
from __future__ import annotations

import sys
from datetime import date

sys.path.insert(0, "python")

from astroquant.research.pipeline import run_full_pipeline   # noqa: E402
from astroquant.research.report import write_html_report     # noqa: E402


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "research_report.html"
    print("AstroQuant OS — running RQ-004 vertical slice (synthetic, offline)\n")

    output = run_full_pipeline(
        symbol="NIFTY",
        start=date(2014, 1, 1),
        end=date(2023, 12, 31),
        source="synthetic",
        n_prior_trials=1,
    )
    r, p, m = output.report, output.paper, output.meta

    print(f"  data        : {m['n_bars']} synthetic bars → {m['n_samples']} samples, {m['n_features']} features")
    print(f"  baseline AUC: {r.baseline_auc:.3f}  (technical + market)")
    print(f"  augmented AUC: {r.augmented_auc:.3f}  (+ astro + gann)")
    print(f"  incremental lift: {r.incremental_lift:+.3f}")
    print(f"  shuffle-label guard: {'GENUINE SIGNAL' if r.shuffle_label_pass else 'no edge (correct null)'}")
    print(f"  random-feature guard: {'pass' if r.random_feature_pass else 'FAIL'}")
    print(f"  adjusted p-value: {r.p_adj:.4f}  (deflated for {r.n_comparisons} comparison(s))")
    print(f"  paper-trade post-cost: return {p.total_return*100:+.2f}%  "
          f"Sharpe {p.sharpe:.2f}  DSR {p.deflated_sharpe:.2f}  maxDD {p.max_drawdown*100:.1f}%  "
          f"(ledger reconciled: {p.reconciled})")
    print(f"\n  >>> VERDICT: {r.verdict.upper().replace('_', ' ')} <<<")
    print("      (a 'no edge' verdict is the platform working correctly — it refuses to certify noise.)\n")

    write_html_report(output, out_path)
    print(f"  HTML report written to: {out_path}")


if __name__ == "__main__":
    main()
