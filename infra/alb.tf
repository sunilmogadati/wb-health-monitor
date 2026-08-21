# Application Load Balancer (FR-002, v1.1.0). The ALB now fronts ONLY the API — CloudFront serves the
# dashboard from S3 and forwards `/api/*` to this ALB (cloudfront.tf). CloudFront terminates TLS at the
# edge, so the ALB origin is plain HTTP; it is reachable only via CloudFront + the security groups.

resource "aws_lb" "main" {
  name               = "${var.project}-alb"
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "api" {
  name        = "${var.project}-api"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip" # Fargate awsvpc
  health_check {
    path                = "/api/v1/health"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 5
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# HTTPS on the ALB — only when the API has its own subdomain (FR-015). Lets `api.example.com` reach
# the API directly with TLS terminated at the ALB (no API Gateway). CloudFront still uses HTTP:80.
resource "aws_lb_listener" "https" {
  count             = local.enable_api_domain ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = local.api_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
