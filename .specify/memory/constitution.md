<!--
SYNC IMPACT REPORT
==================
Version change: (stamped placeholder) → 1.0.0
Bump rationale: Initial constitution for the wb-health-monitor capstone, authored from the
  approved Project Brief's non-negotiables. Replaces the Spec-Kit example constitution that
  ships in the starter. MAJOR baseline — establishes binding governance where none existed.

Status: RATIFIED 1.0.0 — reviewed and adopted by the cohort in the kickoff session (2026-08-18).

Principles defined:
  I.   Public Data Only (NON-NEGOTIABLE)
  II.  Spec-Driven, Test-Backed Change (NON-NEGOTIABLE)
  III. Governed Data Pipeline — Zone Discipline
  IV.  Conformed Dimensional Model
  V.   Honest Modeling & Claims (NON-NEGOTIABLE)
  VI.  Reproducible, Containerized Delivery

Added sections:
  - Scope & Data Boundaries
  - Development Workflow & Quality Gates
  - Governance

Follow-up TODOs: cohort ratification; confirm the compliance regime (ai-security) at stamp
  config; add a web-service section if the dashboard is built as a separate Next.js service.
-->

# wb-health-monitor Constitution

**wb-health-monitor** is a spec-driven, test-driven data platform that turns **World Bank open
health data** into a benchmarking tool: it ingests indicators, curates them through a governed
pipeline, trains and evaluates models to surface where health systems under-perform relative to
spending, serves the result over an API, and presents a country → region dashboard. These
principles are binding on all changes.

## Core Principles

### I. Public Data Only (NON-NEGOTIABLE)

The platform operates on **public World Bank Open Data only**.

- Data is pulled from the **World Development Indicators via `wbgapi`** — no scraping, no
  credentialed sources, no third-party private feeds.
- **No personal, private, or otherwise identifying data of any kind, ever.** By construction this
  system holds none; a change that could introduce it is rejected.
- **No secrets in the repo.** No API keys or credentials are required or committed; `.env`
  holds only local ports and dev DB credentials and is git-ignored.

### II. Spec-Driven, Test-Backed Change (NON-NEGOTIABLE)

We do not vibe-code. Every feature is specified first and tested first.

- **Spec before code.** Each feature begins from an approved `spec.md` (via `/speckit.specify`);
  a plan passes the **Constitution Check** before and after design.
- **Tests before implementation.** Write the failing test, then implement until it passes —
  data-quality tests, model-evaluation tests, and API tests.
- **CI is a gate.** `/csi.preflight` (lint, typecheck, full test suite, no secrets) MUST be
  green before any PR. No code merges without a passing test that covers its behavior.

### III. Governed Data Pipeline — Zone Discipline

Data moves through zones and only ever moves **forward**.

- **Zones:** `raw → staging → warehouse → published`. **Nothing user-facing (API or dashboard)
  reads `raw` or `staging`** — only `published` (and the warehouse via the model step).
- **Quality gates promotion.** Blocking-severity data-quality failures (uniqueness, range,
  freshness, not-null) **halt** promotion from one zone to the next.
- **Ingestion is idempotent and logged.** Every pull is re-runnable and writes a `pull_log`
  row (a sync log); raw pulls are immutable.

### IV. Conformed Dimensional Model

The warehouse is a **Kimball star schema**, and stays one.

- **One fact, conformed dimensions:** `fact_indicator` (grain = one measurement:
  entity × indicator × year) referencing `dim_entity`, `dim_indicator`, `dim_time`.
- **Grain is explicit** per fact; new measures **reuse** existing conformed dimensions rather
  than inventing parallel ones.
- **Codes are reference data.** Indicator codes and country/region codes are treated as a
  code system (code + name + unit + polarity), not free text.

### V. Honest Modeling & Claims (NON-NEGOTIABLE)

The platform benchmarks **systems**, not **investments**, and says so.

- **Value-for-money, not attribution.** The model compares outcomes to **national health
  spending** (a residual = the performance gap). It MUST NOT claim causal impact, and MUST NOT
  attribute any outcome to a specific World Bank operation or investment.
- **Compare, don't cherry-pick.** Train and evaluate **multiple** models with appropriate
  metrics; report them honestly. The evaluation report **states the correlational limitation
  plainly**.
- **Scope is country / WB-region.** No sub-national claims (a known data limit).

### VI. Reproducible, Containerized Delivery

Anyone can run the whole thing from a clean clone.

- **One-command dev loop.** The full stack comes up via `docker compose` / `make up`, with the
  source bind-mounted at `/workspace`. A `curl /health` check passes before the UI is opened.
- **Deployed prototype.** The model ships behind **FastAPI** (`/api`, `/health`, `/metrics`)
  and/or a dashboard — the official capstone deliverable.
- **Documented.** README + architecture docs stay in sync with behavior; the demo is
  reproducible.

## Scope & Data Boundaries

- **In scope:** WB WDI health/economic indicators; country and WB-region level; the four core
  indicators (life expectancy, under-5 mortality, health spend %GDP, UHC coverage) plus
  context features.
- **Out of scope:** any sub-national data; any WB project/financing ledger; any non-public
  source; any personal data.
- **Reuse licensing:** copy code only from permissively-licensed sources (MIT/Apache). Ideas
  and methods from unlicensed repos may be **reproduced in our own code** and cited — never
  pasted verbatim.

## Development Workflow & Quality Gates

- **Lifecycle:** `/speckit.constitution → specify → clarify → plan → tasks → implement →
  converge`; hard tasks run the **RPI loop** (`/rpi`: research → plan → implement → review).
- **Ticket ownership (IKEA effect).** `tasks.md` becomes GitHub issues (`/speckit.taskstoissues`);
  each team member owns a ticket **end to end** — spec-check → tests → build → PR.
- **Gates:** `/csi.preflight` (lint, typecheck, tests, secret scan) before every PR;
  `/csi.feature-exit` for Definition of Done; `/csi.retro` at session end.
- **Branch naming:** `<type>/<issue>-<slug>` with `<type>` ∈ {feat, fix, docs, chore}.
- **PRs are focused** and MUST pass all gates, add/extend tests for new behavior, and update
  docs when behavior changes.

## Governance

This constitution supersedes ad-hoc convention where they conflict.

- **Authority.** All principles are binding gates. The `## Constitution Check` of the plan
  template MUST be evaluated against them, and `/speckit.analyze` treats a conflict with a MUST
  as CRITICAL. Violations are resolved by changing the spec, plan, or tasks — never by diluting
  a principle. Principles I, II, and V are **NON-NEGOTIABLE**.
- **Amendments.** Changes require a PR with rationale, team approval, and a version bump per the
  policy below, with the change recorded in the Sync Impact Report at the top of this file and
  propagated to dependent templates.
- **Versioning (SemVer for governance).** MAJOR = backward-incompatible governance or principle
  removal/redefinition; MINOR = a new principle/section or materially expanded guidance;
  PATCH = clarifications.
- **Compliance review.** Every PR verifies compliance with these principles; any deviation MUST
  be justified in-PR. Unjustified violations block merge.

**Version**: 1.0.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-18
