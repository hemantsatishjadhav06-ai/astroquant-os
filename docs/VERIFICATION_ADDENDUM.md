# Verification Addendum

**Verified:** June 2026, against live sources. The three items flagged in the docs as "verify before
building" are confirmed below. Rates and API terms change — re-check the linked sources before any
production reliance, especially F&O tax rates (revised frequently in Union Budgets).

---

## 1. Swiss Ephemeris licensing — CONFIRMED (affects `000` §3)

- **Dual license:** a developer using any part of Swiss Ephemeris must choose **either** (a) **GNU AGPL-3.0**, **or** (b) the **Swiss Ephemeris Professional License** from Astrodienst AG.
- **AGPL implication:** choosing AGPL obligates you to place your **entire** software project under AGPL (or a compatible license). Critically, AGPL's network clause means that if Swiss-Ephemeris-backed calculations are exposed **over a network/API/SaaS**, the copyleft propagates to all downstream users — i.e. you'd have to open-source the whole platform.
- **Professional license cost:** one-time fixed fee per commercial programming project — **CHF 750** for the first license (~USD 500), **CHF 400** for each additional (~USD 270). License validity stated as 99 years.
- **Underlying data:** based on NASA JPL DExxx ephemerides; as of 2026 the `.se1` data files were rebuilt on **DE441**. Lahiri ayanamsa (for Vedic sidereal work) is supported and the docs even include a comparison method against the *Indian Astronomical Ephemeris*.
- **Decision for AstroQuant OS:** as a **private, non-distributed research platform**, AGPL terms are workable (you're not distributing software or exposing the engine over a public network). **If** it ever becomes a SaaS/API/distributed product, you must either (a) open-source under AGPL, (b) buy the Professional License, or (c) switch to a non-AGPL ephemeris engine. **Record this decision in the repo and keep the ephemeris engine behind a clean interface so it can be swapped.**
- Sources: astro.com/swisseph, the GitHub LICENSE (aloistr/swisseph), and the Professional License contract.

---

## 2. Indian transaction costs — CONFIRMED core rates (affects `011` §3 cost model)

> Implement the cost model as a **versioned config with effective-dates** (already specified in `011`).
> The equity rates below are stable; **F&O STT rates have been revised in recent budgets and sources
> disagree on the exact current figure — verify the live value before trusting paper P&L on F&O.**

**STT (Securities Transaction Tax) — a government tax, non-refundable, not subject to GST:**
- **Equity delivery:** 0.1% on **both** buy and sell.
- **Equity intraday:** 0.025% on **sell side only**.
- **Futures:** charged on **sell side only** (rate revised across recent budgets — sources cite figures in the 0.02%–0.05% range depending on date; **verify current**).
- **Options:** charged on the **premium at sale** and on **intrinsic value if exercised** (rate revised recently — sources cite 0.1%–0.15%; **verify current**). Not charged on option buys squared off before expiry.

**Stamp duty (buy side only, since the unified rules of July 2020):**
- Equity delivery ≈ 0.015% (₹1,500/crore) buy side; intraday ≈ 0.003% (₹300/crore); futures ≈ 0.002%; options ≈ 0.003%. (State variations possible.)

**Exchange transaction charges:** per-crore of turnover, **segment-specific** and periodically revised by NSE/BSE/MCX. Model as a configurable per-segment rate.

**SEBI turnover fee:** ≈ ₹10 per crore of turnover.

**GST:** **18%**, levied on (**brokerage + exchange transaction charges + SEBI turnover fee** + other service charges). **GST is NOT applied to STT or stamp duty** (those are taxes, not services).

**DP (Depository Participant) charges:** flat per ISIN per day on **delivery sells** (≈ ₹13–30 +GST), not on intraday or F&O.

**Brokerage:** broker-dependent (discount brokers commonly flat ~₹20/order for intraday & F&O, often ₹0 for delivery). Model per your assumed broker.

> Net effect for the cost model: per fill, sum `brokerage + STT(segment,side) + exchange_txn(segment) + SEBI_fee + stamp_duty(buy) + DP(delivery sell) + GST*(brokerage+exchange_txn+SEBI_fee)`. Version it by effective-date.
- Sources: Zerodha charges page, ClearTax, Groww, Angel One support, SMC, plus Budget-2026 coverage.

---

## 3. Indian broker / market-data APIs — CONFIRMED baseline (affects `005` §1)

**Zerodha Kite Connect:**
- **Pricing (as of 2026):** **₹500/month per API key** for the paid Connect plan (reduced from ₹2,000 after an NSE regulatory green-signal). The paid plan now **includes live market data AND historical data at no extra cost** (the separate ₹2,000 historical add-on was removed in Feb 2025).
- **Historical depth:** up to ~**10 years of intraday** candle data for NSE/BSE on the paid plan; historical available for active option contracts (**not** expired option contracts); no tick-by-tick historical (1-min is the finest historical granularity).
- **Personal (free) API:** order placement + portfolio, but **NO market data** (neither live nor historical) — not useful as a research data source on its own.
- **Limits/constraints:** WebSocket streams up to **3,000 instruments** per connection; account-level RMS limits (e.g. ~2,000 MIS / 2,000 CO orders per day); **static IP required to place orders** since 1 April 2025 (data endpoints unaffected); **no sandbox** environment; **data redistribution prohibited** by exchange policy (fine for a private research platform; relevant only if you ever expose data externally).

**Upstox Developer API & Angel One SmartAPI:** both offer **free** API access (no monthly data fee), with their own rate limits and instrument-master handling. Good zero-cost options for live/recent data and order simulation feeds.

**Implication for AstroQuant OS:** for a research platform, **Kite Connect at ₹500/mo is the cheapest path to clean 10-year intraday history bundled with live data**, and is the recommended primary. Use a free API (Upstox/SmartAPI) as a secondary cross-check source (satisfies the G1 two-source validation gate in `000` §7). For **deep tick history**, you still need a paid vendor (TrueData/GDFL) — Kite's finest historical granularity is 1-minute. None of this requires order-placement scope (paper trading uses read-only market data only, per `011` §8).
- Sources: Zerodha support + developer forum, Z-Connect, Marketcalls, Chittorgarh.

---

## What did NOT change in the docs
The architecture, agent design, schema, research methodology, paper-trading design, and roadmap stand
as written. These verifications only sharpen the cost model (`011`), the data-source recommendation
(`005`), and the licensing decision (`000`). Treat this addendum as authoritative over any older
inline figures elsewhere in the set.
