# What CI/CD and an operator need after apply.

output "app_url" {
  description = "Public URL of the dashboard (CloudFront); /api/v1 is proxied to the ALB same-origin."
  value       = local.app_url
}

output "api_health_url" {
  description = "Post-deploy smoke-test target (FR-011)."
  value       = "${local.app_url}/api/v1/health"
}

output "ecr_api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "web_bucket" {
  description = "S3 bucket the built dashboard (frontend/out) is synced to."
  value       = aws_s3_bucket.web.bucket
}

output "cloudfront_distribution_id" {
  description = "For cache invalidation after a web deploy."
  value       = aws_cloudfront_distribution.web.id
}

output "ecs_cluster" {
  value = aws_ecs_cluster.main.name
}

output "pipeline_task_definition" {
  description = "Run once manually with `aws ecs run-task` to seed data before the first schedule."
  value       = aws_ecs_task_definition.pipeline.arn
}

output "rds_endpoint" {
  value     = aws_db_instance.main.address
  sensitive = true
}

output "db_secret_arn" {
  description = "Secrets Manager ARN holding the DB creds — CI reads it to build DATABASE_URL for migrations."
  value       = aws_secretsmanager_secret.db.arn
}

output "artifacts_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_DEPLOY_ROLE_ARN GitHub secret for the OIDC deploy (FR-010)."
  value       = aws_iam_role.github_deploy.arn
}
