"""
Black–Scholes pricing + Greeks + implied-vol solver (European; Indian index options are cash-settled).

All Greeks are per ONE unit of underlying and per natural unit:
  * delta  : ∂V/∂S            (per 1.0 of spot)
  * gamma  : ∂²V/∂S²
  * theta  : ∂V/∂t per DAY    (calendar-day decay, negative for long options)
  * vega   : ∂V/∂σ per 1 vol-POINT (i.e. per 0.01 of σ)
Multiply by lot size × lots downstream for position Greeks.
"""
from __future__ import annotations

import math

SQRT2PI = math.sqrt(2.0 * math.pi)


def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _npdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT2PI


def _d1_d2(S: float, K: float, T: float, sigma: float, r: float, q: float) -> tuple[float, float]:
    if T <= 0 or sigma <= 0:
        # degenerate: treat as tiny to avoid div-by-zero; intrinsic handled by callers
        T = max(T, 1e-9)
        sigma = max(sigma, 1e-9)
    vol_t = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / vol_t
    return d1, d1 - vol_t


def bs_price(S: float, K: float, T: float, sigma: float, opt: str = "C",
             r: float = 0.065, q: float = 0.0) -> float:
    """European Black–Scholes price. ``opt`` ∈ {'C','P'}. T in years."""
    if T <= 0:
        return max(0.0, (S - K) if opt.upper().startswith("C") else (K - S))
    d1, d2 = _d1_d2(S, K, T, sigma, r, q)
    if opt.upper().startswith("C"):
        return S * math.exp(-q * T) * _ncdf(d1) - K * math.exp(-r * T) * _ncdf(d2)
    return K * math.exp(-r * T) * _ncdf(-d2) - S * math.exp(-q * T) * _ncdf(-d1)


def greeks(S: float, K: float, T: float, sigma: float, opt: str = "C",
           r: float = 0.065, q: float = 0.0) -> dict:
    """Return {price, delta, gamma, theta_day, vega_pt} for one option."""
    call = opt.upper().startswith("C")
    if T <= 0 or sigma <= 0:
        intrinsic = max(0.0, (S - K) if call else (K - S))
        delta = (1.0 if S > K else 0.0) if call else (-1.0 if S < K else 0.0)
        return {"price": round(intrinsic, 4), "delta": delta, "gamma": 0.0,
                "theta_day": 0.0, "vega_pt": 0.0}
    d1, d2 = _d1_d2(S, K, T, sigma, r, q)
    disc_q = math.exp(-q * T)
    disc_r = math.exp(-r * T)
    pdf = _npdf(d1)
    delta = disc_q * (_ncdf(d1) if call else _ncdf(d1) - 1.0)
    gamma = disc_q * pdf / (S * sigma * math.sqrt(T))
    vega = S * disc_q * pdf * math.sqrt(T)                      # per 1.0 vol
    term1 = -(S * disc_q * pdf * sigma) / (2.0 * math.sqrt(T))
    if call:
        theta = term1 - r * K * disc_r * _ncdf(d2) + q * S * disc_q * _ncdf(d1)
    else:
        theta = term1 + r * K * disc_r * _ncdf(-d2) - q * S * disc_q * _ncdf(-d1)
    return {
        "price": round(bs_price(S, K, T, sigma, opt, r, q), 4),
        "delta": round(delta, 5),
        "gamma": round(gamma, 7),
        "theta_day": round(theta / 365.0, 5),                  # per calendar day
        "vega_pt": round(vega / 100.0, 5),                     # per 1% vol
    }


def implied_vol(price: float, S: float, K: float, T: float, opt: str = "C",
                r: float = 0.065, q: float = 0.0) -> float:
    """Invert BS for σ via bisection (robust, no derivative). Returns 0.0 if not solvable."""
    intrinsic = max(0.0, (S - K) if opt.upper().startswith("C") else (K - S)) * math.exp(-r * T)
    if T <= 0 or price <= intrinsic:
        return 0.0
    lo, hi = 1e-4, 5.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if bs_price(S, K, T, mid, opt, r, q) > price:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-6:
            break
    return round(0.5 * (lo + hi), 6)
