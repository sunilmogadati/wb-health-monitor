# infra/sagemaker/ — Managed MLOps on SageMaker (spec 009, alternative track)

The **managed** way to run the trained model's lifecycle — train → register → gate → serve → monitor —
as an explicit alternative to the DIY path in specs 002/008. **Reference IaC, authored offline** (not
`terraform validate`d/applied; the SageMaker SDK is not installed here).

> **Read the right-sizing note first:** for a ~357-row, 4-feature scikit-learn model this is **more
> machinery than the model needs**. Its value is teaching/portfolio (the managed pattern end-to-end)
> and headroom (it keeps working as the model grows). Adopt it deliberately, not by default.

## What it does — and does NOT — replace

- **Replaces** only the model's lifecycle: managed **Training Job**, **Model Registry** (versioned,
  metric-attached), a **Pipeline** with a metric **condition** gate, optional **Serverless** serving,
  optional **Model Monitor** drift.
- **Leaves in place:** the API + dashboard + RDS + S3 + ALB + app CI/CD (spec 007), and 008's **LLM**
  evals + data-quality + honest-language checks. SageMaker governs *your* model, not Claude.

## The two clarified decisions

- **Serving = S3-load by default.** The API loads the latest **Approved** artifact from the same S3
  bucket (spec 007 FR-006). The Serverless Inference endpoint is authored but **commented off** in
  `main.tf` — a cost-gated opt-in. No always-on endpoint.
- **One gate, not two.** On this managed track the **Registry approval** is the champion/challenger
  (`pipeline.py` condition step: register only if RMSE is not worse than the Approved champion +
  tolerance). It **replaces** 008's `should_promote`; don't run both.

## Files

| File | What |
|---|---|
| `main.tf` | Model package group, SageMaker execution role, `aws_sagemaker_pipeline`, optional endpoint (commented). Own Terraform root; pass `artifacts_bucket` from spec 007's output. |
| `pipeline.py` | SageMaker SDK builder for the DAG (quality → train → evaluate → condition → register). Reference; run in a credentialed session to regenerate the definition. |
| `pipeline_definition.json` | Placeholder so Terraform's `file()` resolves — **regenerate** from `pipeline.py`. |

## Apply (credentialed session)

```sh
cd infra/sagemaker
pip install "sagemaker>=2.200"
python pipeline.py > pipeline_definition.json      # regenerate the real definition
terraform init && terraform validate && terraform plan \
  -var="artifacts_bucket=$(cd .. && terraform output -raw artifacts_bucket)"
terraform apply
```

## Teardown (FR-012)

`terraform destroy`. If you enabled the Serverless endpoint + Model Monitor, confirm both are removed —
monitoring schedules bill even at zero traffic.
