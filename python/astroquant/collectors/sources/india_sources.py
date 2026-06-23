"""
Free NSE & BSE market-data adapters (docs/005 §1).

These pull **real** Indian equity/index history for free via Yahoo Finance's public chart endpoint,
which redistributes NSE (``.NS``) and BSE (``.BO``) data — no API key, no broker account. Each bar is
provider-stamped (``source = "nse" | "bse"``) so the warehouse can cross-check sources (gate G1).

Design choices:
  * **No third-party dependency** — uses the stdlib (`urllib`) so the container stays slim.
  * **Graceful fallback** — if the network is unavailable (offline CI, restricted host), the source
    falls back to the deterministic SyntheticSource so the discovery loop never crashes. Bars from the
    fallback are stamped ``"<name>:synthetic"`` so you always know what you're looking at.
  * Direct NSE JSON (``nseindia.com/api``) is intentionally avoided as a hard dependency: it requires a
    cookie handshake and routinely blocks datacenter IPs. Yahoo's redistribution is the reliable free path.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

from astroquant.agents.base import get_logger
from astroquant.collectors.sources.market_sources import Bar, SyntheticSource

log = get_logger("source.india")

_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"

# Common index aliases → Yahoo tickers.
NSE_INDEX = {
    "NIFTY": "^NSEI", "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "^CNXFIN", "INDIAVIX": "^INDIAVIX", "NIFTYIT": "^CNXIT",
}
BSE_INDEX = {"SENSEX": "^BSESN", "BSE30": "^BSESN"}

_INTERVAL = {"1d": "1d", "1wk": "1wk", "1mo": "1mo", "5m": "5m", "15m": "15m", "60m": "60m"}


def to_yahoo_symbol(symbol: str, exchange: str) -> str:
    """Map a plain symbol to its Yahoo ticker. ``RELIANCE`` → ``RELIANCE.NS`` / ``RELIANCE.BO``."""
    s = symbol.upper().strip()
    if exchange == "NSE":
        return NSE_INDEX.get(s, s if s.startswith("^") else f"{s}.NS")
    return BSE_INDEX.get(s, s if s.startswith("^") else f"{s}.BO")


def _fetch_yahoo(yq_symbol: str, interval: str, start: date, end: date, retries: int = 3) -> dict:
    iv = _INTERVAL.get(interval, "1d")
    p1 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp()) + 86_400
    url = _YAHOO.format(sym=urllib.parse.quote(yq_symbol)) + f"?period1={p1}&period2={p2}&interval={iv}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AstroQuant-OS research)"})
    last: Exception | None = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001 — network is best-effort
            last = e
            time.sleep(1.0 * (i + 1))
    raise ConnectionError(f"Yahoo fetch failed for {yq_symbol}: {last}")


def parse_yahoo_chart(symbol: str, interval: str, source: str, data: dict) -> list[Bar]:
    """Turn a Yahoo chart JSON payload into provider-stamped Bars (skips null/holiday rows)."""
    result = data["chart"]["result"][0]
    ts = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    bars: list[Bar] = []
    for i, t in enumerate(ts):
        o, h, l, c = quote["open"][i], quote["high"][i], quote["low"][i], quote["close"][i]
        v = quote.get("volume", [None] * len(ts))[i]
        if None in (o, h, l, c):
            continue
        bars.append(Bar(
            symbol=symbol, ts=datetime.fromtimestamp(t, tz=timezone.utc).replace(tzinfo=None),
            interval=interval, open=float(o), high=float(h), low=float(l), close=float(c),
            volume=int(v or 0), oi=None, source=source,
        ))
    return bars


class _YahooBackedIndiaSource:
    exchange = "NSE"
    name = "nse"

    def __init__(self, fallback_synthetic: bool = True) -> None:
        self.fallback_synthetic = fallback_synthetic

    def history(self, symbol: str, interval: str, start: date, end: date) -> list[Bar]:
        yq = to_yahoo_symbol(symbol, self.exchange)
        try:
            bars = parse_yahoo_chart(symbol, interval, self.name, _fetch_yahoo(yq, interval, start, end))
            if bars:
                log.info("%s: %d real bars for %s (%s)", self.name, len(bars), symbol, yq)
                return bars
            raise ConnectionError("empty result")
        except Exception as e:  # noqa: BLE001
            if not self.fallback_synthetic:
                raise
            log.warning("%s: live fetch failed (%s); using synthetic fallback for %s",
                        self.name, type(e).__name__, symbol)
            syn = SyntheticSource().history(symbol, interval, start, end)
            for b in syn:
                b.source = f"{self.name}:synthetic"
            return syn


class NSESource(_YahooBackedIndiaSource):
    """National Stock Exchange of India — free EOD/intraday via Yahoo (.NS)."""
    exchange = "NSE"
    name = "nse"


class BSESource(_YahooBackedIndiaSource):
    """Bombay Stock Exchange — free EOD/intraday via Yahoo (.BO)."""
    exchange = "BSE"
    name = "bse"
