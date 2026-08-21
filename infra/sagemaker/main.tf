# Managed MLOps on SageMaker (spec 009) — the ALTERNATIVE model track. Reference IaC, authored
# offline (not `terraform validate`d/applied). It replaces ONLY the trained model's lifecycle
# (train → register → gate → serve → monitor); the app + LLM features stay on specs 007/008.
#
# Serving default = the API loads the latest Approved artifact from S3 (spec 007 FR-006), so the
# SageMaker surface is minimal: a Model Registry group + a Pipeline. The Serverless endpoint +
# Model Monitor are authored but commented OFF (cost-gated opt-in, FR-005/FR-012).
#
# This is a separate root from ../ (the app infra). Point its provider at the same account/region and
# pass the artifact bucket + subnets in as vars; it reuses the S3 artifacts bucket 007 created.

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
    tags = { Project = var.project, Spec = "009-sagemaker-mlops", ManagedBy = "terraform" }
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

# The S3 artifacts bucket from spec 007 (data_stores.tf output `artifacts_bucket`). SageMaker training
# reads features / writes the model here — the SAME artifact contract the API loads from (FR-001/FR-006).
variable "artifacts_bucket" {
  type = string
}

data "aws_caller_identity" "current" {}

# --- Model Registry: one package group, many versioned+evaluated model versions (FR-003) --------

resource "aws_sagemaker_model_package_group" "life_expectancy" {
  model_package_group_name        = "${var.project}-life-expectancy"
  model_package_group_description = "Life-expectancy regressor — versioned, metric-attached, approval-gated (spec 009)."
}

# --- SageMaker execution role: run training jobs + the pipeline, read/write the artifacts bucket ---

resource "aws_iam_role" "sagemaker" {
  name_prefix = "${var.project}-sm-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_managed" {
  role       = aws_iam_role.sagemaker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy" "sagemaker_s3" {
  name_prefix = "artifacts-"
  role        = aws_iam_role.sagemaker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = ["arn:aws:s3:::${var.artifacts_bucket}", "arn:aws:s3:::${var.artifacts_bucket}/*"]
    }]
  })
}

# --- SageMaker Pipeline: quality → train → evaluate → condition → register (FR-002) -------------
# The definition JSON is produced by pipeline.py (the SageMaker SDK builder) and checked in as
# pipeline_definition.json. Regenerate it with:  python infra/sagemaker/pipeline.py > pipeline_definition.json
resource "aws_sagemaker_pipeline" "life_expectancy" {
  pipeline_name         = "${var.project}-life-expectancy"
  pipeline_display_name = "wbHealthLifeExpectancy"
  role_arn              = aws_iam_role.sagemaker.arn
  pipeline_definition   = file("${path.module}/pipeline_definition.json")
}

# --- OPTIONAL: Serverless Inference endpoint (FR-005) — OFF by default (cost). Uncomment to opt in.
# Serving default is S3-load in the API; enable this only if you want a managed endpoint + Model
# Monitor's natural home. Serverless scales to zero, so no always-on bill (FR-012).
#
# resource "aws_sagemaker_model" "approved" { ... latest Approved package ... }
# resource "aws_sagemaker_endpoint_configuration" "serverless" {
#   production_variants {
#     variant_name = "approved"
#     model_name   = aws_sagemaker_model.approved.name
#     serverless_config {
#       max_concurrency   = 2
#       memory_size_in_mb = 1024
#     }
#   }
# }
# resource "aws_sagemaker_endpoint" "serverless" {
#   endpoint_config_name = aws_sagemaker_endpoint_configuration.serverless.name
# }

output "model_package_group" {
  value = aws_sagemaker_model_package_group.life_expectancy.model_package_group_name
}

output "pipeline_name" {
  value = aws_sagemaker_pipeline.life_expectancy.pipeline_name
}
