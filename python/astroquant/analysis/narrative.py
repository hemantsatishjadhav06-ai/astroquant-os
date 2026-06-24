"""
Analyst narrative for a StockReport.

If an LLM key is configured in the environment (``ANTHROPIC_API_KEY`` or ``OPENAI_API_KEY``) the
report is sent to the model for a richer write-up; otherwise a strong, deterministic analyst-style
narrative is generated from the structured numbers. **No keys are read from code** — env only.

The narrative is deliberately honest: the technical/price read is evidence-based; the Gann and astro
sections are framed as descriptive/speculative and explicitly deferred to the backtest verdict, which
states whether those families add real out-of-sample, post-cost edge for this name.
"""
from __future__ import annotations

import json
import os
import urllib.request

from astroquant.analysis.stock import StockReport

_SYSTEM = (
    "You are a rigorous Indian-equity analyst and market strategist who is also a careful "
    "statistician. Write a deep, well-structured markdown analysis from the supplied JSON. Cover: "
    "(1) market context, (2) technical read, (3) Gann geometry levels & timing, (4) astrological "
    "backdrop — clearly flagged as unproven prior, (5) the backtest verdict and what it means, "
    "(6) a balanced strategy with entry/invalidation/risk, (7) a one-line disclaimer. Be honest about "
    "what is evidence-based versus speculative. Never promise returns."
)


def llm_available() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def _call_anthropic(prompt: str, key: str) -> str:
    body = json.dumps({
        "model": os.environ.get("AQ_LLM_MODEL", "claude-3-5-haiku-20241022"),
        "max_tokens": 1400,
        "system": _SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)["content"][0]["text"]


def _call_openai(prompt: str, key: str) -> str:
    body = json.dumps({
        "model": os.environ.get("AQ_LLM_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}],
        "max_tokens": 1400,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=body,
        headers={"authorization": f"Bearer {key}", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def _template(r: StockReport) -> str:
    m, t, g, a, b, s = r.market, r.technical, r.gann, r.astro, r.backtest, r.scores
    retro = ", ".join(a["retrogrades"]) or "none"
    asp = "; ".join(f"{x['a']}–{x['b']} {x['type']}" for x in a["aspects"][:3]) or "no tight major aspects"
    verdict = b.get("verdict", "not run")
    edge_line = (
        "the backtest found **no robust astro/Gann edge** beyond technical+market signals for this name "
        "(an honest null — price action remains the load-bearing input)"
        if verdict == "no_edge_found" else
        f"the backtest verdict is **{verdict}** (lift {b.get('incremental_lift', 0):+.3f}) — treat with caution and re-validate"
    )
    cyc = g["upcoming_cycles"][:3]
    cyc_txt = ", ".join(f"{c['date']} ({c['days']}d from {c['from']})" for c in cyc) or "none upcoming"
    return f"""# {r.name} ({r.symbol}) — Deep Dive
*Sector: {r.sector} · As of {r.as_of} · {r.n_bars} sessions · source: {r.meta.get('data_source_stamp', r.source)}*

## Executive read — **{s['stance']}**
{r.name} last traded **₹{m['last_close']:,}** ({_pct(m['change_1d'])} on the day, {_pct(m['change_20d'])} over ~1 month),
{_pct(m['dist_from_high'])} from its 1-year high of ₹{m['high_252']:,}. The composite stance is **{s['stance']}**
(score {s['composite']:+.2f}), driven primarily by the technical picture; {edge_line}.

## 1. Technical
The trend is **{t['trend']}** with price {_pct(t['price_vs_sma20'])} versus its 20-day SMA (₹{t['sma20']:,})
and {_pct(t['price_vs_sma50'])} versus the 50-day (₹{t['sma50']:,}). RSI(14) is **{t['rsi14']} ({t['rsi_state']})**,
20-day momentum {_pct(t['momentum_20d'])}, annualised volatility ~{t['volatility_annual'] * 100:.0f}%,
and the latest volume is {t['volume_vs_avg20']}× its 20-day average. This is the evidence-based core of the view.

## 2. Gann geometry
On the Square of Nine around ₹{m['last_close']:,}, the nearest projected **resistance is ₹{g['nearest_resistance']:,}**
and **support ₹{g['nearest_support']:,}** (further levels: R {g['resistances']}, S {g['supports']}).
The recent swing high was ₹{g['pivot_high']:,} ({g['pivot_high_date']}) and swing low ₹{g['pivot_low']:,} ({g['pivot_low_date']}).
Gann time-cycle windows to watch: {cyc_txt}. Use these as *levels and dates of interest*, not signals on their own.

## 3. Astrological backdrop (unproven prior — see backtest)
As of {r.as_of[:4]}, the Moon is in **{a['moon_sign']} / {a['moon_nakshatra']}** ({a['paksha']} paksha, tithi {a['tithi']},
{a['moon_illum'] * 100:.0f}% illuminated); Sun in **{a['sun_sign']}**. Retrograde: **{retro}**. Tight aspects: {asp}.
These are recorded for completeness; their predictive value is **not assumed** and is tested directly below.

## 4. Backtest verdict (the honest gate)
Across a chronological walk-forward with multiple-testing correction, baseline AUC was
{b.get('baseline_auc', '—')} versus augmented (with astro+Gann) {b.get('augmented_auc', '—')}; {edge_line}.
The illustrative post-cost paper strategy returned {_pct(b.get('strategy_return', 0))} with Sharpe
{b.get('strategy_sharpe', 0)}, Deflated Sharpe {b.get('strategy_dsr', 0)}, max drawdown
{b.get('strategy_max_drawdown', 0) * 100:.0f}% — *paper only, never live*.

## 5. Strategy & risk
Given a **{t['trend'].lower()}** with RSI {t['rsi_state']}: a constructive plan engages on strength above the
20-day SMA (₹{t['sma20']:,}) toward the Gann resistance ₹{g['nearest_resistance']:,}, with invalidation on a
close below the swing-low/support zone (₹{g['nearest_support']:,}). Size to the ~{t['volatility_annual'] * 100:.0f}%
annual volatility; respect the ~{abs(b.get('strategy_max_drawdown', 0)) * 100:.0f}% historical drawdown of the tested
strategy. Position with the trend, not the horoscope.

> **Disclaimer:** research/education only — not investment advice. Astrological factors are tested, not assumed;
> all performance is hypothetical and post-cost. Nothing here is a live trading signal.
"""


def generate_narrative(report: StockReport, *, use_llm: bool = True) -> str:
    provider = llm_available() if use_llm else None
    if provider:
        prompt = ("Write the analysis from this JSON:\n\n"
                  + json.dumps({k: v for k, v in report.to_dict().items() if k != "astro"}
                               | {"astro_summary": {x: report.astro[x] for x in
                                  ("moon_sign", "moon_nakshatra", "sun_sign", "retrogrades", "aspects")}},
                               default=str))
        try:
            key = os.environ["ANTHROPIC_API_KEY"] if provider == "anthropic" else os.environ["OPENAI_API_KEY"]
            text = _call_anthropic(prompt, key) if provider == "anthropic" else _call_openai(prompt, key)
            return text + "\n\n_— generated with " + provider + "; structured data by AstroQuant OS._"
        except Exception as e:  # noqa: BLE001 — never fail the report on LLM issues
            return _template(report) + f"\n\n_(LLM enrichment unavailable: {type(e).__name__}; showing built-in narrative.)_"
    return _template(report)
