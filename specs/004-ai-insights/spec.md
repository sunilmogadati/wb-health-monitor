# Feature Specification: AI Insights — Natural-Language Query over the Published Mart

**Feature Branch**: `004-ai-insights`

**Created**: 2026-08-18

**Status**: Draft

**Input**: Let a user ask a plain-English question about the health data and get a **grounded, cited**
answer, using only the `published.country_year_indicators` mart. Retrieval + an LLM (Claude) turn the
question into an answer that quotes the actual numbers it used — no invented facts.

> **Constitution alignment:** Principle V (**honest modeling** — value-for-money / association, never
> causal or blame), Principle III (reads only the `published` mart), Principle II (tests before code).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ask a question, get a grounded answer (Priority: P1)

A user asks e.g. *"Which Sub-Saharan countries get the most life expectancy for their health
spending?"* and receives a short answer that names countries and **quotes the mart values** it used.

**Acceptance**:
1. **Given** the published mart, **When** a question is asked, **Then** the answer is derived only from
   mart rows and **cites** them (country, year, indicator, value).
2. **Given** a question the data can't answer, **When** it is asked, **Then** the system says so rather
   than inventing numbers.

### User Story 2 — Honest framing (Priority: P1)

**Acceptance**: the answer frames differences as **value-for-money / association with spending**, never
a causal claim or a "country X is failing" judgement (Principle V, spec-002 SC-006 carried forward).

### User Story 3 — Runs offline for tests (Priority: P2)

**Acceptance**: with no LLM API key, the retrieval + a deterministic template answer still run, so CI
passes without network/keys.

## Requirements *(mandatory)*

- **FR-001**: Retrieval MUST run over `published.country_year_indicators` only — either a **SQL-tool
  agent** (question → parameterized SQL → rows) or an **embedding/vector** index of country-year
  summaries. [NEEDS CLARIFICATION: which approach — SQL-tool agent vs vector RAG. Recommendation:
  SQL-tool agent first (the data is small, structured, and exact), vector RAG as a stretch.]
- **FR-002**: The answer MUST be grounded in retrieved rows and MUST include **citations**
  (country, year, indicator, value) for every figure it states.
- **FR-003**: A **no-hallucinated-numbers** guardrail MUST hold: any number in the answer traces to a
  retrieved row; otherwise the system declines.
- **FR-004**: Output framing MUST be association/value-for-money, never causal/blame (Principle V).
- **FR-005**: The LLM MUST be **Claude** (Anthropic), consistent with the project stack.
- **FR-006**: A deterministic **no-API-key fallback** MUST exist so tests run offline.
- **FR-007**: The feature MUST be exposed as an endpoint (`/api/v1/ask`) or CLI, and covered by tests
  (grounding, citation presence, offline fallback).

### Key Entities

- **InsightRequest**: `question` (str).
- **Citation**: `country_code, country_name, year, indicator, value`.
- **InsightResponse**: `answer` (str, grounded), `citations` (list[Citation]), `caveats` (str —
  states the value-for-money framing and any data gaps).

## Success Criteria *(mandatory)*

- **SC-001**: Asking a question returns an answer + at least one citation to a real mart row.
- **SC-002**: Every number in the answer matches a retrieved mart value (no fabrication).
- **SC-003**: Insufficient-data questions return an honest "can't answer from this data".
- **SC-004**: No causal/blame language (reviewer checklist).
- **SC-005**: Runs and tests pass with no API key (deterministic fallback).

## Out of Scope

- Charts / dashboard visuals (spec 005) — this returns text + citations.
- Model training (spec 002) — this reads the mart and, optionally, model residuals if present.

## Notes for the plan phase

- Reuse the structured-output pattern from `backend/ml/brief.py`. The cohort's RAG research
  (`research/AR-life-expectancy/`) is a reference starting point.
- Start with the SQL-tool-agent approach (exact, cheap on this small mart); a vector index is a
  stretch once the SQL path works.
