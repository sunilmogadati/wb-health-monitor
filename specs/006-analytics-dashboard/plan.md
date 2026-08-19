# Implementation Plan: Analytics Dashboard UI (spec 006)

**Status**: For review · **Spec**: `spec.md` · **Owner**: AR_dev

## Summary

A React / Next.js (App Router) app in `frontend/`, styled with Tailwind CSS, that consumes the
spec-005 read API and renders the value-for-money benchmark, indicator trends, and country
comparisons. Reads only the API — never the database.

## Technical context

- **Consumes**: spec-005 endpoints `GET /countries`, `/timeseries?country=&indicator=`,
  `/compare?countries=&indicator=`, `/benchmark?year=` (see the 005 Key Entities contract).
- **UI**: Next.js (App Router) + Tailwind CSS in `frontend/`; charts via a React library
  (Recharts or Tremor). Own dev server (`npm run dev`, port 3000).
- **Prereq to integrate**: spec-005 API running (`make up` + its prereqs). Until then, mock the four
  endpoints against the contract.

## Constitution check (gate)

- **III Governed** ✅ UI reads only the spec-005 API; never the DB.
- **V Honest modeling** ✅ benchmark labelled "above/near/below what spending predicts", no blame.
- **II Test-backed** ✅ component tests with mocked API data, written first.
- **I Public data** ✅; no secrets in the client.

## Design decisions

1. **Next.js + Tailwind app in `frontend/`** — App Router pages/components. Runs as its own dev server
   on port 3000 (already in the API's `CORS_ALLOWED_ORIGINS`).
2. **One typed API client** (`frontend/lib/api.ts`) — all four calls in one module, base URL from
   `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000/api/v1`). The contract lives here (FR-007).
3. **Three chart components** (Recharts / Tremor): benchmark bar, trend line, compare line. Axis/labels
   say "life expectancy vs. what spending predicts"; benchmark bands are above/near/below — never
   best/worst.
4. **Graceful states** — benchmark handles `model_built: false` ("model not built yet"); a missing
   value renders as a gap; API-unreachable shows an error state.

## Data flow

`(spec-005 API JSON) → typed API client → Next.js/React + Tailwind components → charts`

## Files

- a `frontend/` Next.js + Tailwind app: App Router pages, `lib/api.ts` (typed client + response types),
  three chart components, a benchmark "model not built" state
- component tests under `frontend/` (mocked API responses)

## Testing

- Components render the benchmark, a trend, and a comparison from mocked API data (SC-001).
- Benchmark renders the graceful state on `model_built: false` (SC-002).
- No causal/blame strings in UI copy (SC-003).
- API client points only at the configured base URL (SC-005).
