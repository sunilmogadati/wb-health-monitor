# Implementation Plan: Managed Airflow on MWAA (alt track)

**Spec**: `specs/012-mwaa-orchestration/spec.md` · **Branch**: `mwaa-012`

## Constitution Check
- I — public data; secrets via Secrets Manager/IAM. ✅  VI — same deterministic steps as
  `run_pipeline.py`. ✅  Change Traceability — a different orchestrator → its own alt-track spec. ✅

## Approach (reference IaC + DAG, validated not applied)
1. **`infra/mwaa/dags/wb_pipeline.py`** — the Airflow DAG: `ingest → flag → dbt_build → train` as
   ordered tasks (BashOperator running the same commands `run_pipeline.py` sequences), retries + a
   schedule. Reference code (Airflow not installed here; lives under `infra/`, outside the backend
   package, so mypy/pytest don't touch it; ruff-clean).
2. **`infra/mwaa/main.tf`** — a separate Terraform root (like `infra/sagemaker/`): S3 DAG bucket
   (versioned) + `aws_s3_object` upload of the DAG, MWAA execution role + policies, a security group,
   and `aws_mwaa_environment` (`mw1.small`) in 007's private subnets (passed as vars). `terraform
   validate` clean.
3. **`infra/mwaa/README.md`** — the map, the EventBridge-vs-MWAA decision, apply, idle-cost, teardown.

## Notes
- Reuses 007's VPC/subnets via input vars (`vpc_id`, `private_subnet_ids`), mirroring how
  `infra/sagemaker/` takes `artifacts_bucket`. One orchestrator, not two (FR-004).
