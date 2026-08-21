# Secrets (FR-007). No secret is committed or kept in plaintext in the repo. The DB password is
# generated here and stored in Secrets Manager; the Anthropic key's secret is CREATED empty by
# Terraform and its value is put in out-of-band (README) so the key never enters Terraform state.

resource "random_password" "db" {
  length  = 24
  special = false # RDS master password disallows some symbols; keep it alnum-safe
}

resource "aws_secretsmanager_secret" "db" {
  name_prefix = "${var.project}/db-"
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db.result
    host     = aws_db_instance.main.address
    port     = 5432
    dbname   = var.db_name
  })
}

# Created empty; set the value with:
#   aws secretsmanager put-secret-value --secret-id <name> --secret-string sk-ant-...
resource "aws_secretsmanager_secret" "anthropic" {
  name_prefix = "${var.project}/anthropic-"
}
