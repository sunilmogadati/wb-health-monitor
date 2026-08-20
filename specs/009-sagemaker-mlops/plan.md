# Implementation Plan: Managed MLOps on SageMaker (spec 009)

**Status**: Draft · **Spec**: `spec.md` · **Owner**: maintainer / advanced

## Summary

Run the trained model's lifecycle on SageMaker: `train.py` as a Training Job inside a SageMaker
Pipeline (data-quality → train → evaluate → condition → register), promotion via Model Registry
approval, serving from the latest Approved artifact (S3-load default, Serverless endpoint optional),
drift via Model Monitor. Layered on 007's infra; 008's LLM/data-quality/honest-language evals unchanged.

## Where it sits relative to 007 / 008

```
 STAYS (spec 007)                    THIS SPEC (009) — model lifecycle on SageMaker
 ────────────────                    ─────────────────────────────────────────────
 VPC · RDS · S3 · Secrets            SageMaker Pipeline:
 ECS Fargate: api + web · ALB          quality → Training Job → evaluate → [condition] → Registry
 app CI/CD (OIDC)                              │ Approved?
                                               ▼
 STAYS (spec 008)                    serve latest Approved:  API loads S3 artifact  (default)
 LLM evals (/ask,/brief)                                     └ or Serverless Inference endpoint
 data-quality + honest-language        Model Monitor (endpoint) / scheduled batch drift → alert
 —— these still run ——               Clarify (SHAP) attached to the model package (stretch)

 REPLACED by 009 (pick ONE):
   007 FR-005 Fargate batch-train  → SageMaker Training Job + Pipeline
   007 FR-006 artifact sharing     → Model Registry + S3
   008 FR-006 champion/challenger  → Registry approval gate
   008 model-drift                 → Model Monitor
```

## Constitution check (gate)

- **II Test-backed** ✅ the pipeline's condition step gates promotion on a metric; 008's checks still run.
- **V Honest modeling** ✅ residual semantics unchanged; honest-language checks from 008 still enforced.
- **I Public data / no secrets** ✅ IAM roles + Secrets Manager; no long-lived keys (OIDC from CI).

## Design decisions

1. **One SageMaker Pipeline, reusing `train.py`** — package the existing training code as the Training
   Job's entry point (SKLearn container / script mode), so the *same* logic runs managed. No model
   rewrite; only the I/O boundaries (read RDS/S3, write artifact to S3) are parameterized.
2. **Condition step = the gate** — after `evaluate`, a pipeline condition compares the challenger's
   metric to the current Approved package's metric; register+approve only if within threshold. This is
   008's champion/challenger, expressed as a managed step. **Use this OR 008's, not both.**
3. **Serving keeps the API in charge by default** — the FastAPI app loads the **latest Approved**
   artifact from S3 (the Registry records which S3 URI is Approved). A **Serverless Inference** endpoint
   is the opt-in alternative; **never** an always-on real-time endpoint.
4. **Drift home follows the serving choice** — endpoint → Model Monitor with data capture; S3-load → a
   scheduled batch drift job. Either way it alerts through 008's channel.
5. **IaC + triggers reuse 007** — Terraform for the pipeline/registry/roles/endpoint; EventBridge
   schedule + GitHub Actions (OIDC) start runs; approval auto-on-threshold or manual.
6. **Clarify is a stretch** — SHAP attributions attached to the package for explainability; skip if time-boxed.

## Files

- `infra/sagemaker/` — Terraform for the model package group, pipeline, execution roles, optional
  serverless endpoint + monitor schedule (reuses 007's network/state).
- `ml/sagemaker/` — the pipeline definition + step scripts (train entry point wrapping `ml/train.py`,
  an evaluate step, the register/condition wiring).
- app change: load the **latest Approved** artifact URI from the Registry/S3 (small, env-driven; aligns
  with 007 FR-006's `MODEL_URI`).
- `.github/workflows/` — a job to trigger the pipeline (OIDC).
- `docs/SAGEMAKER.md` — the managed track, the DIY-vs-managed decision, and teardown.

## Testing

- Pipeline dry-run / a real run registers a versioned package with metrics (SC-001).
- Condition step: a synthetic regressed challenger is **not** Approved; a better one is (SC-002).
- Serving: the app resolves and loads only the **Approved** artifact; a Serverless endpoint (if chosen)
  returns predictions with **no always-on instance** (SC-003).
- Drift job/monitor fires an alert on injected drift (SC-004).
- Boundary test: 008's LLM + honest-language checks still pass unchanged (SC-007).
- `terraform destroy` leaves no endpoints/schedules/jobs billing (SC-006).

## Sequencing

Depends on 002 (exists) + 007's infra. Build **after** 007 stands up (reuses its network/roles) and as a
**parallel alternative** to 008's model gate. Advanced/maintainer; not a jr ticket.
