# ECS Fargate: the API and dashboard as long-running services, and the data pipeline as a scheduled
# task (FR-002/FR-005). All three run the same image family from ECR. Secrets are injected from
# Secrets Manager by the execution role (FR-007) — never baked into the image or task def in plaintext.

locals {
  # DB connection pulled from the db secret's JSON keys (ECS `secrets` valueFrom supports :key::).
  db_secrets = [
    { name = "POSTGRES_USER", valueFrom = "${aws_secretsmanager_secret.db.arn}:username::" },
    { name = "POSTGRES_PASSWORD", valueFrom = "${aws_secretsmanager_secret.db.arn}:password::" },
    { name = "POSTGRES_HOST", valueFrom = "${aws_secretsmanager_secret.db.arn}:host::" },
    { name = "POSTGRES_DB", valueFrom = "${aws_secretsmanager_secret.db.arn}:dbname::" },
  ]

  # Non-secret config the model/AI code reads (FR-006/FR-008). Note: S3_ENDPOINT_URL + S3_ACCESS_*
  # are deliberately NOT set here — unset means boto3 uses AWS's default endpoint + the IAM task role.
  data_env = [
    { name = "MODEL_ARTIFACT_DIR", value = "s3://${aws_s3_bucket.artifacts.bucket}/models" },
    { name = "S3_BUCKET_RAW", value = aws_s3_bucket.raw.bucket },
    { name = "PGPORT", value = "5432" },
  ]
}

resource "aws_ecs_cluster" "main" {
  name = "${var.project}-cluster"
}

resource "aws_cloudwatch_log_group" "main" {
  name              = "/ecs/${var.project}"
  retention_in_days = 14
}

# --- API service -------------------------------------------------------------------------------

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name         = "api"
    image        = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
    essential    = true
    portMappings = [{ containerPort = 8000 }]
    environment = concat(local.data_env, [
      { name = "CORS_ALLOWED_ORIGINS", value = local.app_url },
      { name = "ANTHROPIC_MODEL", value = "claude-sonnet-4-5" },
    ])
    secrets = concat(local.db_secrets, [
      { name = "ANTHROPIC_API_KEY", valueFrom = aws_secretsmanager_secret.anthropic.arn },
    ])
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.main.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${var.project}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.tasks.id]
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  depends_on = [aws_lb_listener.http]
}

# The dashboard is NOT an ECS service — it is a static export on S3 + CloudFront (cloudfront.tf,
# FR-002 v1.1.0). Only the API + the batch pipeline run on Fargate.

# --- Batch pipeline task (not a service — run on a schedule, FR-005) ---------------------------

resource "aws_ecs_task_definition" "pipeline" {
  family                   = "${var.project}-pipeline"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "pipeline"
    image     = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
    essential = true
    # ingest → dbt-build → train against RDS + S3 (the same steps `make` runs locally).
    command     = ["sh", "-lc", "python -m scripts.run_pipeline"]
    environment = local.data_env
    secrets     = local.db_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.main.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "pipeline"
      }
    }
  }])
}
