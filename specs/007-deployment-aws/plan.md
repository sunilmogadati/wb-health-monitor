# Implementation Plan: Deployment — AWS (IaC + CI/CD) (spec 007)

**Status**: Draft · **Spec**: `spec.md` · **Owner**: maintainer / advanced

## Summary

Deploy the platform to AWS as Terraform + GitHub Actions CI/CD: API + dashboard as ECS Fargate services
behind one ALB, RDS Postgres, S3 for the `raw` zone and the model artifact, the batch pipeline as a
scheduled Fargate task, secrets in Secrets Manager. Reproduces the local compose stack over HTTPS.

## Target architecture

```
                    Internet
                       │  HTTPS
                 ┌─────▼─────┐
                 │    ALB    │  /api/* → api   ·   /* → web
                 └──┬─────┬──┘
        ┌───────────▼─┐ ┌─▼───────────┐
        │ api (Fargate)│ │ web (Fargate)│   Next.js SSR
        └──┬────────┬─┘ └─────────────┘
   boto3/│        │ psycopg
    IAM  ▼        ▼
   ┌─────────┐ ┌──────────┐        ┌─────────────────────────┐
   │   S3    │ │   RDS    │◀───────│ pipeline (scheduled      │
   │ raw +   │ │ Postgres │  writes│ Fargate task: ingest →   │
   │ model   │ │ wh/mart  │        │ dbt-build → train)       │
   └─────────┘ └──────────┘        └───────────▲─────────────┘
        ▲                          EventBridge Scheduler (cron)
        │ Secrets Manager: ANTHROPIC_API_KEY, RDS creds
```

## Constitution check (gate)

- **I Public data / no secrets** ✅ Secrets Manager; secret-scan in CI; `.env` local-only.
- **III Governed zones** ✅ `raw`→S3, `staging/warehouse/published`→RDS; API still reads only `published`.
- **II Test-backed** ✅ CI runs the suite as a gate; a post-deploy smoke test proves the live stack.

## Design decisions

1. **One image family, three roles** — the existing backend image runs as the `api` service and, with a
   different command, as the `pipeline` scheduled task (`make ingest && make dbt-build && make train`).
   The frontend is its own image (`web`). Fewer artifacts, identical code in batch + serving.
2. **Fargate + one ALB, path routing** — `/api/*`→api, `/*`→web. Keeps a single public hostname and one
   TLS termination. *(App Runner is the lighter alt if the team prefers less networking IaC — resolve in
   clarify.)*
3. **S3 for state that two containers share** — the `raw` zone **and** the trained model artifact. The
   model path becomes env-driven (`MODEL_URI`: local file locally, `s3://…` in prod), so the batch task
   writes it and the API loads it. This is the one code change (FR-006).
4. **RDS via env, migrations as a deploy step** — Alembic runs from a CI/CD job (or a one-off task)
   against RDS before the new API serves.
5. **Scheduled batch, not a service** — EventBridge Scheduler triggers a Fargate `RunTask` on cron; it
   exits when done. First run is also triggerable manually from CI/CD.
6. **Secrets Manager + OIDC** — runtime secrets injected into task defs; GitHub → AWS via OIDC role (no
   long-lived keys). Terraform state in an S3 backend with a DynamoDB lock.
7. **Cost discipline** — smallest RDS/Fargate sizes, single-AZ for the demo, documented `terraform
   destroy`.

## Files

- `infra/` — Terraform root + modules: `network`, `ecr`, `rds`, `s3`, `ecs` (cluster/services/task-defs),
  `alb`, `scheduler`, `secrets`, `iam`; remote-state backend config.
- `.github/workflows/deploy.yml` — build/push images → test gate → `terraform plan` (destroy-guard) →
  `apply` on `main` → migrate → smoke test; OIDC auth.
- code change: env-driven model artifact path (`MODEL_URI`) in `ml/train.py` + `app/main.py` (FR-006).
- `docs/DEPLOY.md` — prerequisites, first-run order, teardown.

## Testing

- **CI gate**: existing `make test` must pass before any infra apply.
- **plan guard**: fail the workflow if `terraform plan` shows unexpected destroys/replacements of RDS/S3.
- **post-deploy smoke**: curl the live `/api/v1/health` + one read endpoint; fail the deploy if red.
- **first-run**: verify the API's graceful states hold before the first pipeline run (no 500s).
- **secret scan**: CI fails on any committed secret.

## Rollout order (first environment)

1. `terraform apply` (network, ECR, RDS, S3, secrets, ECS, ALB, schedule).
2. Push images to ECR (CI/CD).
3. Run Alembic migrations against RDS.
4. Trigger the first pipeline run (manual `RunTask`) → mart + residuals + model in RDS/S3.
5. Smoke test the live API + dashboard.
