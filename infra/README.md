# infra/ — AWS deployment (spec 007)

Terraform for the whole platform on AWS: **ECS Fargate** (API + dashboard behind one **ALB**),
**RDS Postgres**, **S3** (raw zone + model artifacts), a **scheduled Fargate task** for the batch
pipeline, **Secrets Manager**, and a **GitHub OIDC** deploy role. CI/CD is `.github/workflows/deploy.yml`.

> **Status: validated, not applied.** `terraform fmt` + `terraform validate` **pass** on both roots
> (`infra/` and `infra/sagemaker/`, AWS provider ~5.40) — the config is well-formed and
> provider-schema-correct. It has **not** been `plan`/`apply`'d against an AWS account (no credentials,
> and `apply` is billable), so account-specific issues (IAM policy evaluation, name collisions, real
> API behavior) are still surfaced by the first `terraform plan`. The credentialed session:
> uncomment the S3 backend → `init` → `plan` (reconcile anything it flags) → `apply`. Sizes default to
> the smallest workable (single-AZ) for a demo.

## What maps where

| Local (`docker compose`) | AWS |
|---|---|
| `api` container | ECS Fargate service `api` (ALB) |
| `web` (Next.js dev) | **static export → S3 + CloudFront** (CloudFront `/api/*` → ALB, same-origin) |
| Postgres | RDS Postgres |
| MinIO `raw` zone | S3 raw bucket (`S3_BUCKET_RAW`; `S3_ENDPOINT_URL` unset in prod → AWS default) |
| local `models/` | S3 artifacts bucket (`MODEL_ARTIFACT_DIR=s3://…/models`, FR-006) |
| `make ingest dbt-build train` | scheduled Fargate task → `python -m scripts.run_pipeline` |
| `.env` secrets | Secrets Manager (DB creds + `ANTHROPIC_API_KEY`) |

The dashboard is a **client-side SPA** (`next build` with `output: 'export'` → `frontend/out/`), so it
needs no container: CI `aws s3 sync`s it to the web bucket and CloudFront serves it, forwarding
`/api/*` to the ALB so the browser calls the API **same-origin** (`/api/v1`) — no CORS, no baked URL.

## First-time deploy

1. **Bootstrap remote state** (once): create the state bucket + lock table, then uncomment the
   `backend "s3"` block in `versions.tf`:
   ```sh
   aws s3 mb s3://wb-health-monitor-tfstate
   aws dynamodb create-table --table-name wb-health-monitor-tflock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST
   ```
2. `terraform init && terraform validate && terraform plan` — review, especially any destroys.
3. `terraform apply` — stands up infra; services sit unhealthy until images exist (expected).
4. Put the Anthropic key into its secret (never in state):
   ```sh
   aws secretsmanager put-secret-value --secret-id <anthropic-secret-name> --secret-string sk-ant-...
   ```
5. Wire GitHub: set repo **variables** `DEPLOY_ENABLED=true`, `AWS_REGION`, `PROJECT=wb-health-monitor`,
   and **secret** `AWS_DEPLOY_ROLE_ARN` = the `github_deploy_role_arn` output. Push to `main` → CI/CD
   builds/pushes images, `terraform apply`s, runs `alembic upgrade head`, and smoke-tests `/health`.
6. **Seed data** (first run): trigger the pipeline once —
   `aws ecs run-task --cluster <ecs_cluster> --task-definition <pipeline_task_definition> \
    --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[...],securityGroups=[...]}"` —
   or `workflow_dispatch` the deploy with `run_pipeline=true`. Until then the API reports "model not
   ready" and degrades gracefully (spec 002/005), it does not 500.

## HTTPS

Default is HTTP on the ALB's AWS hostname (deployable with no domain). Set `acm_certificate_arn` (and
point a DNS record at the ALB) to serve HTTPS:443 with an 80→443 redirect — the documented stretch.

## Teardown (FR-012)

```sh
terraform destroy
```
`force_delete`/`force_destroy`/`skip_final_snapshot` are set on the demo resources so this leaves no
orphaned billable resources. For real data, remove those and take a final RDS snapshot first.
