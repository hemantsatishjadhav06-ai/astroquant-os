"""
Self-contained HTML research report (docs/007 §8 discoveries ledger, human-readable view).

Renders a single offline HTML file (inline CSS + inline SVG equity curve — no network, no CDN) that
shows the verdict, the baseline→augmented ablation, the integrity guards, and the post-cost paper-trade
result. This is the "working model to look at": open it in any browser.
"""
from __future__ import annotations

import html
from datetime import date, datetime, timezone

from astroquant.research.pipeline import PipelineOutput

_VERDICT_STYLE = {
    "edge": ("#0b8457", "EDGE FOUND"),
    "conditional_edge": ("#b8860b", "CONDITIONAL EDGE"),
    "no_edge_found": ("#5a6472", "NO EDGE FOUND"),
}


def _svg_equity(equity: list[float], width: int = 860, height: int = 260) -> str:
    if len(equity) < 2:
        return "<p>no equity data</p>"
    lo, hi = min(equity), max(equity)
    rng = (hi - lo) or 1.0
    pad = 30
    n = len(equity)
    pts = []
    for i, v in enumerate(equity):
        x = pad + (width - 2 * pad) * i / (n - 1)
        y = pad + (height - 2 * pad) * (1 - (v - lo) / rng)
        pts.append(f"{x:.1f},{y:.1f}")
    base = equity[0]
    y_base = pad + (height - 2 * pad) * (1 - (base - lo) / rng)
    line = " ".join(pts)
    up = equity[-1] >= equity[0]
    color = "#0b8457" if up else "#c0392b"
    return f"""<svg viewBox="0 0 {width} {height}" width="100%" preserveAspectRatio="xMidYMid meet" role="img" aria-label="equity curve">
  <rect x="0" y="0" width="{width}" height="{height}" fill="#fbfcfe" rx="8"/>
  <line x1="{pad}" y1="{y_base:.1f}" x2="{width-pad}" y2="{y_base:.1f}" stroke="#c9d2dc" stroke-dasharray="4 4"/>
  <polyline fill="none" stroke="{color}" stroke-width="2" points="{line}"/>
  <text x="{pad}" y="18" fill="#5a6472" font-size="12">equity curve (post-cost paper trade)</text>
  <text x="{width-pad}" y="{y_base-6:.1f}" fill="#9aa6b2" font-size="11" text-anchor="end">start capital</text>
</svg>"""


def _row(label: str, value: str, hint: str = "") -> str:
    h = f'<span class="hint">{html.escape(hint)}</span>' if hint else ""
    return (f'<tr><td class="lbl">{html.escape(label)}</td>'
            f'<td class="val">{html.escape(value)} {h}</td></tr>')


