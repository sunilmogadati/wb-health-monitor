# WAFv2 web ACL on CloudFront (FR-013). Scope CLOUDFRONT ⇒ it MUST be created in us-east-1. Blocks
# the obvious edge attacks (common exploits, known-bad inputs, SQLi) and rate-limits abusive clients
# before anything reaches the ALB/API. Requests are sampled to CloudWatch for visibility.

resource "aws_wafv2_web_acl" "cloudfront" {
  provider = aws.us_east_1
  name     = "${var.project}-cf-acl"
  scope    = "CLOUDFRONT"

  default_action {
    allow {}
  }

  # AWS managed rule groups (maintained by AWS; count-vs-block is per-group default).
  rule {
    name     = "common"
    priority = 1
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "common"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "known-bad-inputs"
    priority = 2
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "known-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "sqli"
    priority = 3
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesSQLiRuleSet"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "sqli"
      sampled_requests_enabled   = true
    }
  }

  # Rate limit: block an IP exceeding 2000 requests / 5 min (tune per real traffic).
  rule {
    name     = "rate-limit"
    priority = 4
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "rate-limit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project}-cf-acl"
    sampled_requests_enabled   = true
  }
}
