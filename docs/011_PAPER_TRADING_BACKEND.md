# Document 011 — Paper Trading Backend

**Priority:** first-class engine component (you asked for this explicitly). It sits between Backtesting
(`010`) and the deferred Live Trader. Its job: take validated signals and run them forward on **live or
replayed market data with simulated execution**, so we learn whether a backtested edge survives contact
with realistic fills, latency, and changing markets — *before any real capital*.

> Position in the flow: `Backtesting (G4) → Paper Trading (G5) → [Live, deferred]`.
> Paper trading is the 6–12-month forward-validation gate. No broker order-placement until G5 passes.

---

## 1. Why paper trading is not "just a backtest that runs daily"

A backtest replays history with full hindsight over the bar. Paper trading must instead:
- act on data **as it arrives**, with no knowledge of the rest of the bar/day;
- model the **gap** between signal time, order time, and fill time (latency);
- model **fills** against realistic liquidity (you don't always get the mid);
- accrue realistic **costs** (brokerage, STT, exchange txn charges, GST, stamp duty, slippage);
- track a real **ledger** (cash, positions, margin) with corporate-action handling;
- expose **live P&L and attribution** so the Performance Auditor (`013`/Agent 13) can compare to backtest expectations.

If paper performance diverges sharply from backtest, that divergence is itself a finding (overfitting / unrealistic backtest costs).

---

## 2. Components

```
                ┌────────────────────────────────────────┐
 signals ─────► │ Strategy Runtime                         │
                │  - consumes signals + live/replay quotes │
                │  - emits intended orders                 │
                └───────────────┬──────────────────────────┘
                                ▼
                ┌────────────────────────────────────────┐
 risk approvals │ Pre-Trade Risk Gate (Agent 10)          │
        ◄──────►│  - position/portfolio/strategy limits   │
                └───────────────┬──────────────────────────┘
                                ▼
                ┌────────────────────────────────────────┐
                │ Simulated Matching Engine                │
                │  - latency model                         │
                │  - fill model (slippage/partial fills)   │
                │  - cost model (Indian charges)           │
                └───────────────┬──────────────────────────┘
                                ▼
                ┌────────────────────────────────────────┐
                │ Ledger & Portfolio                       │
                │  - cash, positions, margin, P&L          │
                │  - corporate actions, MTM                │
                └───────────────┬──────────────────────────┘
                                ▼
                ┌────────────────────────────────────────┐
                │ Attribution & Reporting                  │
                │  - realized/unrealized, by strategy/symbol│
                │  - vs-backtest comparison                │
                └──────────────────────────────────────────┘
```

All state persists to Postgres (`paper_*` tables, see `006`) so a restart resumes exactly. The engine
is event-driven and can run in two modes:
- **Live mode:** consume the broker WebSocket / quote feed in real time.
- **Replay mode:** stream historical bars/quotes at controllable speed for fast forward-test rehearsals (still no hindsight within a bar).

---

## 3. Order, fill, latency, and cost models

### Order types (v1)
`MARKET`, `LIMIT`, `STOP`, `STOP_LIMIT`. Time-in-force: `DAY`, `IOC`.

### Latency model
Each order carries a simulated delay between `signal_ts` → `order_ts` → `fill_ts` (config: e.g. 200–800 ms, or a distribution). This prevents the unrealistic "fill at the exact signal price" that flatters backtests.

### Fill model (be conservative)
- **Market orders:** fill at next available price *plus slippage*. Slippage as a function of (spread, order size vs. recent volume, volatility). Never fill better than the touch.
- **Limit orders:** fill only if the market trades through your price (need quote/tick or bar high/low logic); model partial fills for size beyond displayed liquidity.
- **No look-ahead within the bar:** when running on bars, an order placed at bar *T* fills using bar *T+1* prices (or intrabar quotes if available), never bar *T*'s close that wasn't known when the signal fired.

### Cost model (India-specific — make it a pluggable, versioned module)
Account for, per trade and per segment (equity delivery / intraday / F&O):
- brokerage (per your assumed broker plan),
- **STT** (securities transaction tax — differs by segment & buy/sell),
- exchange transaction charges,
- **GST** (on brokerage + txn charges),
- SEBI turnover fees,
- **stamp duty**,
- for options: per-lot economics and the bid-ask reality of illiquid strikes.

> These rates change with regulation/budgets. Implement the cost model as a **versioned config** with
> an effective-date. **VERIFIED core rates (June 2026, see `VERIFICATION_ADDENDUM.md`):** equity
> delivery STT 0.1% buy+sell; intraday STT 0.025% sell-only; stamp duty buy-side only (since Jul 2020);
> GST 18% on brokerage+exchange+SEBI fees (NOT on STT/stamp duty); SEBI fee ~₹10/cr; DP charge on
> delivery sells. **F&O STT rates were revised in recent budgets — verify the live figure for F&O.**

---

## 4. Ledger & portfolio
- Cash balance, per-symbol positions (qty, avg price), realized & unrealized P&L, mark-to-market at each bar.
- **Margin tracking** for F&O (SPAN+exposure approximation; flag if a position would breach margin).
- **Corporate actions:** apply splits/bonuses/dividends to paper positions exactly as they'd hit a real account.
- **Reconciliation:** ledger invariants checked every bar (cash + MTM positions == equity curve); any violation raises an anomaly.

## 5. Risk integration (Agent 10 / `012`)
Every intended order passes the pre-trade risk gate: position-size limits, max exposure per symbol/sector, portfolio gross/net limits, max-drawdown circuit breaker, per-strategy capital allocation. The gate may **approve, scale, or reject**; rejections are logged with reason and surfaced in reports.

## 6. Attribution & the vs-backtest comparison (the whole point)
- P&L attribution by strategy, symbol, signal family (so you can see if the *astro-driven* portion is actually contributing).
- **Live-vs-backtest tracking:** the Performance Auditor compares realized paper Sharpe/return/drawdown against the backtest's out-of-sample expectation. A persistent shortfall is the canonical sign of overfitting or unrealistic backtest assumptions → signal demoted.
- Decayed signals go to the "graveyard" with a post-mortem.

## 7. The G5 gate (what paper trading must prove)
Paper trading runs **6–12 months** (your stated minimum) before any live discussion. To pass G5:
- realized performance is **statistically consistent** with backtest expectations (within confidence bands; no severe degradation),
- **risk limits never breached**,
- the edge persists **across at least one regime change** observed during the period,
- costs modeled match what a real account would have incurred (sanity-checked).

Only then does the (out-of-scope, compliance-gated) live conversation begin.

## 8. Build order for Claude Code (this component)
1. Ledger + portfolio + invariants (pure, fully unit-tested).
2. Cost model (versioned, India charges) + tests.
3. Matching engine with latency + conservative fill model (replay mode first).
4. Strategy runtime + signal consumption + risk gate wiring.
5. Attribution + vs-backtest comparison + reports.
6. Live mode (broker WebSocket) last — read-only market data only; **no order endpoint is ever called**.

> Hard guard: the paper backend must have **no code path that can place a real broker order.** The live
> broker integration is a separate, deferred module behind G5. Keep them in different packages so it's
> impossible to accidentally route a paper order to a real exchange.
