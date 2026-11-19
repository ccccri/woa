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
REGION="${REGION:-eu-north-1}"          # D-013
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

sam deploy \
  --template-file template.yaml \
  --profile "$PROFILE" --region "$REGION" --stack-name "$STACK" \
  --capabilities CAPABILITY_IAM --resolve-s3 \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "SkillId=$SKILL_ID" \
    "LwaClientId=$LWA_CLIENT_ID" \
    "AlexaClientId=$ALEXA_CLIENT_ID" \
    "AlexaClientSecret=$ALEXA_CLIENT_SECRET"

echo
echo "Stack outputs (give these to the agent):"
aws cloudformation describe-stacks --profile "$PROFILE" --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table
