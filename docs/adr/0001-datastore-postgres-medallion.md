# ADR-0001: PostgreSQL with medallion zones

- **Status:** Accepted
- **Date:** 2026-08-20

## Context
The platform ingests public health/economic indicators, curates them, trains a model, and serves an
API + dashboard. We need a store that supports governed transformation (raw → clean → conformed →
published), SQL analytics, and easy local + cloud operation. Data volume is small (thousands of rows).

## Decision
Use **PostgreSQL** as the relational store, organised as **medallion zones** — `staging` →
`warehouse` (dbt star schema) → `published` (read mart) — with the object store holding the immutable
`raw` zone. Everything user-facing reads only `published`.

## Alternatives considered
- **A document store (MongoDB):** poor fit for the tabular, join-heavy star schema and SQL analytics.
- **A cloud warehouse (Snowflake/BigQuery) from day one:** over-scaled and cost-heavy for KB-scale data; adds a vendor before there's a need.
- **SQLite:** fine locally, but no real concurrency/roles and a weaker path to production.

## Consequences
- One familiar engine runs locally (Docker) and in the cloud (RDS) with the same SQL.
- dbt models the warehouse + mart; tests enforce grain and integrity.
- **OLTP vs OLAP:** this is an analytics workload, so Postgres-as-warehouse is fine. A high-write
  transactional *product* would keep Postgres for OLTP and add a separate analytical store rather than
  run heavy analytics on the live DB (see ADR-0003 for the engine scaling path).
