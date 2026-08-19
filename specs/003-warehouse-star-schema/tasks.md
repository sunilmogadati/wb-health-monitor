# Tasks: Warehouse — Conformed Star Schema (spec 003)

**Status**: Built · **Plan**: `plan.md` · *(All complete — documents the delivered work.)*

## Phase 1 — dbt project
- [x] **T001** `backend/dbt/` scaffolding: `dbt_project.yml`, `profiles.yml`, `models/`, `macros/`, `tests/`. (FR-009)
- [x] **T002** `generate_schema_name` macro so `warehouse` / `published` schemas land literally.
- [x] **T003** `models/staging/sources.yml` declaring `staging.wdi_observation` as the source.

## Phase 2 — Dimensions + fact
- [x] **T004** `dim_country`, `dim_indicator`, `dim_year` — surrogate + natural keys. (FR-001/FR-002/FR-003)
- [x] **T005** `fact_indicator` — grain country×indicator×year, FK to dims, UNIQUE on the 3-key tuple. (FR-004/FR-006)

## Phase 3 — Published mart
- [x] **T006** `published.country_year_indicators` — pivoted wide view, the single read surface. (FR-007)

## Phase 4 — Tests + gate
- [x] **T007** dbt tests: dim uniqueness/not-null, referential integrity, grain-uniqueness. (FR-008)
- [x] **T008** `make dbt-build` builds `staging → warehouse → published` and runs tests (24 PASS). (SC-001..006)
