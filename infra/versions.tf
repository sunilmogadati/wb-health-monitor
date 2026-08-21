# Terraform + provider pins and the remote-state backend (spec 007 FR-009).
#
# The S3 backend + DynamoDB lock keep state off laptops and prevent concurrent applies. The backend
# bucket/table must exist BEFORE `terraform init` (chicken-and-egg) — create them once as a bootstrap
# (see infra/README.md), then fill in the values below and re-init.

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  # Uncomment and set after the bootstrap bucket/table exist (README → "Bootstrap remote state").
  # backend "s3" {
  #   bucket         = "wb-health-monitor-tfstate"
  #   key            = "007-deployment/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "wb-health-monitor-tflock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      Spec      = "007-deployment-aws"
      ManagedBy = "terraform"
    }
  }
}

# CloudFront's ACM cert and a CLOUDFRONT-scoped WAF must live in us-east-1, regardless of var.region.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project   = var.project
      Spec      = "007-deployment-aws"
      ManagedBy = "terraform"
    }
  }
}
