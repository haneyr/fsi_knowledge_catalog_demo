#!/bin/bash
set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="fsi-kc-demo-ui-live"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BASIC_AGENT_ID="${BASIC_AGENT_ID:?Set BASIC_AGENT_ID}"
SCALED_AGENT_ID="${SCALED_AGENT_ID:?Set SCALED_AGENT_ID}"
KC_AGENT_ID="${KC_AGENT_ID:?Set KC_AGENT_ID}"
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:-}"

echo "=== Deploying FSI KC Demo Website (Live Mode) to Cloud Run ==="
echo "  Project: ${PROJECT_ID}"
echo "  Agents: basic=${BASIC_AGENT_ID} scaled=${SCALED_AGENT_ID} kc=${KC_AGENT_ID}"
if [ -n "${OAUTH_CLIENT_ID}" ]; then
    echo "  OAuth: enabled"
else
    echo "  OAuth: disabled (set OAUTH_CLIENT_ID to enable)"
fi

# Enable required APIs (idempotent)
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com orgpolicy.googleapis.com \
  --project="${PROJECT_ID}" --quiet 2>/dev/null

# Grant Cloud Build permissions to compute SA
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder" --quiet 2>/dev/null | tail -1

# Override org policy: app manages its own auth via Google Identity Services
# Cloud Run must accept unauthenticated requests so users can reach the login page
gcloud org-policies set-policy --project="${PROJECT_ID}" /dev/stdin 2>/dev/null <<POLICY || true
name: projects/${PROJECT_NUMBER}/policies/run.managed.requireInvokerIam
spec:
  rules:
  - enforce: false
POLICY
sleep 5

cd "${SCRIPT_DIR}"
gcloud run deploy "${SERVICE_NAME}" \
  --source=. \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},PROJECT_NUMBER=${PROJECT_NUMBER},BASIC_AGENT_ID=${BASIC_AGENT_ID},SCALED_AGENT_ID=${SCALED_AGENT_ID},KC_AGENT_ID=${KC_AGENT_ID},OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID},ENVIRONMENT_LABEL=${ENVIRONMENT_LABEL:-},SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT:-},SNOWFLAKE_AGENT_USER=${SNOWFLAKE_AGENT_USER:-},SNOWFLAKE_AGENT_PASSWORD=${SNOWFLAKE_AGENT_PASSWORD:-},SNOWFLAKE_WAREHOUSE=${SNOWFLAKE_WAREHOUSE:-},SNOWFLAKE_DATABASE=${SNOWFLAKE_DATABASE:-}" \
  --quiet || true
# Note: --allow-unauthenticated may fail if the org policy blocks allUsers IAM
# bindings. The deploy itself succeeds; access is managed via org policy overrides
# and domain-scoped IAM grants (see docs/ci-setup.md).

URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')
echo ""
echo "=== Live Website Deployed! ==="
echo "  URL: ${URL}"
if [ -n "${OAUTH_CLIENT_ID}" ]; then
    echo "  Auth: Google Sign-In enabled"
    echo "  Note: Add ${URL} as authorized JavaScript origin in OAuth client config"
fi
