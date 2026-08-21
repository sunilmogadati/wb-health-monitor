# VPC endpoints (FR-014): keep task↔AWS traffic on the AWS backbone instead of the NAT. The S3
# gateway endpoint is free and routes S3 traffic (raw zone + model artifacts); the interface
# endpoints (ECR pull, Secrets Manager, CloudWatch Logs) let tasks start + log without NAT egress.

# --- S3 gateway endpoint (free) — attach to the private route table --------------------------

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
  tags              = { Name = "${var.project}-s3-endpoint" }
}

# --- Interface endpoints — need a SG allowing 443 from the tasks ------------------------------

resource "aws_security_group" "endpoints" {
  name_prefix = "${var.project}-vpce-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTPS from tasks"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.tasks.id]
  }
  lifecycle { create_before_destroy = true }
  tags = { Name = "${var.project}-vpce-sg" }
}

locals {
  interface_endpoints = [
    "ecr.api",        # ECR control plane
    "ecr.dkr",        # ECR image layers (docker pull)
    "secretsmanager", # DB creds + Anthropic key at task start
    "logs",           # CloudWatch Logs (awslogs driver)
  ]
}

resource "aws_vpc_endpoint" "interface" {
  for_each            = toset(local.interface_endpoints)
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true
  tags                = { Name = "${var.project}-${each.value}-endpoint" }
}
