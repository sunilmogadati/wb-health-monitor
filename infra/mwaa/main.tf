# Managed Airflow on MWAA (spec 012) — the ALTERNATIVE orchestrator to EventBridge→Fargate (ADR-0002).
# Reference IaC, authored offline (not applied; MWAA bills ~$350+/mo even idle). It reuses spec 007's
# VPC + private subnets (passed as vars, like infra/sagemaker/). One orchestrator, not both (FR-004).

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, Spec = "012-mwaa-orchestration", ManagedBy = "terraform" }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "wb-health-monitor"
}

# From spec 007's outputs — MWAA runs in the same private network as the rest of the platform.
variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

# --- DAG bucket + the DAG object ---------------------------------------------------------------

resource "aws_s3_bucket" "dags" {
  bucket_prefix = "${var.project}-mwaa-"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "dags" {
  bucket = aws_s3_bucket.dags.id
  versioning_configuration { status = "Enabled" } # MWAA requires versioning on the DAG bucket
}

resource "aws_s3_bucket_public_access_block" "dags" {
  bucket                  = aws_s3_bucket.dags.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "dag" {
  bucket = aws_s3_bucket.dags.id
  key    = "dags/wb_pipeline.py"
  source = "${path.module}/dags/wb_pipeline.py"
  etag   = filemd5("${path.module}/dags/wb_pipeline.py")
}

# --- Execution role ----------------------------------------------------------------------------

data "aws_caller_identity" "current" {}

resource "aws_iam_role" "mwaa" {
  name_prefix = "${var.project}-mwaa-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = ["airflow.amazonaws.com", "airflow-env.amazonaws.com"] }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Least-privilege-ish for the demo: DAG bucket, logs, and the secrets the pipeline reads. Tighten for
# a real environment (MWAA publishes a recommended policy).
resource "aws_iam_role_policy" "mwaa" {
  name_prefix = "mwaa-"
  role        = aws_iam_role.mwaa.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket"]
        Resource = [aws_s3_bucket.dags.arn, "${aws_s3_bucket.dags.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:CreateLogGroup", "logs:PutLogEvents", "logs:GetLogEvents", "logs:DescribeLogGroups"]
        Resource = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:airflow-${var.project}-*"]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = ["arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${var.project}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["airflow:PublishMetrics"]
        Resource = ["arn:aws:airflow:${var.region}:${data.aws_caller_identity.current.account_id}:environment/${var.project}"]
      },
    ]
  })
}

# --- Security group ----------------------------------------------------------------------------

resource "aws_security_group" "mwaa" {
  name_prefix = "${var.project}-mwaa-"
  vpc_id      = var.vpc_id

  ingress {
    description = "Self"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  lifecycle { create_before_destroy = true }
}

# --- The MWAA environment (smallest class) -----------------------------------------------------

resource "aws_mwaa_environment" "main" {
  name               = var.project
  airflow_version    = "2.10.1"
  environment_class  = "mw1.small"
  execution_role_arn = aws_iam_role.mwaa.arn
  source_bucket_arn  = aws_s3_bucket.dags.arn
  dag_s3_path        = "dags"

  max_workers = 2
  min_workers = 1

  network_configuration {
    security_group_ids = [aws_security_group.mwaa.id]
    subnet_ids         = slice(var.private_subnet_ids, 0, 2)
  }

  logging_configuration {
    dag_processing_logs {
      enabled   = true
      log_level = "INFO"
    }
    task_logs {
      enabled   = true
      log_level = "INFO"
    }
  }

  webserver_access_mode = "PRIVATE_ONLY"
}

output "mwaa_environment" {
  value = aws_mwaa_environment.main.name
}

output "dag_bucket" {
  value = aws_s3_bucket.dags.bucket
}
