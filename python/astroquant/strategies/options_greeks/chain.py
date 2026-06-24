"""
Option chain: live NSE collection + a deterministic synthetic fallback, plus IV-rank.

Live: NSE's public ``option-chain-indices`` JSON (cookie handshake required; routinely blocks
datacenter IPs) — wrapped best-effort with a graceful fallback to a Black–Scholes synthetic chain so
backtests and offline/PaaS runs always work. Every quote carries Greeks computed by ``greeks.py``.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date

from astroquant.agents.base import get_logger
from astroquant.strategies.options_greeks.expiry import dte, next_weekly_expiry
from astroquant.strategies.options_greeks.greeks import greeks, implied_vol

log = get_logger("options.chain")


def strike_step(symbol: str, spot: float) -> int:
    s = symbol.upper()
    if s in ("NIFTY", "FINNIFTY"):
        return 50
    if s in ("BANKNIFTY", "SENSEX", "BANKEX"):
        return 100
    # stocks: ~2.5% of spot, rounded to a sensible increment
    raw = max(2.5, spot * 0.025)
    for inc in (2.5, 5, 10, 20, 50, 100):
        if raw <= inc:
            return int(inc) if inc >= 1 else inc
    return 100


@dataclass
class OptionQuote:
    strike: float
    opt: str            # 'C' | 'P'
    price: float
    iv: float
    oi: int
    delta: float
    gamma: float
    theta_day: float
    vega_pt: float


@dataclass
class OptionChain:
    symbol: str
    spot: float
    as_of: str
    expiry: str
    dte: int
    atm_strike: float
    iv_atm: float
    iv_rank: float
    quotes: list[OptionQuote] = field(default_factory=list)
    source: str = "synthetic"

    def get(self, strike: float, opt: str) -> OptionQuote | None:
        for q in self.quotes:
            if abs(q.strike - strike) < 1e-6 and q.opt == opt.upper()[0]:
                return q
        return None

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def iv_rank_from_series(series: list[float], current: float) -> float:
    """Percentile rank of ``current`` IV within a trailing series (spec §7)."""
    if not series:
        return 0.5
    below = sum(1 for x in series if x <= current)
    return round(below / len(series), 4)


def build_synthetic_chain(
    symbol: str, spot: float, as_of: date, *, base_iv: float = 0.15,
    iv_rank: float = 0.5, n_strikes: int = 8, r: float = 0.065,
) -> OptionChain:
    """Deterministic BS chain with a mild volatility smile — the offline/clean-room chain."""
    step = strike_step(symbol, spot)
    atm = round(spot / step) * step
    exp = next_weekly_expiry(symbol, as_of)
    t_years = max(dte(symbol, as_of, "weekly"), 1) / 365.0
    quotes: list[OptionQuote] = []
    for i in range(-n_strikes, n_strikes + 1):
        k = atm + i * step
        if k <= 0:
            continue
        moneyness = abs(k - spot) / spot
        iv = base_iv * (1.0 + 0.6 * moneyness)               # smile: OTM richer
        for opt in ("C", "P"):
            g = greeks(spot, k, t_years, iv, opt, r)
            oi = int(max(0, 100000 * (1.0 - moneyness * 4)))  # synthetic OI hump at ATM
            quotes.append(OptionQuote(k, opt, g["price"], round(iv, 4), oi,
                                      g["delta"], g["gamma"], g["theta_day"], g["vega_pt"]))
    return OptionChain(symbol=symbol.upper(), spot=round(spot, 2), as_of=as_of.isoformat(),
                       expiry=exp.isoformat(), dte=dte(symbol, as_of, "weekly"),
                       atm_strike=atm, iv_atm=round(base_iv, 4), iv_rank=round(iv_rank, 4),
                       quotes=quotes, source="synthetic")


def fetch_nse_chain(symbol: str = "NIFTY", *, r: float = 0.065) -> OptionChain:
    """Live NSE option chain (best-effort; raises on failure so callers can fall back)."""
    sym = symbol.upper()
    base = "https://www.nseindia.com"
    headers = {"User-Agent": "Mozilla/5.0 (AstroQuant-OS)", "Accept": "application/json",
               "Accept-Language": "en-US,en;q=0.9", "Referer": f"{base}/option-chain"}
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    opener.open(urllib.request.Request(base, headers=headers), timeout=12)  # seed cookies
    url = f"{base}/api/option-chain-indices?symbol={sym}"
    with opener.open(urllib.request.Request(url, headers=headers), timeout=12) as resp:
        data = json.load(resp)
    recs = data["records"]
    spot = float(recs["underlyingValue"])
    as_of = date.today()
    step = strike_step(sym, spot)
    atm = round(spot / step) * step
    quotes: list[OptionQuote] = []
    iv_atm = 0.15
    for row in recs["data"]:
        k = float(row["strikePrice"])
        exp = next_weekly_expiry(sym, as_of)
        t_years = max((exp - as_of).days, 1) / 365.0
        for side, opt in (("CE", "C"), ("PE", "P")):
            if side not in row:
                continue
            o = row[side]
            price = float(o.get("lastPrice") or 0) or 0.01
            iv = float(o.get("impliedVolatility") or 0) / 100.0
            if iv <= 0:
                iv = implied_vol(price, spot, k, t_years, opt, r) or 0.15
            if abs(k - atm) < 1e-6 and opt == "C":
                iv_atm = iv
            g = greeks(spot, k, t_years, iv, opt, r)
            quotes.append(OptionQuote(k, opt, price, round(iv, 4), int(o.get("openInterest") or 0),
                                      g["delta"], g["gamma"], g["theta_day"], g["vega_pt"]))
    exp = next_weekly_expiry(sym, as_of)
    return OptionChain(symbol=sym, spot=round(spot, 2), as_of=as_of.isoformat(),
                       expiry=exp.isoformat(), dte=max((exp - as_of).days, 0), atm_strike=atm,
                       iv_atm=round(iv_atm, 4), iv_rank=0.5, quotes=quotes, source="nse-live")


def get_chain(symbol: str, spot: float | None = None, *, live: bool = True,
              base_iv: float = 0.15, iv_rank: float = 0.5) -> OptionChain:
    """Live NSE chain when ``live`` and reachable, else a synthetic chain around ``spot``."""
    if live:
        try:
            return fetch_nse_chain(symbol)
        except Exception as e:  # noqa: BLE001 — best effort
            log.warning("options: NSE chain unavailable (%s); using synthetic", type(e).__name__)
    if spot is None:
        raise ValueError("spot required for a synthetic chain")
    return build_synthetic_chain(symbol, spot, date.today(), base_iv=base_iv, iv_rank=iv_rank)
