# Deployment (spec 007) — the runbook

How the platform goes to AWS, and **what you do by hand vs. what Terraform does**. The IaC lives in
`infra/` (and `infra/sagemaker/` for the managed-ML alternative, spec 009). Terraform 1.6+.

> Status: the IaC is **`terraform validate`-clean** but not yet applied to an account. Your first
> `terraform plan` in a real account is where account-specific issues (IAM evaluation, name
> collisions, quotas) surface — reconcile those before `apply`.

## Architecture (what gets stood up)

```
                         ┌──────────── CloudFront (+ WAFv2) ────────────┐
   browser ──HTTPS──►    │  default → S3 (static dashboard, private/OAC)  │
                         │  /api/*  → ALB → ECS Fargate: api             │
                         └───────────────────────────────────────────────┘
   api.example.com ──HTTPS──► ALB (optional dedicated API subdomain)
                                     │
   ECS Fargate: api ─────────────────┼──► RDS Postgres (warehouse/mart/residuals)
   Scheduled Fargate: pipeline ──────┘──► S3 (raw zone + model artifacts)
   (EventBridge cron → run_pipeline.py)   Secrets Manager (DB creds + Anthropic key)
   VPC endpoints: S3 (gw) + ECR/Secrets/Logs (interface) → tasks skip the NAT for AWS services
```

## Manual steps (you, in the AWS console / CLI) — Terraform can't or shouldn't do these

1. **Domain + Route53 hosted zone** *(only if you want custom domains, FR-015)*
   - Register the domain (Route53 registrar or elsewhere). If registered elsewhere, create a Route53
     **hosted zone** for it and **update the registrar's NS records** to Route53's — DNS delegation is a
     manual, propagation-delayed step Terraform shouldn't own.
   - You pass the zone name to Terraform as `route53_zone_name`; it looks the zone up (does not create
     it) and writes the ACM validation + alias records into it.
2. **Bootstrap the Terraform state backend** (chicken-and-egg — state can't store its own bucket):
   ```sh
   aws s3 mb s3://wb-health-monitor-tfstate
   aws s3api put-bucket-versioning --bucket wb-health-monitor-tfstate \
     --versioning-configuration Status=Enabled
   aws dynamodb create-table --table-name wb-health-monitor-tflock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST
   ```
   Then uncomment the `backend "s3"` block in `infra/versions.tf`.
3. **Anthropic key value** — Terraform creates the secret **empty** (so the key never enters state);
   you set the value once after apply:
   ```sh
   aws secretsmanager put-secret-value --secret-id "$(terraform -chdir=infra output -raw ... )" \
     --secret-string sk-ant-...
   ```
   (Find the secret name in the console or from the `anthropic` secret in `infra/secrets.tf`.)
4. **GitHub repo config for CI/CD** (the OIDC *role* is created by Terraform; wiring GitHub is manual):
   - Repo **variables**: `DEPLOY_ENABLED=true`, `AWS_REGION`, `PROJECT=wb-health-monitor`.
   - Repo **secret**: `AWS_DEPLOY_ROLE_ARN` = the `github_deploy_role_arn` Terraform output.
5. **ACM validation approval** is automated when the zone is in Route53 (Terraform writes the DNS
   records). If the domain is delegated late, the `aws_acm_certificate_validation` waits — finish the
   NS delegation (step 1) first.

## What Terraform automates (the rest)

VPC + public/private subnets + **VPC endpoints** (S3 gateway; ECR/Secrets/Logs interface) + security
groups + NAT; **RDS** Postgres; **S3** (raw, versioned artifacts, private web bucket); **ECR** (api
image); **ECS** cluster + api service + scheduled pipeline task; **ALB** (+ optional HTTPS listener for
the API subdomain); **CloudFront** + **WAFv2** (managed rules + rate limit); **ACM** certs (app in
us-east-1, API regional) + **Route53** validation & alias records; **Secrets Manager** (DB creds
generated; Anthropic secret shell); **IAM** (task/exec/scheduler roles + GitHub OIDC role);
**EventBridge** schedule.

## Ordered deploy

```sh
# 0. Manual steps 1–2 above (domain/zone if using; state bootstrap).
cd infra
terraform init
terraform plan  -out=tfplan \
  -var="route53_zone_name=example.com" \       # omit these three for default hostnames
  -var="domain_name=app.example.com" \
  -var="api_domain_name=api.example.com"
terraform apply tfplan
# 1. Manual step 3 (Anthropic secret value) + step 4 (GitHub vars/secrets).
# 2. Ship the app: push to main → CI builds/pushes the API image, applies, s3-syncs the dashboard,
#    invalidates CloudFront, runs `alembic upgrade head`, and smoke-tests /api/v1/health.
# 3. Seed data (first run): trigger the pipeline once —
aws ecs run-task --cluster "$(terraform output -raw ecs_cluster)" \
  --task-definition "$(terraform output -raw pipeline_task_definition)" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<private-subnets>],securityGroups=[<tasks-sg>]}"
# Until the first pipeline run, /predict|/brief|/benchmark degrade gracefully (spec 002/005), not 500.
```

## Custom domains — recap (no API Gateway)

- **App** → `domain_name` on CloudFront (ACM us-east-1 + Route53 alias). WAF sits in front.
- **API** → *same-origin* at `<app>/api/v1` via the CloudFront `/api/*` behavior (no extra domain), **or**
  a dedicated `api_domain_name` on the **ALB HTTPS listener** (regional ACM + Route53 alias). ALB + ACM
  give the API its domain + TLS; API Gateway is not needed.

## Teardown (FR-012)

```sh
cd infra && terraform destroy
```
Demo resources set `force_destroy`/`skip_final_snapshot`, so nothing bills after. For real data, take a
final RDS snapshot and empty/retain the buckets first. If you enabled the SageMaker track (009) or an
MWAA environment (012), destroy those roots too — endpoints/environments bill even at zero traffic.

## Rough cost (single-AZ demo, us-east-1)

NAT (~$32/mo) + ALB (~$16/mo) + RDS t4g.micro (~$12/mo) + CloudFront/WAF/S3 (traffic-based, cents) +
Fargate (api ~$9/mo, pipeline per-run). ≈ **$70–90/mo** left running; **~$0** after `destroy`. The VPC
endpoints trade a little hourly cost for less NAT egress at scale.
