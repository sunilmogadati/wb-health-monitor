# Feature Specification: Analytics Read API

**Feature Branch**: `005-analytics-api`

**Created**: 2026-08-19

**Status**: Accepted (2026-08-19)

**Input**: A thin FastAPI JSON read API over the `published` mart (and the model residuals from spec
002). It is the **data layer for the dashboard** (spec 006): it exposes the country list, indicator
trends, country comparisons, and the **value-for-money benchmark** (which countries over/under-perform
their health spending). The API reads only `published`.

> **Constitution alignment:** Principle III (reads only the `published` zone — never touches
> `staging`/`warehouse`/`raw`), Principle V (**honest modeling** — value-for-money / association,
> never causal or "failing"), Principle II (tests before code).

> **Split note:** spec 005 (this) is the read API; spec 006 is the React/Next.js dashboard that
> consumes it. They can be built in parallel against the contract below; **005 merges first** so 006
> integrates against live endpoints.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Trends & comparison data (Priority: P1)

A client can list countries, fetch one country's indicator values by year, and fetch several
countries' values for one indicator.

**Acceptance**:
1. **Given** the mart, **When** `GET /countries` is called, **Then** it returns the country list.
2. **Given** the mart, **When** `GET /timeseries?country=&indicator=` is called, **Then** it returns
   that country's values by year (2015–2022).
3. **Given** the mart, **When** `GET /compare?countries=&indicator=` is called, **Then** it returns
   the selected countries' values for that indicator.

### User Story 2 — Value-for-money benchmark (Priority: P1)

A client fetches countries ranked by **residual** (actual − predicted life expectancy) — who gets
more/less health outcome than their spending predicts — clearly framed as an association, not a
judgement.

**Acceptance**:
1. **Given** `published.model_residual` exists, **When** `GET /benchmark?year=` is called, **Then** it
   returns countries ranked by residual, each with a `band` of above/near/below.
2. **Given** the model hasn't been built (no `model_residual`), **When** `GET /benchmark` is called,
   **Then** it returns a documented "model not built yet" payload (not a 500).

### User Story 3 — Governed read path (Priority: P2)

**Acceptance**: every endpoint queries only `published.country_year_indicators` and
`published.model_residual` — never `staging`/`warehouse`/`raw` (Principle III).

### Edge Cases

- An indicator missing for a country-year → the value is `null` (a gap), not `0`.
- `model_residual` absent → `/benchmark` degrades gracefully (US2 #2).
- Unknown country/indicator → empty result, not an error.

## Requirements *(mandatory)*

- **FR-001**: The API MUST expose, over the `published` zone only:
  `GET /api/v1/countries` (list), `GET /api/v1/timeseries?country=&indicator=` (a country's values by
  year), `GET /api/v1/compare?countries=&indicator=` (several countries, one indicator), and
  `GET /api/v1/benchmark?year=` (countries ranked by residual, from `published.model_residual`).
- **FR-002**: Each endpoint MUST be a **thin, parameterized `SELECT`** over `published` — no free-form
  SQL, no string-built queries.
- **FR-003**: `/benchmark` MUST degrade gracefully when `published.model_residual` is absent — return a
  documented "model not built yet" payload with a flag, not an error.
- **FR-004**: The API MUST read **only** `published.*`; no endpoint reads other zones.
- **FR-005**: Response framing MUST be value-for-money / association — the benchmark `band` is
  above/near/below, never "best/worst" or "failing" (Principle V). No computed field or label implies
  blame.
- **FR-006**: The feature MUST be covered by tests: each endpoint returns the expected shape/values
  (asserted against a direct mart query); `/benchmark` handles the residuals-absent case.
- **FR-007**: CORS MUST allow the dashboard origin so browser calls from spec 006 succeed (driven by
  `CORS_ALLOWED_ORIGINS`; already wired in `app.main` — confirm, don't rebuild).

### Key Entities *(the contract spec 006 builds against)*

- **CountrySummary**: `country_code, country_name`.
- **TimeSeriesPoint**: `year, indicator, value` (`value` nullable).
- **BenchmarkRow**: `country_code, country_name, year, actual, predicted, residual, band` (band ∈
  `above` | `near` | `below`).
- **BenchmarkResponse** (when the model is absent): `{ "model_built": false, "rows": [] }`.

## Success Criteria *(mandatory)*

- **SC-001**: Each read endpoint returns correct data from the mart (verified against a direct query).
- **SC-002**: `/benchmark?year=` returns residual-ranked rows with correct bands when the model exists.
- **SC-003**: With no `model_residual`, `/benchmark` returns the graceful payload and the other three
  endpoints still work.
- **SC-004**: No causal/blame language anywhere in the API responses or field names (reviewer check).
- **SC-005**: `make test` covers the endpoints; nothing reads outside `published`.

## Out of Scope

- The dashboard UI (spec 006 — consumes this API).
- Model training (spec 002) and the RAG NL-query (spec 004) — this exposes / consumes their outputs.
- Auth / user accounts; write endpoints of any kind.

## Notes for the plan phase

- Depends on spec 003 (`published` mart — built) and, for the benchmark, spec 002
  (`published.model_residual`). Build the trends/compare first (mart-only), benchmark second.
- Keep each endpoint thin: a parameterized `SELECT` over `published`, returning JSON.
