# Tasks: Analytics Read API (spec 005)

**Status**: Accepted & implemented · **Plan**: `plan.md` · **Owner**: SA_dev · Work in order; each maps to a spec FR / SC.

## Phase 0 — Prereqs (run once)
- [x] **T001** Bring the data up: `make up && make ingest && make dbt-build` (mart) and `make train`
  (`published.model_residual`). Confirm both tables have rows.

## Phase 1 — Tests first (Principle II)
- [x] **T002** Write endpoint tests in `backend/tests/`: expected shape/values for `/countries`,
  `/timeseries`, `/compare`, `/benchmark` (assert against a direct mart query); a test that
  `/benchmark` returns `model_built: false` when `model_residual` is absent. (FR-006)

## Phase 2 — Read API (published zone only)
- [x] **T003** `GET /api/v1/countries` — list from `published`. (FR-001/FR-002/FR-004)
- [x] **T004** `GET /api/v1/timeseries?country=&indicator=` — one country's values by year; missing
  values as `null`. (FR-001/FR-002)
- [x] **T005** `GET /api/v1/compare?countries=&indicator=` — several countries, one indicator. (FR-001/FR-002)
- [x] **T006** `GET /api/v1/benchmark?year=` — countries ranked by residual from
  `published.model_residual` with a `band` (above/near/below); return `{ "model_built": false,
  "rows": [] }` if the table is absent. (FR-001/FR-003/FR-005)
- [x] **T007** Register the router in `app/main.py::create_app()`. Confirm CORS is already wired
  (do not re-add). (FR-007)

## Phase 3 — Gate
- [x] **T008** Reviewer check: nothing reads outside `published`; no causal/blame field names or copy;
  `make test` green. (SC-004/SC-005)

## Phase 4 — Ship
- [x] **T009** PR into `develop`; maintainer reviews against Success Criteria. **Merge before spec 006**
  so the dashboard integrates against live endpoints.
