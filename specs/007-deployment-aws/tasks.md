# Tasks: Deployment — AWS (IaC + CI/CD) (spec 007)

**Status**: Draft · **Plan**: `plan.md` · **Owner**: maintainer / advanced · Work in order; each maps to a spec FR / SC.

> Run `/speckit.clarify` first to settle the open choice (ECS Fargate+ALB vs App Runner for the two web
> services) before building the compute module.

## Phase 0 — Prep the app for the cloud (code, not infra)
- [ ] **T001** Make the model artifact path env-driven (`MODEL_URI`): `ml/train.py` writes and
  `app/main.py` loads via a small storage shim — local file locally, `s3://…` in prod. Test both. (FR-006)
- [ ] **T002** Confirm the `boto3` object-store client works against real S3 (no custom endpoint + IAM
  creds) as well as MinIO locally, driven by env. (FR-004)
- [ ] **T003** Prod config knobs: `CORS_ALLOWED_ORIGINS`, `NEXT_PUBLIC_API_BASE`, DB + S3 from env;
  document them in `.env.example` (no values). (FR-008)

## Phase 1 — Terraform foundation
- [ ] **T004** Remote state: S3 backend + DynamoDB lock; `infra/` root + provider/versions. (FR-009)
- [ ] **T005** `network` module: VPC, public/private subnets, security groups, ALB. (FR-002/FR-009)
- [ ] **T006** `ecr` module: repositories for the `api`/`pipeline` image and the `web` image. (FR-001)
- [ ] **T007** `secrets` module: Secrets Manager entries for `ANTHROPIC_API_KEY` + RDS creds; IAM to read them. (FR-007)

## Phase 2 — Stateful stores
- [ ] **T008** `rds` module: managed Postgres (smallest workable size, single-AZ ok for demo). (FR-003/FR-012)
- [ ] **T009** `s3` module: buckets for the `raw` zone and model artifacts; least-privilege bucket policies. (FR-004/FR-006)

## Phase 3 — Compute + schedule
- [ ] **T010** `ecs` module: cluster; `api` + `web` Fargate services behind the ALB (path routing
  `/api/*`, `/*`); task roles; secrets + env wired in. (FR-002)
- [ ] **T011** `scheduler` module: the `pipeline` Fargate task def (runs `ingest → dbt-build → train`) +
  EventBridge Scheduler cron + a manual `RunTask` path. (FR-005)
- [ ] **T012** Migrations step: run Alembic against RDS as a deploy job (CI/CD or one-off task). (FR-003)

## Phase 4 — CI/CD
- [ ] **T013** GitHub → AWS via **OIDC** (no long-lived keys); the deploy IAM role. (FR-010)
- [ ] **T014** `.github/workflows/deploy.yml`: build/push images → **test gate** → `terraform plan`
  (**destroy-guard**) → `apply` on `main` → migrate → trigger first pipeline run. (FR-010)
- [ ] **T015** Post-deploy **smoke test** job: curl live `/api/v1/health` + one read endpoint; fail the
  deploy if red. (FR-011)
- [ ] **T016** Secret-scan job (e.g. `git secrets` / gitleaks) fails CI on any committed secret. (FR-007/SC-004)

## Phase 5 — Prove it + document
- [ ] **T017** Stand up the first environment in rollout order (apply → images → migrate → first
  pipeline run → smoke). Verify SC-001..SC-005. (SC-001/002/003/005)
- [ ] **T018** `docs/DEPLOY.md`: prerequisites, first-run order, config, and **teardown**; verify
  `terraform destroy` leaves no billable resources. (FR-012/SC-006)

## Phase 6 — Ship
- [ ] **T019** PR into `develop`; maintainer reviews against Success Criteria; then a controlled first
  deploy from `main`.
