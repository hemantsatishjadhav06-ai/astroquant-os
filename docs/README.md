# AstroQuant OS — Master Documentation Set

> A research platform that scientifically tests whether astrology (Vedic/astronomical),
> Gann theory, technical analysis, options flow, news sentiment, and macro signals have
> **real, measurable predictive edge** in Indian markets (NSE / BSE / MCX).
>
> **Founding principle:** Nothing is assumed true. Everything is tested.
> The single most important question the platform must answer:
> **"Do astrology / Gann features add predictive power *beyond* standard technical indicators?"**
>
> This is a **research lab**, not a live-trading product. Live capital is deferred until
> the research layer proves an edge and the paper-trading backend validates it over 6–12 months.

---

## How to read this set (for humans and for Claude Code)

These documents are written so an AI coding agent can navigate them and build the system
incrementally. Read in this order:

| # | Document | Purpose | Priority |
|---|----------|---------|----------|
| 000 | `000_MASTER_SPEC.md` | The spine. Architecture, repo layout, tech stack, build order, how all docs interlock. | **CORE — read first** |
| 001 | `001_FOUNDER_VISION.md` | Why this exists, what success/failure looks like. | Context |
| 002 | `002_PRD.md` | What is being built (features, user, scope boundaries). | Context |
| 003 | `003_SYSTEM_ARCHITECTURE.md` | The 8 layers in detail, service boundaries, data flow. | **CORE** |
| 004 | `004_AGENT_ARCHITECTURE.md` | The ~15 agents: responsibilities, I/O, tech, comms. | **CORE** |
| 005 | `005_DATA_PLATFORM.md` | Every data source + collector: market, astro, Gann, news, macro. | **CORE** |
| 006 | `006_DATABASE_DESIGN.md` | Full schema: Postgres + TimescaleDB + MongoDB + Vector DB. | **CORE** |
| 007 | `007_RESEARCH_METHODOLOGY.md` | The anti-self-fooling statistics. The intellectual heart. | **CORE** |
| 008 | `008_FEATURE_FACTORY.md` | 1000+ features/day across technical / astro / Gann / market. | High |
| 009 | `009_AI_ML.md` | Models, feature ablation, SHAP, drift detection. | High |
| 010 | `010_BACKTESTING.md` | Event-driven, walk-forward, Monte Carlo, regime testing. | High |
| 011 | `011_PAPER_TRADING_BACKEND.md` | First-class simulated execution backend. | **CORE** |
| 012 | `012_RISK_MANAGEMENT.md` | Portfolio / position / strategy / system / black-swan risk. | High |
| 013 | `013_IMPLEMENTATION_ROADMAP.md` | 6-month build plan, milestone gates. | **CORE** |
| — | `VERIFICATION_ADDENDUM.md` | Live-verified (June 2026) figures: Swiss Ephemeris license, India transaction costs, broker API pricing. Authoritative over older inline figures. | Reference |

**Build order for Claude Code:** 000 → 006 → 005 → 008 → 007 → 009 → 010 → 011 → 004 → 013.
(Schema and data come before research; research methodology gates everything downstream.)

---

## The non-negotiable rules (encoded in every document)

1. **No look-ahead.** A feature for date *T* may only use information available at the close of *T* (or earlier). Astro/Gann features are exempt from look-ahead only because they are deterministic functions of time — but their *predictive* claims are never exempt from out-of-sample testing.
2. **Pre-register every hypothesis** before touching test data. (See `007`.)
3. **Correct for multiple testing.** Testing thousands of planetary combinations *will* produce false positives. FDR / deflated-Sharpe control is mandatory, not optional.
4. **The technical-only baseline is sacred.** Every astro/Gann claim is measured as *incremental* lift over a model that uses only technical + market features. If it doesn't beat the baseline out-of-sample, it is reported as "no edge found" — and that is a valid, valuable result.
5. **Paper before live. Always.** No broker write-access (order placement) until a milestone gate is formally passed.

---

## Repository layout (target)

```
astroquant-os/
├── docs/                      # this documentation set
├── cpp/                       # performance-critical C++ (ephemeris, Gann, tick backtest)
│   ├── ephemeris/             # Swiss Ephemeris wrapper + sidereal/Lahiri calcs
│   ├── gann/                  # Square of Nine, angles, price-time squaring
│   └── backtest_engine/       # tick-level event-driven engine
├── python/
│   ├── astroquant/
│   │   ├── collectors/        # Agents 1–5 (data collection)
│   │   ├── features/          # Feature Factory (Agent 6)
│   │   ├── research/          # Pattern Discovery, Research Analyst (Agents 7–8)
│   │   ├── backtest/          # Backtester wrapper (Agent 9)
│   │   ├── risk/              # Risk Manager (Agent 10)
│   │   ├── paper/             # Paper Trading backend (Agent 11)
│   │   ├── audit/             # Performance Auditor, Anomaly Detector (Agents 13,15)
│   │   ├── reporting/         # Report Generator (Agent 14)
│   │   ├── orchestrator/      # the conductor + n8n hooks
│   │   ├── db/                # SQLAlchemy models, migrations, repositories
│   │   └── common/            # config, logging, message bus, types
│   └── pyproject.toml
├── sql/                       # migrations (Alembic) + TimescaleDB setup
├── infra/                     # docker-compose, env, message queue config
├── notebooks/                 # exploratory research (NOT production)
└── tests/
```

---

## Glossary (so terms are unambiguous across docs)

- **Edge** — statistically significant, out-of-sample, post-cost predictive ability that survives multiple-testing correction.
- **Baseline model** — a model using only technical + market features. The control group.
- **Astro feature** — any feature derived from planetary positions (sidereal/Lahiri), transits, nakshatras, dashas, moon phase, retrogrades.
- **Gann feature** — day/cycle counts, Square-of-Nine levels, Gann angles, price-time squaring.
- **Ablation** — training the same model with and without a feature group to measure that group's incremental contribution.
- **DSR** — Deflated Sharpe Ratio (Bailey & López de Prado): a Sharpe ratio corrected for the number of strategies tried.
- **RQ** — Research Question (pre-registered). E.g. RQ-004: "Do planetary features add predictive power beyond technical indicators?"

---

*Generated as the working spec for AstroQuant OS. Treat `000_MASTER_SPEC.md` as the source of truth when documents conflict.*
