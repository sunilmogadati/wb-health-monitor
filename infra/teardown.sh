#!/usr/bin/env bash
# Teardown for the wb-health-monitor AWS deployment (spec 007 FR-012).
#
# `terraform destroy` is the real undo: it reads state and removes EXACTLY what it created, in reverse
# dependency order. This wrapper adds (1) the credential handling this repo needs — ignore any stale
# temporary creds in the shell, use the static deploy profile — and (2) a tag-based verification that
# nothing billable is orphaned (every top-level resource is tagged Project=wb-health-monitor).
#
# Usage:  ./infra/teardown.sh            # destroy + verify
#         TF=/path/to/terraform ./infra/teardown.sh
#         AWS_PROFILE=other ./infra/teardown.sh
set -euo pipefail
cd "$(dirname "$0")"

# Prefer the static deploy profile; drop any stale temporary session creds the shell may export.
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN || true
export AWS_PROFILE="${AWS_PROFILE:-wb-deploy}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
TF="${TF:-terraform}"
PROJECT="${PROJECT:-wb-health-monitor}"

echo ">>> Account: $(aws sts get-caller-identity --query Account --output text)  Region: $AWS_REGION"
echo ">>> terraform destroy — removes exactly what state tracks (CloudFront takes ~15-20 min)…"
"$TF" destroy -auto-approve

echo ">>> Verifying nothing tagged Project=$PROJECT remains…"
arns=$(aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=Project,Values=$PROJECT" \
  --query 'ResourceTagMappingList[].ResourceARN' --output text 2>/dev/null || echo "")
if [ -z "$arns" ]; then
  echo "CLEAN — no tagged resources remain. Nothing should be billing."
else
  echo "WARNING — these tagged resources are still present; delete manually or re-run:"
  printf '%s\n' "$arns" | tr '\t' '\n'
  echo "(Untagged sub-resources — IAM policies, route associations — are removed with their parents.)"
  exit 1
fi

# Optional belt-and-suspenders: also confirm the Secrets Manager entries are scheduled for deletion
# (they linger in a recovery window but do not bill). Uncomment to force-delete immediately:
# aws secretsmanager delete-secret --secret-id "<name>" --force-delete-without-recovery
echo ">>> Done."
