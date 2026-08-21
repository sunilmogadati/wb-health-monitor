# Stateful stores: ECR (images), S3 (raw zone + model artifacts), RDS Postgres (warehouse/mart/
# residuals). The `raw` zone and the model artifact move here intact from MinIO/local (Principle III).

# --- ECR: the API image (FR-001). The dashboard is a static export (no image) — see cloudfront.tf.

resource "aws_ecr_repository" "api" {
  name                 = "${var.project}/api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true # demo teardown (FR-012); set false for a real registry
  image_scanning_configuration { scan_on_push = true }
}

# --- S3: raw zone + model artifacts (FR-004/FR-006) --------------------------------------------

resource "aws_s3_bucket" "raw" {
  bucket_prefix = "${var.project}-raw-"
  force_destroy = true # demo teardown; a real raw zone is immutable and retained
}

resource "aws_s3_bucket" "artifacts" {
  bucket_prefix = "${var.project}-artifacts-"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration { status = "Enabled" } # keep a lineage of model versions
}

# --- RDS Postgres (FR-003) ---------------------------------------------------------------------

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db-subnets"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier             = "${var.project}-db"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  db_name                = var.db_name
  username               = var.db_username
  password               = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = false # single-AZ demo (FR-012)
  skip_final_snapshot    = true  # demo teardown; set false + a snapshot id for real data
  storage_encrypted      = true
  publicly_accessible    = false
  apply_immediately      = true
}
