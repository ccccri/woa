#!/usr/bin/env bash
# Deploy the WOA backend with AWS SAM (reference deployment of ccccri).
# The user runs this in their own terminal: it asks for the only secret
# (the skill's Alexa Skill Messaging client secret) without echoing it.
#
# Usage: tools/deploy.sh            (first deploy and every update)
# Override any value with environment variables, e.g. REGION=us-east-1 tools/deploy.sh
set -euo pipefail

cd "$(dirname "$0")/.."

PROFILE="${PROFILE:-woa}"
REGION="${REGION:-eu-west-1}"           # D-016 (Alexa Europe region)
STACK="${STACK:-woa}"
SKILL_ID="${SKILL_ID:-amzn1.ask.skill.cf0d3465-5f2e-4fb5-8b8c-c58bb27a0ab0}"
LWA_CLIENT_ID="${LWA_CLIENT_ID:-amzn1.application-oa2-client.291a9a72786d49ab983dfa3165198459}"
ALEXA_CLIENT_ID="${ALEXA_CLIENT_ID:-amzn1.application-oa2-client.5212b8e810a94865a5a5c5d07e2edf60}"

export PATH="$HOME/.local/bin:$PATH"

echo "Checking AWS login for profile '$PROFILE'..."
if ! aws sts get-caller-identity --profile "$PROFILE" >/dev/null 2>&1; then
  echo "Not logged in (or session expired). Opening the browser login..."
  aws login --profile "$PROFILE" --region "$REGION"
fi

if [ -z "${ALEXA_CLIENT_SECRET:-}" ]; then
  echo
  echo "Paste the Alexa Skill Messaging CLIENT SECRET"
  echo "(Alexa console > WOA > Build > Permissions > Alexa Client Secret > SHOW)."
  read -rs -p "Secret (hidden): " ALEXA_CLIENT_SECRET
  echo
fi
if [ -z "$ALEXA_CLIENT_SECRET" ]; then
  echo "No secret given, stopping." >&2
  exit 1
fi

ALERT_EMAIL="${ALERT_EMAIL:-}"
while [[ ! "$ALERT_EMAIL" =~ ^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$ ]]; do
  echo
  echo "Type the email that should receive cost alerts (it cannot be empty)."
  read -r -p "Alert email: " ALERT_EMAIL
done

sam deploy \
  --template-file template.yaml \
  --profile "$PROFILE" --region "$REGION" --stack-name "$STACK" \
  --capabilities CAPABILITY_IAM --resolve-s3 \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "SkillId=$SKILL_ID" \
    "LwaClientId=$LWA_CLIENT_ID" \
    "AlexaClientId=$ALEXA_CLIENT_ID" \
    "AlexaClientSecret=$ALEXA_CLIENT_SECRET" \
    "AlertEmail=$ALERT_EMAIL"

# Remove the uploaded build artifacts (all versions): nothing stays stored in S3.
BUCKET="$(aws cloudformation describe-stacks --profile "$PROFILE" --region "$REGION" \
  --stack-name aws-sam-cli-managed-default \
  --query "Stacks[0].Outputs[?OutputKey=='SourceBucket'].OutputValue" --output text 2>/dev/null || true)"
if [ -n "$BUCKET" ] && [ "$BUCKET" != "None" ]; then
  echo "Cleaning build artifacts from s3://$BUCKET ..."
  python3 - "$PROFILE" "$REGION" "$BUCKET" <<'PY'
import json, subprocess, sys
profile, region, bucket = sys.argv[1:4]
def aws(*args):
    out = subprocess.run(["aws", *args, "--profile", profile, "--region", region, "--output", "json"],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out) if out.strip() else {}
while True:
    page = aws("s3api", "list-object-versions", "--bucket", bucket, "--max-items", "500")
    objs = [{"Key": o["Key"], "VersionId": o["VersionId"]}
            for o in page.get("Versions", []) + page.get("DeleteMarkers", [])]
    if not objs:
        break
    aws("s3api", "delete-objects", "--bucket", bucket, "--delete", json.dumps({"Objects": objs, "Quiet": True}))
print("Build artifacts removed.")
PY
fi

echo
echo "Cost guard: confirm the 'AWS Notification - Subscription Confirmation' email sent to $ALERT_EMAIL."
echo
echo "Stack outputs (give these to the agent):"
aws cloudformation describe-stacks --profile "$PROFILE" --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table
