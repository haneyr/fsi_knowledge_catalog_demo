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
# OAuth is required — read from env var or Secret Manager
if [ -z "${OAUTH_CLIENT_ID:-}" ]; then
    OAUTH_CLIENT_ID=$(gcloud secrets versions access latest --secret=oauth-client-id \
        --project="${PROJECT_ID}" 2>/dev/null || true)
fi
if [ -z "${OAUTH_CLIENT_ID}" ]; then
    echo "ERROR: OAUTH_CLIENT_ID is required. Set it via environment variable or"
    echo "       store it in Secret Manager as 'oauth-client-id'."
    echo "       The website must not be deployed without authentication."
    exit 1
fi

echo "=== Deploying FSI KC Demo Website (Live Mode) to Cloud Run ==="
echo "  Project: ${PROJECT_ID}"
echo "  Agents: basic=${BASIC_AGENT_ID} scaled=${SCALED_AGENT_ID} kc=${KC_AGENT_ID}"
echo "  OAuth: enabled"

# Enable required APIs (idempotent; may fail in CI if SA lacks serviceusage permissions)
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com orgpolicy.googleapis.com \
  --project="${PROJECT_ID}" --quiet 2>/dev/null || true

# Grant Cloud Build permissions to compute SA (may fail in CI)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder" --quiet 2>/dev/null || true

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
echo "  Auth: Google Sign-In enabled"
echo "  Note: Add ${URL} as authorized JavaScript origin in OAuth client config"
