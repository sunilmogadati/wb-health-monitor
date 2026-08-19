# Implementation Plan: WDI Ingestion (spec 001)

**Status**: Built · **Spec**: `spec.md` (Accepted) · **Author**: maintainer
*(Authored retroactively to document the as-built design.)*

## Summary

Pull World Bank WDI indicators via `wbgapi`, land the exact pull immutably in the MinIO `raw` zone,
load the tidy long rows into `staging.wdi_observation`, and record every run in `ingestion.pull_log`
(referencing a registered source in `ingestion.data_sources`). Public data only, no credentials.

## Technical context

- **Deps**: `wbgapi`, `pandas` (host pull); `psycopg`, `boto3` (container load).
- **Split**: `pull_wdi.py` runs on the host (has `wbgapi`); `load_wdi.py` runs in the api container
  (has DB + MinIO access). The CSV under `backend/data/` is the handoff (bind-mounted).
- **Object store**: MinIO (`raw` bucket), S3-compatible via `boto3`.

## Constitution check (gate)

- **I Public data only** ✅ WB public API, no keys. **III Zone discipline** ✅ raw is immutable, only
  staging is loaded from it. **II Test-backed** ✅ migration round-trip + pull verification.
  **VI Reproducible** ✅ `make ingest`, containerized.

## Design decisions (as built)

1. **Source registry first** — `ingestion.data_sources` (migration `0002`) holds `world_bank_wdi`;
   `load_wdi.py` resolves the active source and fails if it isn't registered.
2. **Raw landing** — `load_wdi.py` uploads the pull to `s3://raw/world_bank_wdi/pull_<id>/…` and
   records the object key in `pull_log.object_keys`.
3. **Staging** — long shape `(country_code, country_name, year, indicator, value)`, PK
   `(country_code, year, indicator)`; `uhc_index` dropped (too sparse).
4. **Lineage** — `ingestion.pull_log` (migration `0001`), one row per run, FK to the source.

## Files

- `backend/scripts/pull_wdi.py` (host pull → CSV), `backend/scripts/load_wdi.py` (raw + staging + log)
- `backend/alembic/versions/0001_ingestion_pull_log.py`, `0002_data_sources_registry.py`
- `Makefile` target `ingest`

## Testing

- Migration round-trip (up/down) asserted; a pull writes a `raw` object + a `succeeded` `pull_log` row.
