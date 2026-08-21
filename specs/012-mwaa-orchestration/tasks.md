# Tasks: Managed Airflow on MWAA (spec 012, alt track)

- [x] **T001** `infra/mwaa/dags/wb_pipeline.py` — the DAG (ingest→flag→dbt_build→train, deps + retries). (FR-001)
- [x] **T002** `infra/mwaa/main.tf` — S3 DAG bucket + object, execution role + policies, SG, MWAA
      environment (mw1.small) in 007's private subnets (vars). (FR-002/FR-003)
- [x] **T003** `infra/mwaa/README.md` — map, EventBridge-vs-MWAA decision, apply, idle cost, teardown. (FR-005/FR-006)
- [x] **T004** `terraform validate` clean on `infra/mwaa/`. (SC-002)
