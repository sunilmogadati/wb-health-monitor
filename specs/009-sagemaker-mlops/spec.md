# Feature Specification: Managed MLOps on SageMaker (alternative track)

**Feature Branch**: `009-sagemaker-mlops`

**Created**: 2026-08-19

**Status**: Draft — needs `/speckit.clarify` review before Accepted

**Depends on**: spec 002 (the model + `train.py`), spec 007 (AWS infra — VPC/RDS/S3/roles it reuses).
**Alternative to** parts of 007 + 008: it replaces the **model** training/gating/serving slice with AWS
SageMaker managed primitives. It is **not** a replacement for the whole platform.

**Input**: Run the **trained model's lifecycle** — train → evaluate → register → promote → serve →
monitor — on **AWS SageMaker** (Training Jobs, Model Registry, SageMaker Pipelines, optional Serverless
Inference, Model Monitor) instead of the hand-rolled Fargate-batch + own-champion/challenger path. Same
outcomes, managed building blocks. Built so the project can **demonstrate both** the DIY and the managed
way.

> **Constitution alignment:** Principle II (evaluation gates promotion — here via a Registry approval
> step), Principle V (honest modeling — the residual is still a value-for-money signal, and the honest
> checks from 008 still run), Principle I (public data; secrets via Secrets Manager, roles via IAM).

## Scope boundary — what this does and does NOT cover

**Covers (the trained regression model only):** managed training, a versioned model registry, an
ML-native pipeline with a metric-based promotion gate, optional managed serving, and drift monitoring.

**Does NOT cover — stays as specified elsewhere:**
- The **API + dashboard + RDS + S3 + ALB + app CI/CD** stay on **spec 007** (SageMaker does not host
  your FastAPI/Next.js).
- The **LLM features** (`/ask`, `/brief`) stay on the **Anthropic API / Bedrock** — SageMaker is for
  *your* model, not the hosted LLM.
- **Spec 008's** LLM evals, data-quality gate, and honest-language checks **still apply** — SageMaker
  doesn't evaluate the Claude features or enforce Principle V wording.

> **Honest right-sizing (read this first):** for a ~357-row, 4-feature scikit-learn model, this managed
> stack is **more machinery than the model strictly needs** (the DIY path in 007/008 is correctly
> sized). Its value is (a) **teaching/portfolio** — showing the managed-ML pattern end to end, and
> (b) **headroom** — it's the path that keeps working when the model grows (more data, deep learning,
> GPU, governance requirements). Adopt it as a *deliberate alternative track*, not because the current
> model demands it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A managed retrain produces a versioned, evaluated model (Priority: P1)

**Acceptance**:
1. **Given** the SageMaker Pipeline, **When** it runs, **Then** it executes data-quality → **Training
   Job** → evaluate → and **registers** a new model version in the **Model Registry** with its metrics
   attached — no laptop involved.
2. **Given** the trained artifact, **Then** it lands in **S3** (the same artifact contract 007 uses).

### User Story 2 — Only an approved (non-regressed) model is promoted (Priority: P1)

**Acceptance**:
1. **Given** a new version whose CV/held-out metric is **not worse** than the current approved champion
   by more than the threshold, **When** the pipeline's condition step runs, **Then** the version is
   marked **Approved** (managed champion/challenger); otherwise it stays **Pending/Rejected** and the
   champion is untouched.
2. **Given** an Approved version, **Then** serving uses **that** version — never an unapproved one.

### User Story 3 — Serving without an always-on bill (Priority: P2)

**Acceptance**: the model is served either by the **API loading the latest Approved artifact from S3**
(default) **or** by a **SageMaker Serverless Inference** endpoint (scale-to-zero) — **not** an always-on
real-time endpoint. *(Which one → resolve in `/speckit.clarify`.)*

### User Story 4 — Drift is watched (Priority: P2)

**Acceptance**: input/output **drift** is monitored (Model Monitor on the endpoint, or a scheduled batch
drift check if serving from S3); a breach **alerts** — complementing 008's data-quality gate.

### Edge Cases

- No approved model yet (first run) → the first registered version becomes the champion (no gate to beat).
- Training Job fails → the pipeline stops; no new version is registered; the current champion still serves.
- Serverless endpoint cold start → acceptable for this low-traffic use; documented, not "fixed" with an always-on instance.

## Requirements *(mandatory)*

- **FR-001** — **Training Job**: `train.py` runs as a **SageMaker Training Job** (managed, ephemeral),
  reading features from RDS/S3 and writing the model artifact + metadata to **S3**.
