# infra/mwaa/ — Managed Airflow (MWAA) orchestration (spec 012, alternative track)

The **managed-Airflow** way to run the batch pipeline (`ingest → flag → dbt build → train`), as an
explicit alternative to the default **EventBridge Scheduler → Fargate task** (ADR-0002). **Reference
IaC + DAG, authored offline** (`terraform validate`-clean; not applied — MWAA bills even idle).

> **Right-sizing first:** for one linear daily batch this is **more orchestrator than the job needs**,
> and an MWAA environment costs **~$0.49/hr (~$350+/mo) always-on**. EventBridge→Fargate is the
> correctly-sized default. MWAA earns its keep when the pipeline becomes a real **DAG** (many tasks,
> fan-out/in, backfills, SLAs, an operator UI) — or for the teaching/portfolio story. Same framing as
> the SageMaker alternative (spec 009): adopt deliberately, not by default.

## What it does — and does NOT — replace

- **Replaces** only the *orchestration*: MWAA runs the DAG instead of the scheduled Fargate task. **Use
  one, not both** (FR-004).
- **Leaves in place:** the app + API + RDS + S3 (spec 007), the model (002/008/009), the LLM features.
  The DAG runs the **same governed steps** as `backend/scripts/run_pipeline.py` — only the trigger +
  task graph change (Principle VI).

## Files

| File | What |
|---|---|
| `dags/wb_pipeline.py` | The Airflow DAG: `ingest → flag → dbt_build → train`, explicit deps + retries. A failed task halts downstream. |
| `main.tf` | Own Terraform root: versioned DAG S3 bucket + object, MWAA execution role + SG, `aws_mwaa_environment` (`mw1.small`) in 007's private subnets (passed as vars). |

## Apply (credentialed session)

```sh
cd infra/mwaa
terraform init && terraform validate && terraform plan \
  -var="vpc_id=$(cd ../ && terraform output -raw ... )" \
  -var='private_subnet_ids=["subnet-aaa","subnet-bbb"]'
terraform apply
```
(Reuse spec 007's VPC + private subnets — add matching outputs there, or pass the IDs directly.)

## Teardown (FR-006)

`terraform destroy` — removes the environment + DAG bucket. **Do not leave it running**: MWAA bills
continuously regardless of DAG activity.
