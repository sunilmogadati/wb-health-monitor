# Implementation Plan: Analytics Dashboard (spec 005)

**Status**: For review · **Spec**: `spec.md` · **Author**: maintainer

## Summary

A thin read API over the `published` zone + a dashboard UI that shows the value-for-money benchmark,
indicator trends, and country comparisons. UI reads the API; API reads only `published`.

## Technical context

- **Read surface**: `published.country_year_indicators` (built) and `published.model_residual`
  (from spec 002; may not exist yet — handle gracefully).
- **API**: FastAPI routers in `backend/app/`, thin parameterized `SELECT`s via psycopg.
- **UI**: a **React / Next.js (App Router) app** in `frontend/`, styled with **Tailwind CSS**, that
  consumes the FastAPI JSON read API. Charts via a React library (Recharts or Tremor). Runs as its own
  dev server (`npm run dev`, port 3000) or a compose `frontend` service.

## Constitution check (gate)

- **III Governed** ✅ API reads only `published`; UI reads only the API.
- **V Honest modeling** ✅ benchmark labelled "above/near/below what spending predicts", no blame.
- **II Test-backed** ✅ endpoint shape + residuals-absent tests.
- **I Public data** ✅; no secrets.

## Design decisions

1. **Read API, thin & parameterized** — `GET /countries`, `/timeseries`, `/compare`, `/benchmark`.
   Each is a fixed `SELECT` over `published`; no free-form SQL. Returns JSON.
2. **Benchmark resilience** — `/benchmark` checks for `published.model_residual`; if absent, returns a
   documented "model not built" payload (204/empty + a flag) so the UI shows the graceful state.
3. **UI = a Next.js + Tailwind app** (`frontend/`) — App Router pages/components fetch the read API and
   render three charts (benchmark bar, trend line, compare line) with a React chart lib (Recharts /
   Tremor). CORS: add the frontend origin (`http://localhost:3000`) to `CORS_ALLOWED_ORIGINS`.
4. **Framing in the UI copy** — axis/labels say "life expectancy vs. what spending predicts"; the
   benchmark bands are above/near/below, never best/worst.

## Data flow

`published mart + model_residual → FastAPI read API (JSON) → Next.js/React + Tailwind app → charts`

## Files

- add routers under `backend/app/` (`/countries`, `/timeseries`, `/compare`, `/benchmark`, `/dashboard`)
- add a `frontend/` **Next.js + Tailwind** app (App Router pages, chart components, a typed API client)
- tests in `tests/`

## Testing

- Each endpoint returns the expected JSON shape and values (assert vs a direct mart query).
- `/benchmark` returns the graceful payload when `model_residual` is absent.
- No causal/blame strings in API/UI copy (SC-004).
