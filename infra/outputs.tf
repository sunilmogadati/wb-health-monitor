# What CI/CD and an operator need after apply.

output "app_url" {
  description = "Public URL of the dashboard (and /api/v1 for the API)."
  value       = local.app_url
}

output "api_health_url" {
  description = "Post-deploy smoke-test target (FR-011)."
  value       = "${local.app_url}/api/v1/health"
}

output "ecr_api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_web_repository_url" {
  value = aws_ecr_repository.web.repository_url
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

output "artifacts_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_DEPLOY_ROLE_ARN GitHub secret for the OIDC deploy (FR-010)."
  value       = aws_iam_role.github_deploy.arn
}
