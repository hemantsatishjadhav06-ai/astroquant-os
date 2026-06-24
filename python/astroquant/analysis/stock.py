"""
Stock Deep Dive — combine technical + Gann + astrology + a rigorous backtest for one symbol.

Produces a structured ``StockReport``. The technical and price sections are the load-bearing,
evidence-based part; the Gann and astro sections are presented descriptively and are *graded by the
backtest* (which honestly reports whether astro/Gann add out-of-sample, post-cost edge for this name).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import date

import numpy as np

from astroquant.agents.base import get_logger
from astroquant.collectors.astronomy import AstronomyCollector
from astroquant.collectors.gann import square_of_nine, time_cycles
from astroquant.collectors.sources.market_sources import get_source
from astroquant.features.factory import AUGMENTED_FAMILIES, BASELINE_FAMILIES, FeatureFactory, _rsi
from astroquant.paper.engine import positions_from_probabilities, run_paper_trade
from astroquant.research.engine import run_protocol
from astroquant.research.model import LogisticModel
from astroquant.universe import get_stock

log = get_logger("analysis.stock")

_MAJOR_ASPECTS = {0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition"}


@dataclass
class StockReport:
    symbol: str
    name: str
    sector: str
    source: str
    as_of: str
    n_bars: int
    market: dict
    technical: dict
    gann: dict
    astro: dict
    backtest: dict
    scores: dict
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _classify_aspect(sep: float, orb: float = 6.0) -> str | None:
    for ang, name in _MAJOR_ASPECTS.items():
        if abs(sep - ang) <= orb:
            return name
    return None


def _technical(closes: np.ndarray, vols: np.ndarray) -> dict:
    last = float(closes[-1])
    sma20 = float(closes[-20:].mean())
    sma50 = float(closes[-50:].mean()) if len(closes) >= 50 else sma20
    rets = np.diff(closes[-21:]) / closes[-21:-1]
    vol_annual = float(rets.std() * math.sqrt(252)) if len(rets) > 1 else 0.0
    rsi = _rsi(closes, 14)
    mom20 = float(last / closes[-21] - 1.0) if len(closes) > 21 else 0.0
    if last > sma20 > sma50:
        trend = "Uptrend"
    elif last < sma20 < sma50:
        trend = "Downtrend"
    else:
        trend = "Sideways"
    if rsi >= 70:
        rsi_state = "overbought"
    elif rsi <= 30:
        rsi_state = "oversold"
    else:
        rsi_state = "neutral"
    return {
        "rsi14": round(rsi, 1), "rsi_state": rsi_state, "sma20": round(sma20, 2),
        "sma50": round(sma50, 2), "price_vs_sma20": round(last / sma20 - 1, 4),
        "price_vs_sma50": round(last / sma50 - 1, 4), "momentum_20d": round(mom20, 4),
        "volatility_annual": round(vol_annual, 4), "trend": trend,
        "volume_vs_avg20": round(float(vols[-1] / (vols[-20:].mean() + 1e-9)), 2),
    }


def _gann(closes: np.ndarray, dates: list[str]) -> dict:
    last = float(closes[-1])
    levels = square_of_nine(last)
    res = sorted([l.price for l in levels if l.price > last])
    sup = sorted([l.price for l in levels if 0 < l.price < last], reverse=True)
    win = closes[-90:] if len(closes) >= 90 else closes
    win_dates = dates[-len(win):]
    hi_i, lo_i = int(np.argmax(win)), int(np.argmin(win))
    as_of = date.fromisoformat(dates[-1])
    cycles_hi = [c for c in time_cycles(date.fromisoformat(win_dates[hi_i]))
                 if date.fromisoformat(c.target_date) >= as_of][:4]
    cycles_lo = [c for c in time_cycles(date.fromisoformat(win_dates[lo_i]))
                 if date.fromisoformat(c.target_date) >= as_of][:4]
    return {
        "sqrt_price": round(math.sqrt(last), 3),
        "nearest_resistance": round(res[0], 2) if res else None,
        "nearest_support": round(sup[0], 2) if sup else None,
        "resistances": [round(x, 2) for x in res[:3]],
        "supports": [round(x, 2) for x in sup[:3]],
        "pivot_high": round(float(win.max()), 2), "pivot_high_date": win_dates[hi_i],
        "pivot_low": round(float(win.min()), 2), "pivot_low_date": win_dates[lo_i],
        "upcoming_cycles": [{"from": "swing high", "days": c.cycle_len, "date": c.target_date} for c in cycles_hi]
                            + [{"from": "swing low", "days": c.cycle_len, "date": c.target_date} for c in cycles_lo],
    }


def _astro(as_of: date) -> dict:
    col = AstronomyCollector()
    planets = col.planets_for_date(as_of)
    mp = col.moon_phase_for_date(as_of)
    by = {p.body: p for p in planets}
    retro = [p.body for p in planets if p.is_retrograde and p.body not in ("Rahu", "Ketu")]
    aspects = []
    for a in col.aspects_for_date(as_of):
        kind = _classify_aspect(a.angle_deg)
        if kind and a.body_a not in ("Rahu", "Ketu") and a.body_b not in ("Rahu", "Ketu"):
            aspects.append({"a": a.body_a, "b": a.body_b, "type": kind, "sep": a.angle_deg})
    aspects.sort(key=lambda x: min(abs(x["sep"] - k) for k in _MAJOR_ASPECTS))
    return {
        "moon_phase": mp.phase_angle, "moon_illum": mp.illumination, "tithi": mp.tithi,
        "paksha": mp.paksha, "moon_nakshatra": by["Moon"].nakshatra_name,
        "moon_sign": by["Moon"].sign_name, "sun_sign": by["Sun"].sign_name,
        "retrogrades": retro,
        "planets": [{"body": p.body, "sign": p.sign_name, "nakshatra": p.nakshatra_name,
                     "deg": round(p.longitude_sidereal, 2), "retro": p.is_retrograde} for p in planets],
        "aspects": aspects[:6],
    }


def _backtest(bars, n_permutations: int) -> dict:
    fm = FeatureFactory(warmup=25, use_astro=True, use_gann=True).build(bars)
    rep = run_protocol(fm, "STOCK", baseline_families=BASELINE_FAMILIES,
                       augmented_families=AUGMENTED_FAMILIES, k_folds=4,
                       n_permutations=n_permutations, n_prior_trials=1)
    split = int(len(fm.y) * 0.6)
    X = fm.subset(AUGMENTED_FAMILIES)
    model = LogisticModel(l2=1.0, lr=0.2, n_iter=400).fit(X[:split], fm.y[:split])
    probs = model.predict_proba(X[split:])
    pos = positions_from_probabilities(probs, band=0.02)
    paper = run_paper_trade(bars, pos, fm.fwd_return[split:], fm.dates[split:], n_prior_trials=1)
    return {
        "verdict": rep.verdict, "baseline_auc": rep.baseline_auc, "augmented_auc": rep.augmented_auc,
        "incremental_lift": rep.incremental_lift, "astro_gann_adds_edge": rep.shuffle_label_pass and rep.incremental_lift > 0,
        "strategy_return": paper.total_return, "strategy_sharpe": paper.sharpe,
        "strategy_dsr": paper.deflated_sharpe, "strategy_max_drawdown": paper.max_drawdown,
        "n_samples": int(len(fm.y)), "equity_curve": paper.equity_curve,
    }


def _scores(technical: dict, gann: dict, backtest: dict, market: dict) -> dict:
    t = 0.0
    t += 0.5 if technical["trend"] == "Uptrend" else (-0.5 if technical["trend"] == "Downtrend" else 0.0)
    t += 0.2 if technical["momentum_20d"] > 0 else -0.2
    if technical["rsi_state"] == "overbought":
        t -= 0.15
    elif technical["rsi_state"] == "oversold":
        t += 0.15
    t = max(-1.0, min(1.0, t))
    # Gann: room to nearest resistance vs support (closer to support => more upside room)
    last = market["last_close"]
    nr, ns = gann["nearest_resistance"], gann["nearest_support"]
    g = 0.0
    if nr and ns and nr > ns:
        pos_in_range = (last - ns) / (nr - ns)
        g = round(0.5 - pos_in_range, 3)        # near support (+), near resistance (-)
    edge = bool(backtest.get("astro_gann_adds_edge"))
    composite = round(0.6 * t + 0.2 * g + (0.2 if edge else 0.0), 3)
    stance = "Constructive" if composite > 0.25 else ("Cautious" if composite < -0.25 else "Neutral")
    return {"technical_score": round(t, 3), "gann_score": g,
            "astro_gann_edge": edge, "composite": composite, "stance": stance}


def analyze_stock(
    symbol: str,
    source: str = "nse",
    *,
    years: int = 6,
    do_backtest: bool = True,
    n_permutations: int = 10,
) -> StockReport:
    meta = get_stock(symbol)
    end = date.today()
    start = date(end.year - years, 1, 1)
    kwargs = {"fallback_synthetic": True} if source in ("nse", "bse") else {}
    bars = get_source(source, **kwargs).history(meta.symbol, "1d", start, end)
    if len(bars) < 60:
        raise ValueError(f"not enough data for {symbol} ({len(bars)} bars)")
    closes = np.array([b.close for b in bars], dtype=float)
    vols = np.array([b.volume for b in bars], dtype=float)
    dates = [b.ts.date().isoformat() for b in bars]
    as_of = date.fromisoformat(dates[-1])

    market = {
        "last_close": round(float(closes[-1]), 2),
        "change_1d": round(float(closes[-1] / closes[-2] - 1), 4),
        "change_5d": round(float(closes[-1] / closes[-6] - 1), 4) if len(closes) > 6 else 0.0,
        "change_20d": round(float(closes[-1] / closes[-21] - 1), 4) if len(closes) > 21 else 0.0,
        "high_252": round(float(closes[-252:].max()), 2),
        "low_252": round(float(closes[-252:].min()), 2),
        "dist_from_high": round(float(closes[-1] / closes[-252:].max() - 1), 4),
        "currency": "INR",
    }
    technical = _technical(closes, vols)
    gann = _gann(closes, dates)
    astro = _astro(end)
    backtest = _backtest(bars, n_permutations) if do_backtest else {}
    scores = _scores(technical, gann, backtest, market)

    log.info("stock[%s]: stance=%s trend=%s verdict=%s", meta.symbol, scores["stance"],
             technical["trend"], backtest.get("verdict", "skipped"))
    return StockReport(
        symbol=meta.symbol, name=meta.name, sector=meta.sector, source=source,
        as_of=as_of.isoformat(), n_bars=len(bars), market=market, technical=technical,
        gann=gann, astro=astro, backtest=backtest, scores=scores,
        meta={"start": start.isoformat(), "end": end.isoformat(), "yahoo": meta.yahoo,
              "data_source_stamp": bars[-1].source},
    )
