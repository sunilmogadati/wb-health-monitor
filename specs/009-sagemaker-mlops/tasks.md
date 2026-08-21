# Tasks: Managed MLOps on SageMaker (spec 009)

**Status**: Accepted as an alternative track — SageMaker IaC (roles, package group, pipeline, condition step) + `pipeline.py` authored offline (reference, not validated/applied); script-mode/training-job/serving/drift + verify are credentialed-session items.

**Status**: Draft · **Plan**: `plan.md` · **Owner**: maintainer / advanced · Work in order; each maps to a spec FR / SC.

> Run `/speckit.clarify` first to settle two forks: **(1)** promotion gate = SageMaker Registry approval
> **or** 008's champion/challenger (not both); **(2)** serving = S3-load **or** Serverless Inference.

## Phase 0 — Prep the training code for managed runs
- [ ] **T001** Wrap `ml/train.py` as a SageMaker **script-mode** entry point (SKLearn container): read
  features from RDS/S3, write artifact + metadata to S3 via parameters — no logic change. (FR-001)
- [ ] **T002** App loads the **latest Approved** artifact URI (from the Registry/S3), env-driven —
  aligns with 007's `MODEL_URI`. (FR-005)

## Phase 1 — Registry + Training Job (IaC)
- [x] **T003** Terraform: SageMaker **execution roles** + **model package group**; reuse 007's
  network/state backend. (FR-003/FR-009)
- [ ] **T004** Terraform + code: a standalone **Training Job** that runs T001 and lands the artifact in
  S3. (FR-001)

## Phase 2 — The Pipeline + gate
- [x] **T005** SageMaker **Pipeline**: `data-quality → train → evaluate → condition → register`.
  (FR-002)
- [x] **T006** **Condition step** = the promotion gate: register/approve only if the challenger's metric
  is not worse than the current Approved champion past threshold; else leave Pending. (FR-002/FR-004/SC-002)
- [ ] **T007** Threshold + config in one documented place (RMSE tolerance, etc.), reusing 008's
  `thresholds` where they overlap. (FR-004)

## Phase 3 — Serving (per the clarify decision)
- [ ] **T008** Default: the API serves the **latest Approved** artifact from S3. *(If Serverless chosen
  instead:)* Terraform a **Serverless Inference** endpoint + the API client for it. **No always-on
  endpoint.** (FR-005/SC-003)

## Phase 4 — Drift + explainability
- [ ] **T009** **Drift**: Model Monitor (endpoint + data capture) **or** a scheduled batch drift job
  (S3-load); breach → alert via 008's channel. (FR-006/SC-004)
- [ ] **T010** *(stretch)* **Clarify**: SHAP attributions attached to the model package. (FR-007)

## Phase 5 — Orchestration + CI/CD
- [ ] **T011** Trigger the pipeline on an **EventBridge schedule** and from **GitHub Actions** (OIDC —
  no long-lived keys). (FR-008)

## Phase 6 — Prove, bound, document
- [ ] **T012** Verify the boundaries hold: 008's LLM + data-quality + honest-language checks still pass;
  the app/dashboard (007) are unchanged. (FR-010/SC-007)
- [x] **T013** `docs/SAGEMAKER.md`: the managed track, the **DIY-vs-managed decision** (FR-011), and
  **teardown**; confirm `terraform destroy` leaves no billable SageMaker resources. (FR-011/FR-012/SC-006)
- [ ] **T014** PR into `develop`; maintainer reviews against Success Criteria.