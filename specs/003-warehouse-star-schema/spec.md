# Feature Specification: Warehouse — Conformed Star Schema

**Feature Branch**: `003-warehouse-star-schema`

**Created**: 2026-08-18

**Status**: Draft

**Input**: Turn the flat `staging.wdi_observation` into a **conformed dimensional model** (Kimball star
schema) in a `warehouse` schema, and expose a clean `published` mart that the model (spec 002) and the
dashboard (spec 005) read from. This is the "gold" layer: one set of shared dimensions, one fact table.

> **Constitution alignment:** Principle IV (**Conformed Dimensional Model** — shared dims, a fact at a
> declared grain), Principle III (zone discipline — `staging → warehouse → published`, nothing
> user-facing reads `staging`/`raw` directly), Principle II (tests before code), Principle VI
> (reproducible, idempotent rebuild).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Conformed dimensions (Priority: P1)

An analyst needs stable, deduplicated **dimensions** so every fact joins to the same country, the same
indicator, and the same year — no matter which pipeline run produced it.

**Acceptance**:
1. **Given** staging data, **When** the warehouse is built, **Then** `dim_country`, `dim_indicator`,
   and `dim_year` each hold one row per natural key with a stable surrogate key.
2. **Given** a re-run, **When** the build repeats, **Then** surrogate keys are stable and no duplicate
   dimension rows appear (idempotent).

### User Story 2 — The fact table at a declared grain (Priority: P1)

A modeler needs one **fact** table whose grain is unambiguous: **one row per country × indicator ×
year**, foreign-keyed to the three dimensions, with the observed value.

**Acceptance**:
1. **Given** the dimensions, **When** `fact_indicator` is built, **Then** each row references valid
   `dim_country`, `dim_indicator`, `dim_year` surrogate keys and carries `value`.
2. **Given** the declared grain, **When** the fact is checked, **Then** `(country_key, indicator_key,
   year_key)` is unique (no double-counting).
3. **Given** a staging row with no matching dimension, **When** the fact is built, **Then** the build
   fails loudly (referential integrity), it does not silently drop the row.

### User Story 3 — A published mart for consumers (Priority: P2)

A dashboard/model developer wants a simple, denormalized **`published`** view — country, year, and the
indicators — without having to join the star themselves.

**Acceptance**:
1. **Given** the star, **When** a consumer queries `published.country_year_indicators`, **Then** they
   get one row per country-year with the indicators as columns (the same shape spec 002 features use).
2. **Given** the published mart, **When** anything user-facing reads data, **Then** it reads from
   `published`, never from `staging`/`raw` (Principle III).

### Edge Cases

- An indicator present in staging but not yet in `dim_indicator` → build fails (add it to the dim
  seed), never a silent skip.
- Sparse indicators (e.g. `uhc_index`) still get dimension rows; the fact simply has fewer rows for
  them. Nulls are absence-of-fact, not zero.

## Requirements *(mandatory)*

- **FR-001**: A `warehouse` schema MUST contain `dim_country`, `dim_indicator`, `dim_year`, and
  `fact_indicator`.
- **FR-002**: Each dimension MUST have a surrogate key (PK) and its natural key (UNIQUE):
  `dim_country.country_code`, `dim_indicator.indicator_code`, `dim_year.year`.
- **FR-003**: `dim_country` MUST carry `country_code`, `country_name`, `region`; `dim_indicator` MUST
  carry `indicator_code`, `indicator_name`, and a human description/unit.
- **FR-004**: `fact_indicator` grain MUST be one row per **country × indicator × year**, enforced by a
  UNIQUE constraint on the three foreign keys; it MUST carry `value`.
- **FR-005**: The fact MUST enforce **referential integrity** to all three dimensions (FK constraints
  or an equivalent tested check); orphan facts MUST fail the build.
- **FR-006**: The build MUST be **idempotent** — re-running produces the same warehouse with no
  duplicates and stable surrogate keys.
- **FR-007**: A `published` mart (view or table) MUST expose one row per country-year with the
  indicators, as the single read surface for spec 002 (model) and spec 005 (dashboard).
- **FR-008**: The transform MUST be reproducible in the container and covered by tests: dimension
  uniqueness, fact grain uniqueness, referential integrity, and published row counts.
- **FR-009**: The build MUST be driven by a documented command [NEEDS CLARIFICATION: transform tool —
  **dbt** (`staging → warehouse → published` models, adds `dbt-postgres`) vs plain **SQL in an Alembic
  migration**]. Recommendation: dbt, to match the EMET pattern and teach the standard tool.

### Key Entities

- **dim_country**: `country_key (PK), country_code (UNIQUE), country_name, region`.
- **dim_indicator**: `indicator_key (PK), indicator_code (UNIQUE), indicator_name, description`.
- **dim_year**: `year_key (PK), year (UNIQUE)`.
- **fact_indicator**: `country_key (FK), indicator_key (FK), year_key (FK), value` — UNIQUE
  `(country_key, indicator_key, year_key)`.
- **published.country_year_indicators**: `country_code, country_name, year, <indicator columns…>`.

## Success Criteria *(mandatory)*

- **SC-001**: One command builds the full warehouse from `staging`.
- **SC-002**: The three dimensions have zero duplicate natural keys.
- **SC-003**: `fact_indicator` has zero grain violations (the 3-key tuple is unique).
- **SC-004**: Every fact row joins to valid dimensions (no orphans).
- **SC-005**: `published.country_year_indicators` returns the expected country-year rows and is the
  shape spec 002 reads.
- **SC-006**: Re-running the build changes nothing (idempotent) and its tests pass in CI.

## Out of Scope

- Slowly-changing-dimension history (SCD2) — dimensions are current-state for now.
- The ML model (spec 002) and dashboard (spec 005) — they *consume* `published`, defined here.
- Additional indicators beyond those already ingested (extend `001`/`pull_wdi.py` if needed).

## Notes for the plan phase

- If dbt is chosen (FR-009): add `dbt-postgres`, a `profiles.yml` templated to the `db` service, and
  `models/{staging,warehouse,published}/`. If Alembic-only: one migration for the DDL + a seed/build
  script. Either way, keep `staging → warehouse → published` zone discipline (Principle III).
- `dim_year` is the simplest date dimension; promote to a full `dim_date` only if later specs need
  month/quarter grain.
