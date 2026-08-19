# Feature Specification: Analytics Dashboard (UI)

**Feature Branch**: `006-analytics-dashboard`

**Created**: 2026-08-19

**Status**: Accepted (2026-08-19)

**Depends on**: **spec 005 (Analytics Read API)** — this consumes its endpoints. Build in parallel
against the 005 contract (mock the data if 005 hasn't merged yet); integrate once 005 is live.

**Input**: A **React / Next.js (App Router) app styled with Tailwind CSS** (a separate `frontend/`)
that consumes the spec-005 JSON read API. It shows the **value-for-money benchmark** (which countries
over/under-perform their health spending), indicator **trends**, and country **comparisons**. The UI
reads only the API — never the database.

> **Constitution alignment:** Principle III (reads only via the API, which reads only `published`),
> Principle V (**honest modeling** — value-for-money / association, never causal or "failing"),
> Principle II (tests before code).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Value-for-money benchmark (Priority: P1)

A user sees a ranked view of countries by **residual** (actual − predicted life expectancy) — who gets
more/less health outcome than their spending predicts — clearly labelled as an association with
spending, not a judgement.

**Acceptance**:
1. **Given** `/benchmark` returns residual rows, **When** the benchmark loads, **Then** countries are
   ranked with the framing "above / near / below what spending predicts".
2. **Given** `/benchmark` returns `model_built: false`, **When** the benchmark loads, **Then** the UI
   shows a clear "model not built yet" state instead of erroring.

### User Story 2 — Indicator trends & country compare (Priority: P1)

A user picks a country and an indicator and sees its trend over the years, and can compare a few
countries on the same chart.

**Acceptance**:
1. **Given** `/timeseries`, **When** a country + indicator are selected, **Then** a time-series chart
   (2015–2022) renders.
2. **Given** `/compare`, **When** multiple countries are selected, **Then** they render on one
   comparison chart.

### User Story 3 — Governed read path (Priority: P2)

**Acceptance**: the UI calls only the spec-005 API — it never queries the database directly
(Principle III).

### Edge Cases

- An indicator missing for a country-year (API returns `null`) → the chart shows a gap, not a zero.
- `/benchmark` returns `model_built: false` → benchmark degrades gracefully (US1 #2); trends/compare
  still work.
- API unreachable → a clear error state, not a blank screen.

## Requirements *(mandatory)*

- **FR-001**: The UI MUST be a **React / Next.js (App Router) app styled with Tailwind CSS** in a
  separate `frontend/` (own dev server, port 3000). **Not** a FastAPI-served page, **not** Streamlit.
- **FR-002**: The dashboard MUST render, from the spec-005 API: (a) the value-for-money **benchmark**,
  (b) **indicator trends**, and (c) a **country comparison** — charts via a React chart library
  (Recharts / Tremor).
- **FR-003**: All framing MUST be value-for-money / association — labels like "above/below what
  spending predicts", never "best/worst" or "failing" (Principle V).
- **FR-004**: The benchmark MUST degrade gracefully when the API reports `model_built: false` (show a
  "model not built yet" state, not an error).
- **FR-005**: The UI MUST read **only** the spec-005 API; it never touches the database or any zone
  directly.
- **FR-006**: The feature MUST be covered by tests: components render the expected charts from mocked
  API data; the benchmark handles the `model_built: false` case; no causal/blame copy.
- **FR-007**: The UI MUST call the API through a single typed API client module (base URL from an env
  var, e.g. `NEXT_PUBLIC_API_BASE`), so the endpoint contract lives in one place.

### Key Entities *(consumed from the spec-005 contract)*

- **CountrySummary**: `country_code, country_name`.
- **TimeSeriesPoint**: `year, indicator, value` (nullable).
- **BenchmarkRow**: `country_code, country_name, year, actual, predicted, residual, band` (above/near/below).

## Success Criteria *(mandatory)*

- **SC-001**: The dashboard renders the benchmark, a trend, and a comparison from live API data.
- **SC-002**: With the API reporting `model_built: false`, the benchmark shows the graceful state and
  the rest still works.
- **SC-003**: No causal/blame language anywhere in the UI copy (reviewer checklist).
- **SC-004**: Component tests pass with mocked API responses (`make test` / `npm test`).
- **SC-005**: The UI issues requests only to the spec-005 API base URL (no direct DB access).

## Out of Scope

- The read API itself (spec 005 — this consumes it).
- Model training (spec 002) and the RAG NL-query (spec 004).
- Auth / user accounts; sub-national or map-tile geodata (a ranked list/bar is enough).

## Notes for the plan phase

- Build against the spec-005 contract (Key Entities). If 005 hasn't merged, mock the four endpoints,
  then point the API client at the live base URL once 005 lands.
- CORS for `http://localhost:3000` is already wired on the API (spec 005 FR-007); no backend change
  needed from this spec.
