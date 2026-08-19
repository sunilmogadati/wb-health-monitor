# Feature Specification: Analytics Dashboard

**Feature Branch**: `005-analytics-dashboard`

**Created**: 2026-08-19

**Status**: Accepted (2026-08-19)

**Clarifications (2026-08-19)**: FR-007 — the UI is a **lightweight page served by FastAPI** (one
HTML/JS page + a chart lib reading the JSON API). No new service; Streamlit/Next.js are not used for
the core. Spec accepted — ready to implement.

**Input**: A read API + a dashboard UI over the `published` mart (and the model residuals from spec
002). It shows the **value-for-money benchmark** — which countries over/under-perform their health
spending — plus indicator trends and country comparisons. The UI reads only the API; the API reads
only `published`.

> **Constitution alignment:** Principle III (reads only the `published` zone — the UI never touches
> `staging`/`warehouse`/`raw` directly), Principle V (**honest modeling** — value-for-money /
> association, never causal or "failing"), Principle II (tests before code).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Value-for-money benchmark (Priority: P1)

A user sees a ranked view of countries by **residual** (actual − predicted life expectancy) — who gets
more/less health outcome than their spending predicts — clearly labelled as an association with
spending, not a judgement.

**Acceptance**:
1. **Given** `published.model_residual` exists, **When** the benchmark loads, **Then** countries are
   ranked by residual with the framing "above / near / below what spending predicts".
2. **Given** the model hasn't been built yet (no `model_residual`), **When** the benchmark loads,
   **Then** the UI shows a clear "model not built yet" state instead of erroring.

### User Story 2 — Indicator trends & country compare (Priority: P1)

A user picks a country and an indicator and sees its trend over the years, and can compare a few
countries on the same chart.

**Acceptance**:
1. **Given** the mart, **When** a country + indicator are selected, **Then** a time-series chart
   (2015–2022) renders from the mart values.
2. **Given** multiple countries selected, **Then** they render on one comparison chart.

### User Story 3 — Governed read path (Priority: P2)

**Acceptance**: the UI calls only the API; the API queries only `published.country_year_indicators`
and `published.model_residual` — never `staging`/`warehouse`/`raw` (Principle III).

### Edge Cases

- An indicator missing for a country-year → the chart shows a gap, not a zero.
- `model_residual` absent → benchmark degrades gracefully (US1 #2).

## Requirements *(mandatory)*

- **FR-001**: A read API MUST expose, over the `published` zone only:
  `GET /api/v1/countries` (list), `GET /api/v1/timeseries?country=&indicator=` (a country's values by
  year), `GET /api/v1/compare?countries=&indicator=` (several countries), and
  `GET /api/v1/benchmark?year=` (countries ranked by residual, from `published.model_residual`).
- **FR-002**: The dashboard UI MUST render (a) the value-for-money **benchmark**, (b) **indicator
  trends**, and (c) a **country comparison**, from the API.
- **FR-003**: All framing MUST be value-for-money / association — labels like "above/below what
  spending predicts", never "best/worst" or "failing" (Principle V).
- **FR-004**: The benchmark MUST degrade gracefully when `published.model_residual` is absent (show a
  "model not built yet" state, not an error).
- **FR-005**: The API MUST read **only** `published.*`; nothing user-facing reads other zones.
- **FR-006**: The feature MUST be covered by tests: each endpoint returns the expected shape; the
  benchmark handles the residuals-absent case.
- **FR-007**: The UI is a **lightweight page served by FastAPI** — one HTML/JS page + a chart lib
  (Plotly/Chart.js via CDN) that reads the JSON API. No new service, no build step. *(Clarified.)*

### Key Entities

- **CountrySummary**: `country_code, country_name`.
- **TimeSeriesPoint**: `year, indicator, value`.
- **BenchmarkRow**: `country_code, country_name, year, actual, predicted, residual, band (above/near/below)`.

## Success Criteria *(mandatory)*

- **SC-001**: Each read endpoint returns correct data from the mart (verified against a direct query).
- **SC-002**: The dashboard renders the benchmark, a trend, and a comparison from live API data.
- **SC-003**: With no `model_residual`, the benchmark shows the graceful state and the rest still works.
- **SC-004**: No causal/blame language anywhere in the API or UI (reviewer checklist).
- **SC-005**: `make test` covers the endpoints; nothing reads outside `published`.

## Out of Scope

- Model training (spec 002) and the RAG NL-query (spec 004) — this consumes their outputs.
- Auth / user accounts.
- Sub-national or map-tile geodata (a simple ranked list/bar is enough; a choropleth is a stretch).

## Notes for the plan phase

- Depends on spec 003 (`published` mart — built) and, for the benchmark, spec 002
  (`published.model_residual`). Build the trends/compare first (mart-only), benchmark second.
- Keep the read API thin: parameterized `SELECT`s over `published`, returning JSON.
