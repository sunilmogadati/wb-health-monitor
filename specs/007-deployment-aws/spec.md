# Feature Specification: Deployment — AWS (IaC + CI/CD)

**Feature Branch**: `007-deployment-aws`

**Created**: 2026-08-19

**Status**: Draft — needs `/speckit.clarify` review before Accepted

**Depends on**: specs 001–006 (the full application: pipeline, warehouse, model, API, AI, dashboard).

**Input**: Deploy the whole platform to **AWS** as **infrastructure-as-code (Terraform)** with a
**CI/CD** pipeline (GitHub Actions). The running system must reproduce what `docker compose up` gives
locally — API + dashboard reachable over HTTPS, Postgres + object store persistent, the batch data
pipeline run on a schedule, and the Claude key held in a secrets manager — with **no secrets in the
repo** and a documented **teardown**.

> **Constitution alignment:** Principle I (public data; **no secrets committed** — all via Secrets
> Manager), Principle III (the governed zones move intact — object store → S3, warehouse/mart → RDS),
> Principle II (a smoke test proves the deployed stack answers before it's "done").

## Why this is its own spec

The app is **four deployable concerns**, and the complexity is in the stateful/batch parts:
API (stateless), dashboard (stateless), Postgres (stateful), object store (MinIO→S3), and the **batch
pipeline** (`ingest`/`dbt-build`/`train`) which is a **scheduled job, not a long-running service**.
Deployment decides how each maps to AWS, how the model artifact is shared between the batch job and the
API, and how CI/CD ships changes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A stakeholder opens the live dashboard (Priority: P1)

**Acceptance**:
1. **Given** the stack is deployed, **When** a user opens the dashboard's public HTTPS URL, **Then**
   the benchmark, trends, and comparison render from the live API (spec 006 over spec 005).
2. **Given** the API's public URL, **When** `GET /api/v1/health` is called, **Then** it returns healthy.

### User Story 2 — The pipeline refreshes data on a schedule (Priority: P1)

**Acceptance**:
1. **Given** the scheduled batch job, **When** it runs, **Then** it executes `ingest → dbt-build →
   train` against the cloud database + object store and updates the mart, residuals, and the model
   artifact — without a human on a laptop.
2. **Given** a fresh environment, **When** the pipeline has never run, **Then** the API reports a clear
   "data/model not ready" state rather than crashing (reuses the graceful states from 002/005).

### User Story 3 — A change ships through CI/CD (Priority: P1)

**Acceptance**:
1. **Given** a merge to `main`, **When** CI/CD runs, **Then** it builds + pushes the container images,
   applies the infrastructure, runs DB migrations, and the new version serves — no manual console
   clicking.
2. **Given** a failing test or `terraform plan` with unexpected destroys, **Then** the pipeline stops
   before touching prod.

### User Story 4 — No secrets in the repo; clean teardown (Priority: P2)

**Acceptance**: the Claude API key and DB credentials live only in **Secrets Manager**; a documented
`terraform destroy` removes all billable resources.

### Edge Cases

- Model artifact absent (pipeline hasn't run) → API serves health + read endpoints; `/predict`,
  `/brief`, `/benchmark` degrade gracefully.
- RDS/S3 unreachable → health/readiness reports the degraded dependency, not a 500 storm.
- CI/CD image build succeeds but migration fails → deploy halts; previous version stays up.

## Requirements *(mandatory)*

- **FR-001** — **Container registry**: both images (API, frontend) are built and pushed to **ECR**.
- **FR-002** — **Compute**: the **API** and **dashboard** run as **ECS Fargate services behind a single
  Application Load Balancer** (HTTPS; path routing `/api/*` → API, `/*` → dashboard). *(App Runner is an
  accepted lighter alternative for the two web services — decide in `/speckit.clarify`.)*
- **FR-003** — **Database**: Postgres runs on **RDS** (managed, persistent); the warehouse + mart +
  residuals live there. **Alembic migrations** run as a deploy step against RDS.
- **FR-004** — **Object store**: the `raw` zone moves from MinIO to **S3**. Because the code uses
  `boto3`, this is an **endpoint/credentials swap via env vars** — no rewrite. Confirm the client honors
  "no custom endpoint + IAM creds" in the AWS path.
- **FR-005** — **Batch pipeline**: `ingest → dbt-build → train` runs as a **scheduled Fargate task**
  (EventBridge Scheduler → `RunTask`), on the same image, reading/writing RDS + S3. Not a web service.
- **FR-006** — **Model artifact sharing**: the batch task writes the trained `life_expectancy.joblib`
  (and metadata) to **S3**; the **API loads it from S3** (not a baked-in local file), so the two
  independently-deployed containers share one model. *(Requires a small change to the model load/save
  path — see Dependencies.)*
- **FR-007** — **Secrets**: `ANTHROPIC_API_KEY` and DB credentials are stored in **AWS Secrets
  Manager** and injected into task definitions. **No secret is committed**; `.env` stays local-only.
- **FR-008** — **Config for prod**: `CORS_ALLOWED_ORIGINS` is set to the deployed dashboard origin;
  the dashboard's `NEXT_PUBLIC_API_BASE` points at the deployed API; DB/S3 come from env.
- **FR-009** — **Infrastructure as code**: all of the above is **Terraform** (VPC/subnets/security
  groups, ECR, RDS, S3, ECS cluster/services/task-defs, ALB, EventBridge schedule, Secrets Manager,
  IAM roles) under `infra/`. No click-ops; state stored remotely (S3 backend + DynamoDB lock).
- **FR-010** — **CI/CD**: a **GitHub Actions** workflow builds/pushes images, runs tests as a gate,
  `terraform plan` (guarding against unexpected destroys) then `apply` on `main`, runs migrations, and
  can trigger a one-off pipeline run. OIDC to AWS — **no long-lived AWS keys in GitHub**.
- **FR-011** — **Deploy smoke test**: an automated post-deploy check hits the live `/api/v1/health` and
  one read endpoint and fails the pipeline if they don't answer (Principle II at the deploy layer).
- **FR-012** — **Cost + teardown**: default to the smallest workable sizes (single-AZ acceptable for the
  demo); document `terraform destroy` and confirm it removes all billable resources.

### Key Entities *(infra, not data)*

- **Network**: VPC, public/private subnets, security groups, ALB.
- **Services**: `api` (Fargate), `web` (Fargate), `pipeline` (scheduled Fargate task) — one shared ECR image family.
- **Stores**: RDS Postgres instance, S3 buckets (`raw` zone + model artifacts), Terraform-state bucket.
- **Secrets**: `ANTHROPIC_API_KEY`, RDS credentials (Secrets Manager).

## Success Criteria *(mandatory)*

- **SC-001**: The dashboard and API are reachable over public HTTPS; the dashboard renders from the live API.
- **SC-002**: The scheduled pipeline runs unattended and refreshes mart + residuals + model in RDS/S3.
- **SC-003**: A merge to `main` ships end-to-end via CI/CD with no manual console steps; migrations run automatically.
- **SC-004**: `git secrets`/scan finds **no** committed secret; the Claude key resolves from Secrets Manager at runtime.
- **SC-005**: The post-deploy smoke test passes; a first-run (no data/model) environment degrades gracefully, not 500s.
- **SC-006**: `terraform destroy` tears the environment down with no orphaned billable resources.

## Out of Scope

- Multi-region / HA, autoscaling policies beyond defaults, blue-green/canary (single rolling deploy is enough).
- Custom domain + ACM cert is a **stretch** (the ALB/App Runner default hostname is acceptable for the demo).
- Auth/user accounts (unchanged from 005/006).
- Non-AWS targets (GCP/PaaS) — decided against for this spec (S3-compatibility makes AWS the least-change path).

## Dependencies & risks (for the plan phase)

- **Model artifact path (FR-006)** is the one real code change: today `train.py` writes `backend/models/
  life_expectancy.joblib` and `app.main` loads that local path. In the cloud the batch task and the API
  are separate → route both through **S3** (env-driven: local file locally, S3 in prod). Small, but it's
  a prerequisite for `/predict` + `/brief` to work in the deployed stack.
- **First-run ordering**: infra up → migrations → first pipeline run → model in S3 → API fully live. The
  API must tolerate the window before the first pipeline run (graceful states already specified).
- **Cost**: RDS + ALB + Fargate accrue hourly; keep sizes minimal and document teardown (FR-012).
