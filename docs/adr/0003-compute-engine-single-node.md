# ADR-0003: Compute engine — single-node (Postgres/dbt/pandas)

- **Status:** Accepted
- **Date:** 2026-08-20

## Context
The transform + modelling need a compute engine. The data is **kilobyte-scale** (thousands of rows).
"Big data" tooling is a common reflex that adds large operational cost for no benefit at this size.

## Decision
Process on a **single node**: **dbt-postgres** for the SQL transforms and **pandas + scikit-learn** for
the model. No distributed engine.

## Alternatives considered
- **Spark / PySpark:** built for distributed, out-of-core, TB-scale data. At KB–GB it is a freight
  train for a letter — JVM + cluster overhead for nothing. Not old, just the wrong scale here.
- **DuckDB / Polars:** modern **vectorized single-node** engines (columnar; Arrow underneath). Excellent
  for millions–tens-of-millions of rows on one machine. Not needed yet, but the *first* upgrade.

## Consequences
- Simple, fast, cheap; runs identically on a laptop and a small container.
- **Upgrade path (in order), if data grows:** `dbt-postgres` → **`dbt-duckdb` / Polars** (single-node,
  vectorized) → **Spark or a cloud warehouse** only at true distributed scale. We do *not* jump to Spark.
