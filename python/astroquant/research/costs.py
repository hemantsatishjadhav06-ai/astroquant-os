"""
India transaction-cost model (docs/011 §3, rates per docs/VERIFICATION_ADDENDUM.md, June 2026).

Versioned by effective-date. Equity rates are stable; F&O STT was revised in recent budgets —
the F&O figures here are a configurable baseline and MUST be re-verified before trusting F&O P&L.

Per-fill total =
    brokerage + STT(segment,side) + exchange_txn(segment) + sebi_fee
    + stamp_duty(buy only) + dp_charge(delivery sell)
    + GST * (brokerage + exchange_txn + sebi_fee)        # GST NOT on STT or stamp duty
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Segment(str, Enum):
    EQUITY_DELIVERY = "equity_delivery"
    EQUITY_INTRADAY = "equity_intraday"
    FUTURES = "futures"
    OPTIONS = "options"


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class CostConfig:
    """All rates as fractions of turnover unless noted. effective_date for versioning."""
    effective_date: str = "2026-06-01"
    # STT
    stt_delivery: float = 0.001          # 0.1% both sides
    stt_intraday_sell: float = 0.00025   # 0.025% sell side only
    stt_futures_sell: float = 0.0002     # 0.02% sell side (VERIFY — revised in budgets)
    stt_options_sell: float = 0.001      # 0.1% on premium sell (VERIFY — revised in budgets)
    # stamp duty (buy side only, since Jul 2020)
    stamp_delivery_buy: float = 0.00015  # 0.015%
    stamp_intraday_buy: float = 0.00003  # 0.003%
    stamp_futures_buy: float = 0.00002   # 0.002%
    stamp_options_buy: float = 0.00003   # 0.003%
    # exchange transaction charges (per-segment, configurable; NSE baseline-ish)
    exch_equity: float = 0.0000297       # ~0.00297%
    exch_futures: float = 0.0000173
    exch_options: float = 0.0003503      # on premium
    # SEBI turnover fee (~Rs 10 per crore = 1e-6)
    sebi_fee: float = 0.000001
    # GST on (brokerage + exchange + sebi)
    gst: float = 0.18
    # brokerage: flat per executed order (discount-broker style); 0 for delivery is common
    brokerage_flat: float = 20.0
    brokerage_delivery_flat: float = 0.0
    # DP charge on delivery sells (per ISIN per day), incl. GST already
    dp_charge_delivery_sell: float = 15.34


@dataclass
class CostBreakdown:
    brokerage: float
    stt: float
    exchange: float
    sebi: float
    stamp_duty: float
    dp: float
    gst: float
    total: float


def compute_costs(
    turnover: float, segment: Segment, side: Side, cfg: CostConfig | None = None
) -> CostBreakdown:
    """turnover = price * qty (for options, the premium turnover)."""
    c = cfg or CostConfig()

    # brokerage
    if segment == Segment.EQUITY_DELIVERY:
        brokerage = c.brokerage_delivery_flat
    else:
        brokerage = c.brokerage_flat

    # STT
    stt = 0.0
    if segment == Segment.EQUITY_DELIVERY:
        stt = turnover * c.stt_delivery
    elif segment == Segment.EQUITY_INTRADAY and side == Side.SELL:
        stt = turnover * c.stt_intraday_sell
    elif segment == Segment.FUTURES and side == Side.SELL:
        stt = turnover * c.stt_futures_sell
    elif segment == Segment.OPTIONS and side == Side.SELL:
        stt = turnover * c.stt_options_sell

    # exchange txn charges
    if segment in (Segment.EQUITY_DELIVERY, Segment.EQUITY_INTRADAY):
        exch = turnover * c.exch_equity
    elif segment == Segment.FUTURES:
        exch = turnover * c.exch_futures
    else:
        exch = turnover * c.exch_options

    # SEBI fee
    sebi = turnover * c.sebi_fee

    # stamp duty — buy side only
    stamp = 0.0
    if side == Side.BUY:
        stamp = turnover * {
            Segment.EQUITY_DELIVERY: c.stamp_delivery_buy,
            Segment.EQUITY_INTRADAY: c.stamp_intraday_buy,
            Segment.FUTURES: c.stamp_futures_buy,
            Segment.OPTIONS: c.stamp_options_buy,
        }[segment]

    # DP charge — delivery sells only
    dp = c.dp_charge_delivery_sell if (segment == Segment.EQUITY_DELIVERY and side == Side.SELL) else 0.0

    # GST on (brokerage + exchange + sebi); NOT on STT or stamp duty
    gst = c.gst * (brokerage + exch + sebi)

    total = brokerage + stt + exch + sebi + stamp + dp + gst
    return CostBreakdown(
        brokerage=round(brokerage, 4), stt=round(stt, 4), exchange=round(exch, 4),
        sebi=round(sebi, 4), stamp_duty=round(stamp, 4), dp=round(dp, 4),
        gst=round(gst, 4), total=round(total, 4),
    )
