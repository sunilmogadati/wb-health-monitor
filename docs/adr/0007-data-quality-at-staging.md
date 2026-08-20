# ADR-0007: Data-quality detection at the staging boundary (shift-left)

- **Status:** Accepted
- **Date:** 2026-08-20
- **Supersedes the placement in** ADR-0004 (the *what* — filter + tripwire — is unchanged; only *where* it runs moves).

## Context
Anomaly detection was retrofitted into two late consumers: `ml/train.py` filtered the model's rows,
and the read API gapped flagged values at request time. That's the band-aid-at-every-consumer
pattern — the same detection ran in two places, and a consumer that forgot to re-filter (or a new one)
would serve bad data. The World Bank error (`life_expectancy = 18.8`) reached the dashboard for exactly
this reason: the mart the UI reads was never cleansed.

## Decision
Run the detection **once, early** — at the **`raw → staging → mart` boundary**, before anything
consumes the data:

1. A pipeline step (`make flag`, `scripts/flag_quality.py`) runs **after staging is loaded, before dbt
   builds the mart**. It reshapes the long staging rows to wide, applies the same detectors (static
   ranges + robust-z + year-over-year), and writes the flagged country-year-indicators to
   **`ingestion.data_quality_flag`**. A large flagged fraction **halts** (the tripwire).
2. The **dbt `published` model nulls** any flagged cell, so the **mart is clean at the source**.
3. Downstream consumers — the **model** (`train.py`) and the **read API** — **stop re-filtering**; they
   trust the mart. One detection, inherited everywhere.

`raw` stays **immutable** (audit/replay); cleansing happens at the first *transform*, never by deleting
source data.

## Alternatives considered
- **Keep filtering in train + gapping in the API** (the retrofit): duplicated logic, easy to drift — the
  problem this ADR fixes.
- **Delete bad rows from `raw`/`staging`:** violates raw immutability; loses the audit trail. Flag-and-null
  preserves provenance.
- **Robust-z inside dbt SQL:** the statistical detectors are far cleaner in Python; a Python flag step
  that dbt reads keeps detection flexible and the mart declarative.

## Consequences
- Every zone (warehouse, mart, model, API, dashboard) inherits clean data from one place.
- Pipeline order matters: `ingest → flag → dbt-build → train`. `make flag` always creates the flag table
  (empty if nothing is flagged), so dbt never fails on a missing table.
- The retrofit is removed: `train.py` no longer flags/persists, and the read API no longer gaps — the
  mart is already clean. Detection lives in `scripts/flag_quality.py` + `ingestion.data_quality_flag`.
- The static value-ranges (and robust-z on `life_expectancy` only) carry over unchanged — including the
  false-positive lesson (skewed columns like GDP/fertility are range-checked, not robust-z'd).