def render_html_report(out: PipelineOutput) -> str:
    r = out.report
    p = out.paper
    m = out.meta
    color, badge = _VERDICT_STYLE.get(r.verdict, ("#5a6472", r.verdict.upper()))

    # planetary snapshot for the window start (illustrative provenance)
    try:
        from astroquant.collectors.astronomy import AstronomyCollector
        col = AstronomyCollector()
        snap = col.planets_for_date(date.fromisoformat(m["start"]))
        planet_rows = "".join(
            f"<tr><td>{html.escape(pl.body)}</td><td>{pl.longitude_sidereal:.2f}°</td>"
            f"<td>{html.escape(pl.sign_name)}</td><td>{html.escape(pl.nakshatra_name)}</td>"
            f"<td>{'R' if pl.is_retrograde else '—'}</td></tr>"
            for pl in snap
        )
    except Exception:
        planet_rows = ""

    sane = "✓ pass" if (r.random_feature_pass and p.reconciled) else "⚠ check"
    shuffle_txt = ("genuine signal detected above shuffled noise"
                   if r.shuffle_label_pass else
                   "collapses to chance on shuffled labels (correct null behaviour)")

    metrics = "".join([
        _row("Baseline AUC (technical + market)", f"{r.baseline_auc:.3f}", "control model, out-of-sample"),
        _row("Augmented AUC (+ astro + gann)", f"{r.augmented_auc:.3f}", "treatment model, out-of-sample"),
        _row("Incremental lift (ablation)", f"{r.incremental_lift:+.3f}", "augmented − baseline"),
        _row("Raw p-value", f"{r.p_raw:.4f}", "one-sided, fold lift > 0"),
        _row("Adjusted p-value", f"{r.p_adj:.4f}", f"deflated for {r.n_comparisons} comparison(s)"),
        _row("Shuffle-label guard", "real signal" if r.shuffle_label_pass else "no edge", shuffle_txt),
        _row("Random-feature guard", "pass" if r.random_feature_pass else "FAIL", "noise must not rank important"),
    ])

    capital_val = float(p.detail.get("capital", 0.0))
    paper_metrics = "".join([
        _row("Post-cost total return", f"{p.total_return*100:+.2f}%", f"on ₹{capital_val:,.0f} capital"),
        _row("Sharpe (post-cost)", f"{p.sharpe:.2f}", "annualised"),
        _row("Deflated Sharpe Ratio", f"{p.deflated_sharpe:.3f}", "Bailey & López de Prado; > 0.5 ≈ credible"),
        _row("Max drawdown", f"{p.max_drawdown*100:.1f}%", ""),
        _row("Hit rate", f"{p.hit_rate*100:.1f}%", "of active days"),
        _row("Trades", f"{p.n_trades}", ""),
        _row("Total costs paid", f"₹{p.total_cost:,.0f}", "STT+exch+SEBI+stamp+GST"),
        _row("Ledger reconciled", "✓ yes" if p.reconciled else "✗ NO", "equity == cash + Σpnl − Σcost"),
    ])

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AstroQuant OS — {html.escape(r.hypothesis_id)} Research Report</title>
<style>
  :root {{ --ink:#1f2733; --muted:#5a6472; --line:#e6eaf0; --card:#ffffff; --bg:#f1f4f8; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
         margin:0; background:var(--bg); color:var(--ink); line-height:1.5; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:28px 20px 60px; }}
  header h1 {{ margin:0 0 4px; font-size:24px; }}
  header p {{ margin:0; color:var(--muted); font-size:14px; }}
  .badge {{ display:inline-block; padding:8px 16px; border-radius:999px; color:#fff;
            font-weight:700; letter-spacing:.4px; background:{color}; }}
  .verdict {{ display:flex; align-items:center; gap:16px; margin:20px 0 8px; flex-wrap:wrap; }}
  .verdict .q {{ color:var(--muted); font-size:14px; max-width:620px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:18px; }}
  @media (max-width:720px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; }}
  .card h2 {{ margin:0 0 12px; font-size:15px; text-transform:uppercase; letter-spacing:.5px; color:var(--muted); }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  td {{ padding:7px 4px; border-bottom:1px solid var(--line); vertical-align:top; }}
  td.lbl {{ color:var(--muted); }} td.val {{ text-align:right; font-variant-numeric:tabular-nums; font-weight:600; }}
  .hint {{ display:block; font-weight:400; color:#9aa6b2; font-size:11px; }}
  .full {{ grid-column:1 / -1; }}
  .pl td {{ font-size:13px; text-align:left; }} .pl th {{ text-align:left; color:var(--muted); font-size:12px; padding:4px; }}
  footer {{ margin-top:26px; color:#9aa6b2; font-size:12px; }}
  .note {{ background:#fff8e6; border:1px solid #f0e2bb; border-radius:10px; padding:12px 14px; font-size:13px; color:#6b5b1f; margin-top:18px; }}
</style></head>
<body><div class="wrap">
  <header>
    <h1>AstroQuant OS — Research Report</h1>
    <p>Hypothesis <strong>{html.escape(r.hypothesis_id)}</strong> · {html.escape(m['symbol'])} · {html.escape(m['source'])} data · {html.escape(m['start'])} → {html.escape(m['end'])} · generated {generated}</p>
  </header>

  <div class="verdict">
    <span class="badge">{html.escape(badge)}</span>
    <span class="q">Do astro + Gann features add out-of-sample, post-cost predictive power beyond technical + market features for next-day {html.escape(m['symbol'])} direction?</span>
  </div>

  <div class="grid">
    <div class="card"><h2>Ablation &amp; integrity</h2><table>{metrics}</table></div>
    <div class="card"><h2>Paper-trade (G5 gate, post-cost)</h2><table>{paper_metrics}</table></div>
    <div class="card full"><h2>Out-of-sample equity curve</h2>{_svg_equity(p.equity_curve)}</div>
    <div class="card full"><h2>Ephemeris provenance — {html.escape(m['start'])} (sidereal / Lahiri)</h2>
      <table class="pl"><tr><th>Body</th><th>Sid. long.</th><th>Sign</th><th>Nakshatra</th><th>Retro</th></tr>{planet_rows}</table>
    </div>
  </div>

  <div class="note"><strong>How to read this:</strong> a verdict of <em>NO EDGE FOUND</em> is a
  <em>success of the platform</em>, not a failure — it means the integrity controls (chronological
  walk-forward, shuffle-label &amp; random-feature guards, multiple-testing deflation, Deflated Sharpe)
  correctly refused to certify noise as signal. An <em>EDGE</em> verdict requires positive incremental
  lift that is out-of-sample, post-cost, survives correction, and clears the Deflated-Sharpe bar.</div>

  <footer>
    Reproducible run · {m['n_bars']} bars · {m['n_samples']} samples · {m['n_features']} features
    (baseline + astro + gann) · seed {m['seed']} · sanity {sane}.<br/>
    Research platform only — no live trading. Swiss Ephemeris (AGPL) isolated behind the astronomy collector.
  </footer>
</div></body></html>"""


def write_html_report(out: PipelineOutput, path: str) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_html_report(out))
    return path
