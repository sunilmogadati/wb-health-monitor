# Tasks: Analytics Dashboard (spec 005)

**Status**: For review · **Plan**: `plan.md` · Work in order; each maps to a spec FR / SC.

## Phase 1 — Read API (published zone only)
- [ ] **T001** `backend/app/` router: `GET /api/v1/countries` — list from `published`. (FR-001/FR-005)
- [ ] **T002** `GET /api/v1/timeseries?country=&indicator=` — one country's values by year. (FR-001)
- [ ] **T003** `GET /api/v1/compare?countries=&indicator=` — several countries, one indicator. (FR-001)
- [ ] **T004** `GET /api/v1/benchmark?year=` — countries ranked by residual from `published.model_residual`; return a "model not built" payload if the table is absent. (FR-001/FR-004)

## Phase 2 — Dashboard UI (React / Next.js / Tailwind)
- [ ] **T005** Scaffold a **Next.js (App Router)** app in `frontend/` with **Tailwind CSS** + a typed API client for the read endpoints; add the frontend origin to `CORS_ALLOWED_ORIGINS`. (FR-007)
- [ ] **T006** Build three chart components (React chart lib — Recharts / Tremor): value-for-money **benchmark**, indicator **trend**, country **compare**. Labels say "vs what spending predicts"; bands above/near/below (no best/worst). (FR-002/FR-003)
- [ ] **T007** Benchmark shows the graceful "model not built yet" state when residuals are absent. (FR-004)

## Phase 3 — Tests & gate
- [ ] **T008** Endpoint tests: each returns the expected shape/values (vs a direct mart query); `/benchmark` handles residuals-absent. (FR-006)
- [ ] **T009** Reviewer check: nothing reads outside `published`; no causal/blame copy. `make test` green. (SC-004/SC-005)

## Phase 4 — Ship
- [ ] **T010** PR into `develop`; maintainer reviews against the spec's Success Criteria.