- **FR-002** — **SageMaker Pipeline**: an ML DAG — **data-quality → train → evaluate → (condition)
  register** — with a metric-based **condition step** that only registers/approves a non-regressed model.
- **FR-003** — **Model Registry**: a model package **group**; each run registers a **versioned** package
  with its evaluation metrics attached, giving a lineage of models over time.
- **FR-004** — **Promotion gate = Registry approval**: promotion is the package's **Approved** status
  (auto on threshold, or manual approval). Serving consumes **only Approved** versions. This is the
  managed equivalent of 008's champion/challenger (FR-006) — use one or the other, not both.
- **FR-005** — **Serving**: default = the FastAPI app loads the **latest Approved** artifact from S3;
  **optional** = a **Serverless Inference** endpoint the app calls. **No always-on real-time endpoint**
  (cost). The choice is a single documented config.
- **FR-006** — **Drift monitoring**: **Model Monitor** (if an endpoint is used, with data capture) or a
  **scheduled batch drift job** (if serving from S3); breaches **alert**, feeding the same channel as 008.
- **FR-007** — **Explainability (stretch)**: **SageMaker Clarify** produces **SHAP** feature
  attributions for the model, attached to the model package — "which features drove this residual".
- **FR-008** — **Orchestration**: the pipeline is triggerable on a **schedule** (EventBridge) and from
  **CI/CD** (GitHub Actions, OIDC — no long-lived keys), consistent with 007.
- **FR-009** — **Infrastructure as code**: the SageMaker resources (pipeline definition, model package
  group, execution roles, optional endpoint, monitoring schedule) are **Terraform/IaC** under `infra/`,
  reusing 007's network/roles/state backend.
- **FR-010** — **Boundaries honored**: LLM features remain on Anthropic API/Bedrock; 008's LLM +
  data-quality + honest-language evals still run (this spec governs only the trained model).
- **FR-011** — **Right-sizing documented**: the doc states when the managed track is worth it vs the DIY
  path (007/008), so the choice is explicit, not cargo-culted.
- **FR-012** — **Cost + teardown**: ephemeral training jobs, serverless/scale-to-zero serving, documented
  `terraform destroy`; no orphaned billable resources (endpoints, monitoring schedules).

### Key Entities *(managed-ML objects)*

- **Pipeline**: the SageMaker Pipeline (steps: quality, train, evaluate, condition, register).
- **Model Package Group / Versions**: the registry — one group, many approved/pending versions with metrics.
- **Training Job**: an ephemeral managed run of `train.py`.
- **Endpoint (optional)**: a Serverless Inference endpoint + (optional) Model Monitor schedule.

## Success Criteria *(mandatory)*

- **SC-001**: A pipeline run trains, evaluates, and **registers a versioned model** with metrics — unattended.
- **SC-002**: A regressed challenger is **not Approved**; the champion keeps serving.
- **SC-003**: Serving uses only an **Approved** version, via S3-load (default) or Serverless endpoint — **no always-on instance**.
- **SC-004**: Drift monitoring runs and **alerts** on a breach.
- **SC-005**: The whole model-MLOps flow is **Terraform** + triggerable from CI/CD; **no console click-ops**.
- **SC-006**: `terraform destroy` removes all SageMaker billable resources (endpoints, schedules, jobs).
- **SC-007**: The 007/008 boundaries hold — app + LLM + honest-language checks are unchanged and still pass.

## Out of Scope

- Hosting the **LLM** on SageMaker (JumpStart/self-hosted models) — the project uses Claude via API/Bedrock.
- **Real-time (always-on) endpoints**, multi-model endpoints, A/B/shadow deployment (serverless is enough).
- **Feature Store** — the dbt `published` mart already serves that role.
- Replacing 007's app hosting or 008's **LLM** evaluation — those stand.

## Dependencies & risks (for the plan phase)

- **Pick one gate, not two:** SageMaker Registry approval (this spec, FR-004) **or** 008's own
  champion/challenger (008 FR-006) — running both duplicates the promotion logic. Decide in clarify.
- **Serving decision (FR-005)** drives how much SageMaker you actually stand up: S3-load keeps the API
  in charge (least SageMaker surface); a Serverless endpoint adds Model Monitor's natural home but more infra.
- **Cost creep** — endpoints + monitoring schedules bill even at zero traffic if left "always warm";
  serverless + teardown discipline (FR-012) is mandatory.
- **Complexity vs payoff** — for the current model this is deliberately more than needed (FR-011); keep
  the DIY path (007/008) available so the comparison is real.
