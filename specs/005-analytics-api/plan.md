# Implementation Plan: Analytics Read API (spec 005)

**Status**: For review · **Spec**: `spec.md` · **Owner**: SA_dev

## Summary

A thin read API over the `published` zone: the country list, indicator trends, country comparisons,
and the value-for-money benchmark. It is the data layer the spec-006 dashboard consumes. Reads only
`published`.

## Technical context

- **Read surface**: `published.country_year_indicators` (built) and `published.model_residual`
  (from spec 002; may not exist yet — handle gracefully).
- **API**: FastAPI routers in `backend/app/`, thin parameterized `SELECT`s via psycopg. Existing DB
  helpers: `ml.features.connect()` and the mart-row helpers already used by `/predict` and `/brief`.
- **Prereq to run/test**: `make up && make ingest && make dbt-build` (mart) and `make train`
  (`published.model_residual`).

## Constitution check (gate)

- **III Governed** ✅ every endpoint reads only `published`.
- **V Honest modeling** ✅ benchmark `band` = above/near/below, no blame.
- **II Test-backed** ✅ endpoint shape + residuals-absent tests written first.
- **I Public data** ✅; no secrets.

## Design decisions

1. **One router, four thin endpoints** — `GET /countries`, `/timeseries`, `/compare`, `/benchmark`.
   Each is a fixed parameterized `SELECT` over `published`; no free-form SQL. Register under
   `API_V1_PREFIX` in `app.main.create_app()`, next to the existing routers.
2. **Benchmark resilience** — `/benchmark` first checks `published.model_residual` exists (catalog
   query or a guarded `SELECT`); if absent, return `{ "model_built": false, "rows": [] }` (HTTP 200)
   so the UI shows the graceful state. When present, compute `band` from the residual sign/threshold
   (e.g. `> +ε` above, `< −ε` below, else near) — a code constant, not a value judgement.
3. **Null gaps, not zeros** — missing indicator values serialize as `null`.
4. **CORS** — already wired in `app.main` from `CORS_ALLOWED_ORIGINS` (verified live). Confirm
   `.env`/`.env.example` carry `http://localhost:3000`; do not re-add middleware.

## Data flow

`published mart + model_residual → parameterized SELECT → FastAPI JSON → (spec 006 dashboard)`

## Files

- add a read router under `backend/app/` (e.g. `app/analytics.py`) with the four endpoints + Pydantic
  response models (`CountrySummary`, `TimeSeriesPoint`, `BenchmarkRow`, `BenchmarkResponse`)
- register it in `app/main.py::create_app()`
- tests in `backend/tests/`

## Testing

- Each endpoint returns the expected JSON shape and values (assert vs a direct mart query).
- `/benchmark` returns `model_built: false` when `model_residual` is absent, and correct bands when
  present.
- No causal/blame strings in field names or responses (SC-004).
