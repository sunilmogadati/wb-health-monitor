# ADR-0002: Orchestration — EventBridge + scheduled Fargate task

- **Status:** Accepted
- **Date:** 2026-08-20

## Context
The DE pipeline (`ingest → dbt-build → train`) is run manually today via `make`. To run unattended it
needs scheduling and a compute home. The pipeline is **linear, few-step, batch** — no branching, no
backfills, one source.

## Decision
Automate with an **EventBridge schedule** that triggers a **Fargate task** running the same pipeline
steps (spec 007). This is orchestration-*lite*: schedule + run, no standing orchestrator to operate.

## Alternatives considered
- **Apache Airflow (self-hosted):** the right tool once there are many DAGs / branching / backfills, but
  a full scheduler + web UI + metadata DB is overkill for one linear job today. *(Adopt when the
  pipeline branches — see below.)*
- **Dagster / Prefect:** modern, asset-oriented, great DX; the preferred upgrade over Airflow when we
  outgrow cron — but still more than a single linear batch needs now.
- **Managed Airflow (MWAA) / Cloud Composer:** hundreds of dollars/month even idle; not justified.
- **AWS Lambda:** 15-minute cap and size limits; the ingest+dbt+train run can exceed both.

## Consequences
- Minimal infra, minimal cost; the batch runs on a cron with no server to manage.
- Compute and orchestration compose: this task can later become a worker under Dagster/Airflow without
  rewriting the steps.
- **Trigger to revisit:** when the pipeline gains branches, multiple sources, backfills, or needs
  lineage/retries/observability → adopt **Dagster** (dbt-native, asset lineage) or self-hosted Airflow.
