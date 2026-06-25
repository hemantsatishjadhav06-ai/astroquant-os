"""
Technical indicators for charting (SMA, EMA, RSI(Wilder), Bollinger, MACD).

Pure numpy; each returns an array the same length as the input with ``nan`` where the indicator is
undefined (warm-up). The chart endpoint pairs these with dates and drops the nans.
"""
from __future__ import annotations

import numpy as np


def sma(x: np.ndarray, n: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        c = np.cumsum(np.insert(x, 0, 0.0))
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ema(x: np.ndarray, n: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    alpha = 2.0 / (n + 1.0)
    out[n - 1] = x[:n].mean()
    for i in range(n, len(x)):
        out[i] = alpha * x[i] + (1 - alpha) * out[i - 1]
    return out


def rsi(x: np.ndarray, n: int = 14) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    delta = np.diff(x)
    gain = np.clip(delta, 0, None)
    loss = -np.clip(delta, None, 0)
    avg_g = gain[:n].mean()
    avg_l = loss[:n].mean()
    for i in range(n, len(x)):
        if i > n:
            avg_g = (avg_g * (n - 1) + gain[i - 1]) / n
            avg_l = (avg_l * (n - 1) + loss[i - 1]) / n
        rs = avg_g / avg_l if avg_l > 0 else np.inf
        out[i] = 100.0 - 100.0 / (1.0 + rs)
    return out


def bollinger(x: np.ndarray, n: int = 20, k: float = 2.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    mid = sma(x, n)
    sd = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        sd[i] = x[i - n + 1:i + 1].std()
    return mid, mid + k * sd, mid - k * sd


def macd(x: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    line = ema(x, fast) - ema(x, slow)
    valid = ~np.isnan(line)
    sig = np.full(len(x), np.nan)
    if valid.sum() >= signal:
        idx = np.where(valid)[0]
        s = ema(line[idx], signal)
        sig[idx] = s
    return line, sig, line - sig
