# Tasks: Analytics Dashboard UI (spec 006)

**Status**: For review · **Plan**: `plan.md` · **Owner**: AR_dev · Work in order; each maps to a spec FR / SC.

**Depends on spec 005 (read API).** Build against the 005 contract; mock the endpoints until 005 merges.

## Phase 1 — Scaffold
- [ ] **T001** Scaffold a **Next.js (App Router)** app in `frontend/` with **Tailwind CSS** and a React
  chart library (Recharts / Tremor). Own dev server (`npm run dev`, port 3000). (FR-001)
- [ ] **T002** `frontend/lib/api.ts` — one typed API client for `/countries`, `/timeseries`, `/compare`,
  `/benchmark`, base URL from `NEXT_PUBLIC_API_BASE`; response types from the 005 contract. (FR-007)

## Phase 2 — Tests first (Principle II)
- [ ] **T003** Component tests with **mocked** API responses: benchmark, trend, and compare render; the
  benchmark renders the graceful state on `model_built: false`; no causal/blame copy. (FR-006)

## Phase 3 — Dashboard UI
- [ ] **T004** Benchmark component — countries ranked by residual with bands above/near/below; labels
  "vs what spending predicts" (no best/worst). Graceful "model not built yet" state on
  `model_built: false`. (FR-002/FR-003/FR-004)
- [ ] **T005** Trend component — one country + indicator time series (2015–2022); missing values render
  as a gap, not zero. (FR-002)
- [ ] **T006** Compare component — several countries on one indicator, one chart. (FR-002)
- [ ] **T007** Page/layout wiring the three components; API-unreachable error state. (FR-002/FR-005)

## Phase 4 — Gate
- [ ] **T008** Reviewer check: UI reads only the spec-005 API (no direct DB); no causal/blame copy;
  tests green. (SC-003/SC-004/SC-005)

## Phase 5 — Ship
- [ ] **T009** Integrate against the live spec-005 API (point `NEXT_PUBLIC_API_BASE` at it); PR into
  `develop` **after** spec 005 has merged. Maintainer reviews against Success Criteria.
