# Implementation Plan: Warehouse — Conformed Star Schema (spec 003)

**Status**: Built · **Spec**: `spec.md` (Accepted) · **Author**: maintainer
*(Authored retroactively to document the as-built design.)*

## Summary

Conform `staging.wdi_observation` into a Kimball star (`warehouse` schema) and a wide `published` mart,
built and tested by **dbt** (`make dbt-build`). The `published` mart is the single read surface for the
model (spec 002) and dashboard (spec 005).

## Technical context

- **Tool**: dbt (`dbt-postgres`), run on the host, connecting to the Postgres container.
- **Project**: `backend/dbt/` — `dbt_project.yml`, `profiles.yml`, `models/{staging,warehouse,published}/`,
  a `generate_schema_name` macro (so zones land in clean `warehouse` / `published` schemas), and tests.

## Constitution check (gate)

- **IV Conformed dimensional model** ✅ shared dims + a fact at a declared grain. **III Zone discipline**
  ✅ `staging → warehouse → published`. **II Test-backed** ✅ dbt tests. **VI Reproducible** ✅ idempotent.

## Design decisions (as built)

1. **Dimensions** — `dim_country`, `dim_indicator`, `dim_year`; surrogate keys via `dense_rank()`
   (stable and idempotent over this fixed dataset), natural keys UNIQUE.
2. **Fact** — `fact_indicator` at grain **country × indicator × year**, FK-joined to the three dims;
   the 3-key tuple is UNIQUE (grain guard).
3. **Published mart** — `country_year_indicators`, a dbt **view** pivoting the star to one row per
   country-year with the indicators as columns.
4. **Schema naming** — a `generate_schema_name` macro so `+schema: warehouse|published` land literally
   (not `<target>_warehouse`).

## Files

- `backend/dbt/models/warehouse/{dim_country,dim_indicator,dim_year,fact_indicator}.sql` + `schema.yml`
- `backend/dbt/models/published/country_year_indicators.sql`
- `backend/dbt/models/staging/sources.yml`, `macros/generate_schema_name.sql`, `tests/assert_fact_grain_unique.sql`
- `Makefile` target `dbt-build`

## Testing

- dbt tests: dim uniqueness + not-null, fact referential integrity, singular grain-uniqueness test.
  Delivered run: **24 tests PASS**.
