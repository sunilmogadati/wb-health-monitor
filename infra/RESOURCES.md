# Resource inventory — what `terraform apply` creates, and what it costs

The default `infra/` plan creates **60 resources**. **`./infra/teardown.sh`** (or `terraform destroy`)
removes all of them — that is the exact undo. This file is the human-readable list + the honest cost.

## What actually bills (the ~$100/mo)

| Resource | ~Monthly (us-east-1, idle demo) | Note |
|---|---|---|
| `aws_nat_gateway.main` (+ `aws_eip.nat`) | **~$32** + data | Private-subnet egress. The single biggest line. |
| `aws_vpc_endpoint.interface` ×4 (ecr.api, ecr.dkr, secretsmanager, logs) | **~$29** (~$7.20 each) | A prod-scale optimization (skip the NAT for AWS APIs). At demo scale they can cost **more than they save** — drop `infra/vpc_endpoints.tf` to save ~$29/mo (tasks then reach those services via the NAT). |
| `aws_lb.main` | **~$16** + LCUs | The API load balancer. |
| `aws_db_instance.main` (RDS t4g.micro) | **~$12** | Single-AZ, 20 GB. |
| `aws_wafv2_web_acl.cloudfront` | **~$9** | $5 ACL + $1/rule × 4. Drop `infra/waf.tf` to save it. |
| `aws_ecs_service.api` (1 Fargate task, 0.25 vCPU / 0.5 GB) | **~$9** | Always-on API. |
| `aws_secretsmanager_secret` ×2 | ~$0.80 | $0.40 each. |
| `aws_cloudfront_distribution`, `aws_s3_bucket` ×3, `aws_ecr_repository` | **~cents** idle | Usage/storage-based. |
| Everything else (VPC, subnets, route tables, IGW, security groups, IAM ×9, S3 **gateway** endpoint, OIDC, scheduler, log group, task defs) | **$0** | Free to exist; some bill only on use. |

**Rough total left running: ~$100–110/mo.** ~**$0** after teardown. **Quick savings:** delete
`vpc_endpoints.tf` (−$29) and/or `waf.tf` (−$9) for a leaner demo (~$70/mo).

## The full 60 (Terraform addresses)

Network (18): `aws_vpc.main`, `aws_subnet.{public,private}[0..1]`, `aws_internet_gateway.main`,
`aws_nat_gateway.main`, `aws_eip.nat`, `aws_route_table.{public,private}`,
`aws_route_table_association.{public,private}[0..1]`, `aws_security_group.{alb,tasks,rds,endpoints}`.

VPC endpoints (5): `aws_vpc_endpoint.s3`, `aws_vpc_endpoint.interface["ecr.api"|"ecr.dkr"|"secretsmanager"|"logs"]`.

Data stores (9): `aws_db_instance.main`, `aws_db_subnet_group.main`, `aws_ecr_repository.api`,
`aws_s3_bucket.{raw,artifacts,web}`, `aws_s3_bucket_versioning.artifacts`, `aws_s3_bucket_policy.web`,
plus `aws_s3_bucket_public_access_block.{raw,artifacts,web}`.

Compute + schedule (6): `aws_ecs_cluster.main`, `aws_ecs_service.api`,
`aws_ecs_task_definition.{api,pipeline}`, `aws_cloudwatch_log_group.main`, `aws_scheduler_schedule.pipeline`.

Edge (4): `aws_lb.main`, `aws_lb_target_group.api`, `aws_lb_listener.http`,
`aws_cloudfront_distribution.web` (+ `aws_cloudfront_origin_access_control.web`), `aws_wafv2_web_acl.cloudfront`.

Secrets + IAM (14): `aws_secretsmanager_secret.{db,anthropic}`, `aws_secretsmanager_secret_version.db`,
`random_password.db`, `aws_iam_role.{execution,task,scheduler,github_deploy}`,
`aws_iam_role_policy.{execution_secrets,task_s3,scheduler}`,
`aws_iam_role_policy_attachment.{execution_managed,github_deploy}`, `aws_iam_openid_connect_provider.github`.

*(With custom domains set, add ACM certs + Route53 records; with the API subdomain, an ALB HTTPS
listener. The SageMaker (009) and MWAA (012) alternative tracks are separate roots — destroy those
too if you applied them.)*

## Undo

```sh
./infra/teardown.sh          # terraform destroy + verify nothing tagged remains
# or, manually:
cd infra && AWS_PROFILE=wb-deploy terraform destroy
```
Demo resources set `force_destroy`/`skip_final_snapshot`, so destroy leaves nothing behind. Secrets
enter a recovery window (they don't bill); force-delete them if you want them gone immediately.
