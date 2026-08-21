# Custom domains (FR-015) — no API Gateway. The app gets a domain via CloudFront + an ACM cert in
# us-east-1; the API optionally gets a subdomain via an ALB HTTPS listener + a regional cert. Both are
# DNS-validated in an EXISTING Route53 zone (the domain must already be registered/delegated — a
# manual step, see docs/DEPLOYMENT.md). All gated on optional vars: unset ⇒ default AWS hostnames.

locals {
  enable_dns        = var.route53_zone_name != ""
  enable_app_domain = local.enable_dns && var.domain_name != ""
  enable_api_domain = local.enable_dns && var.api_domain_name != ""

  app_certificate_arn = local.enable_app_domain ? aws_acm_certificate_validation.app[0].certificate_arn : ""
  api_certificate_arn = local.enable_api_domain ? aws_acm_certificate_validation.api[0].certificate_arn : ""
}

data "aws_route53_zone" "main" {
  count = local.enable_dns ? 1 : 0
  name  = var.route53_zone_name
}

# --- App certificate (CloudFront → us-east-1) --------------------------------------------------

resource "aws_acm_certificate" "app" {
  count             = local.enable_app_domain ? 1 : 0
  provider          = aws.us_east_1
  domain_name       = var.domain_name
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
}

resource "aws_route53_record" "app_validation" {
  for_each = {
    for dvo in(local.enable_app_domain ? aws_acm_certificate.app[0].domain_validation_options : []) :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "app" {
  count                   = local.enable_app_domain ? 1 : 0
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.app[0].arn
  validation_record_fqdns = [for r in aws_route53_record.app_validation : r.fqdn]
}

resource "aws_route53_record" "app_alias" {
  count   = local.enable_app_domain ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.web.domain_name
    zone_id                = aws_cloudfront_distribution.web.hosted_zone_id
    evaluate_target_health = false
  }
}

# --- API certificate (ALB → regional, var.region) ----------------------------------------------

resource "aws_acm_certificate" "api" {
  count             = local.enable_api_domain ? 1 : 0
  domain_name       = var.api_domain_name
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
}

resource "aws_route53_record" "api_validation" {
  for_each = {
    for dvo in(local.enable_api_domain ? aws_acm_certificate.api[0].domain_validation_options : []) :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "api" {
  count                   = local.enable_api_domain ? 1 : 0
  certificate_arn         = aws_acm_certificate.api[0].arn
  validation_record_fqdns = [for r in aws_route53_record.api_validation : r.fqdn]
}

resource "aws_route53_record" "api_alias" {
  count   = local.enable_api_domain ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.api_domain_name
  type    = "A"
  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
