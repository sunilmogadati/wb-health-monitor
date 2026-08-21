# Feature Specification: Managed Airflow on MWAA (alternative track)

**Feature Branch**: `012-mwaa-orchestration`

**Created**: 2026-08-21

**Status**: Accepted (2026-08-21) — as a **documented alternative track**; reference IaC + DAG,
`terraform validate`-clean, **not applied** (MWAA carries a real always-on cost).

**Depends on**: spec 007 (the app infra — VPC/subnets/RDS/S3 it reuses; the `run_pipeline.py` steps).
**Alternative to** the orchestration slice of 007 (ADR-0002): it replaces **EventBridge Scheduler →
scheduled Fargate task** with **Amazon MWAA (managed Apache Airflow)** running the same
`ingest → dbt build → train` pipeline as an Airflow **DAG**.

**Input**: Show the managed-Airflow way to orchestrate the batch pipeline — a DAG with explicit task
dependencies, retries, backfill, and the Airflow UI — as a **deliberate alternative** to the
right-sized EventBridge approach, for teaching/portfolio and for headroom when the pipeline grows
beyond one linear daily job.

> **Constitution alignment:** Principle I (public data; secrets via Secrets Manager/IAM), Principle VI
> (the DAG runs the same deterministic, containerized steps), **Change Traceability** (a genuinely
> different orchestrator → its own spec, an alternative like SageMaker/009).

## Right-sizing — read first

For **one linear daily batch** (`ingest → dbt → train`), MWAA is **more orchestrator than the job
needs**, and it bills **~$0.49/hr (~$350+/mo) even idle** (a managed Airflow environment is always on).
ADR-0002's EventBridge→Fargate is the correctly-sized default. MWAA earns its keep when the pipeline
becomes a real **DAG** — many tasks, fan-out/fan-in, backfills, cross-dataset dependencies, SLAs, a UI
for operators. Adopt it for that, or for the teaching/portfolio story — **not** because today's pipeline
demands it. This is the same "managed alternative for headroom" framing as spec 009 (SageMaker).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The pipeline runs as a DAG (Priority: P1)

**Acceptance**:
1. **Given** the MWAA environment, **When** the DAG runs (schedule or manual), **Then** it executes
   `ingest → flag → dbt build → train` as ordered Airflow tasks against RDS + S3, and a failed task
   **stops** its downstream (no bad data promoted).
2. **Given** a failed run, **When** an operator opens the Airflow UI, **Then** they see the task graph,
   logs, and can **retry/backfill** — the managed-orchestrator value over a bare scheduled task.

### User Story 2 — Same governance, different orchestrator (Priority: P2)

**Acceptance**: the DAG runs the **same steps** as `run_pipeline.py` (Principle VI); secrets come from
Secrets Manager; 008's data-quality + eval gates still apply. Only the *orchestration* changes.

## Requirements *(mandatory)*

- **FR-001** — **DAG**: an Airflow DAG (`infra/mwaa/dags/wb_pipeline.py`) with ordered tasks
  `ingest → flag → dbt_build → train` and explicit dependencies; retries + a schedule; a failed task
  halts downstream.
- **FR-002** — **MWAA environment** (IaC): an `aws_mwaa_environment` on a versioned **S3 DAG bucket**,
  in **private subnets** (reusing 007's VPC), with an **execution role** (S3/logs/Secrets/ECS as
  needed) and a security group. Smallest class (`mw1.small`).
- **FR-003** — **Same steps, same governance**: tasks run the `run_pipeline.py` stages (or trigger the
  Fargate task per step); secrets via Secrets Manager; no new data path (Principle I/VI).
- **FR-004** — **One orchestrator, not two**: MWAA **replaces** the EventBridge→Fargate schedule on
  this track; don't run both (like 009's "one gate, not both").
- **FR-005** — **Right-sizing documented**: the doc states when MWAA is worth it vs. EventBridge (this
  spec's "Right-sizing" section), so the choice is explicit, not cargo-culted.
- **FR-006** — **Cost + teardown**: MWAA is always-on; `terraform destroy` removes the environment +
  bucket; the doc flags the idle cost (FR-006).

### Key Entities

- **MWAA environment**, **DAG S3 bucket**, **execution role + SG**, **the DAG** (tasks + dependencies).

## Success Criteria *(mandatory)*

- **SC-001**: The DAG defines `ingest → flag → dbt_build → train` with dependencies; a failed upstream
  task blocks downstream.
- **SC-002**: `terraform validate` passes on `infra/mwaa/`; the environment reuses 007's VPC/subnets.
- **SC-003**: The doc states the EventBridge-vs-MWAA decision + the idle cost, and teardown is documented.

## Out of Scope

- Replacing 007's app hosting or 009's model track; MWAA orchestrates the **batch pipeline** only.
- A real applied MWAA environment (cost) — this is reference IaC + a DAG, validated not applied.
