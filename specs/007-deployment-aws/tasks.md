# Tasks: Deployment — AWS (IaC + CI/CD) (spec 007)

**Status**: In progress — IaC + CI/CD authored offline (reference, not yet `terraform validate`d/applied); apply-and-verify (T017) + secret-scan (T016) are credentialed-session items · **Plan**: `plan.md` · **Owner**: maintainer / advanced · Work in order; each maps to a spec FR / SC.

> Run `/speckit.clarify` first to settle the open choice (ECS Fargate+ALB vs App Runner for the two web
> services) before building the compute module.

## Phase 0 — Prep the app for the cloud (code, not infra)
- [x] **T001** Make the model artifact path env-driven (`MODEL_ARTIFACT_DIR`): `ml/artifacts.py`
  storage shim (local path default, `s3://…` in prod); `ml/train.py` writes + `app/main.py` loads via
  it. Local branch unit-tested; `make train` + `/predict` verified. (FR-006)
- [x] **T002** `load_wdi.s3_client_kwargs()` — env-driven: unset `S3_ENDPOINT_URL`/keys ⇒ AWS default
  endpoint + IAM role (prod); `.env` sets MinIO (local). Unit-tested. *(Live-against-real-S3 confirm is
  a cloud-session check.)* (FR-004)
- [x] **T003** Prod config knobs documented in `.env.example` (no values): DB/S3/LLM/CORS +
  `NEXT_PUBLIC_API_BASE=/api/v1` (same-origin static export). (FR-008)

## Phase 1 — Terraform foundation
- [x] **T004** Remote state: S3 backend + DynamoDB lock; `infra/` root + provider/versions. (FR-009)
- [x] **T005** `network` module: VPC, public/private subnets, security groups, ALB. (FR-002/FR-009)
- [x] **T006** `ecr` module: repositories for the `api`/`pipeline` image and the `web` image. (FR-001)
- [x] **T007** `secrets` module: Secrets Manager entries for `ANTHROPIC_API_KEY` + RDS creds; IAM to read them. (FR-007)

## Phase 2 — Stateful stores
- [x] **T008** `rds` module: managed Postgres (smallest workable size, single-AZ ok for demo). (FR-003/FR-012)
- [x] **T009** `s3` module: buckets for the `raw` zone and model artifacts; least-privilege bucket policies. (FR-004/FR-006)

## Phase 3 — Compute + schedule
- [x] **T010** `ecs` module: cluster; `api` + `web` Fargate services behind the ALB (path routing
  `/api/*`, `/*`); task roles; secrets + env wired in. (FR-002)
- [x] **T011** `scheduler` module: the `pipeline` Fargate task def (runs `ingest → dbt-build → train`) +
  EventBridge Scheduler cron + a manual `RunTask` path. (FR-005)
- [x] **T012** Migrations step: run Alembic against RDS as a deploy job (CI/CD or one-off task). (FR-003)

## Phase 4 — CI/CD
- [x] **T013** GitHub → AWS via **OIDC** (no long-lived keys); the deploy IAM role. (FR-010)
- [x] **T014** `.github/workflows/deploy.yml`: build/push images → **test gate** → `terraform plan`
  (**destroy-guard**) → `apply` on `main` → migrate → trigger first pipeline run. (FR-010)
- [x] **T015** Post-deploy **smoke test** job: curl live `/api/v1/health` + one read endpoint; fail the
  deploy if red. (FR-011)
- [ ] **T016** Secret-scan job (e.g. `git secrets` / gitleaks) fails CI on any committed secret. (FR-007/SC-004)

## Phase 5 — Prove it + document
- [ ] **T017** Stand up the first environment in rollout order (apply → images → migrate → first
  pipeline run → smoke). Verify SC-001..SC-005. (SC-001/002/003/005)
- [x] **T018** `docs/DEPLOY.md`: prerequisites, first-run order, config, and **teardown**; verify
  `terraform destroy` leaves no billable resources. (FR-012/SC-006)

## Phase 6 — Ship
- [ ] **T019** PR into `develop`; maintainer reviews against Success Criteria; then a controlled first
  deploy from `main`.

## v1.2.0 — production hardening (FR-013..016)
- [x] **T020** WAFv2 web ACL on CloudFront (managed rules + rate limit), us-east-1 provider. (FR-013)
- [x] **T021** VPC endpoints: S3 gateway + ECR/Secrets/Logs interface (skip NAT for AWS svcs). (FR-014)
- [x] **T022** Route53 + ACM for the app domain (CloudFront, us-east-1) + optional API subdomain (ALB
      HTTPS, regional); all gated on optional vars. (FR-015)
- [x] **T023** `docs/DEPLOYMENT.md` — manual AWS steps vs Terraform automation + teardown + cost. (FR-016)
- [x] **T024** `terraform fmt` + `validate` clean on both roots (validated, not applied).
