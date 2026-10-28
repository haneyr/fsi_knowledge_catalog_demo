#!/bin/bash
set -e

export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="retail-kc-demo-ui-live"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BASIC_AGENT_ID="${BASIC_AGENT_ID:-$(gcloud secrets versions access latest --secret=retail-basic-agent-id --project="${PROJECT_ID}" 2>/dev/null || true)}"
SCALED_AGENT_ID="${SCALED_AGENT_ID:-$(gcloud secrets versions access latest --secret=retail-scaled-agent-id --project="${PROJECT_ID}" 2>/dev/null || true)}"
KC_AGENT_ID="${KC_AGENT_ID:-$(gcloud secrets versions access latest --secret=retail-kc-agent-id --project="${PROJECT_ID}" 2>/dev/null || true)}"
BASIC_AGENT_ID="${BASIC_AGENT_ID:?Set BASIC_AGENT_ID or store retail-basic-agent-id in Secret Manager}"
SCALED_AGENT_ID="${SCALED_AGENT_ID:?Set SCALED_AGENT_ID or store retail-scaled-agent-id in Secret Manager}"
KC_AGENT_ID="${KC_AGENT_ID:?Set KC_AGENT_ID or store retail-kc-agent-id in Secret Manager}"
# OAuth is required — read from env var or Secret Manager
if [ -z "${OAUTH_CLIENT_ID:-}" ]; then
    OAUTH_CLIENT_ID=$(gcloud secrets versions access latest --secret=retail-oauth-client-id \
        --project="${PROJECT_ID}" 2>/dev/null || true)
fi
if [ -z "${OAUTH_CLIENT_ID}" ]; then
    echo "ERROR: OAUTH_CLIENT_ID is required. Set it via environment variable or"
    echo "       store it in Secret Manager as 'retail-oauth-client-id'."
    echo "       The website must not be deployed without authentication."
    exit 1
fi

echo "=== Deploying Retail KC Demo Website (Live Mode) to Cloud Run ==="
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
# Session affinity + a warm min instance + a low max keep the in-memory WebSocket
# sessions (app.py) on a stable instance. Without these, reconnects land on cold or
# other instances and in-flight agent streams are cut off (#81).
gcloud run deploy "${SERVICE_NAME}" \
  --source=. \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --min-instances=1 \
  --max-instances=5 \
  --session-affinity \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},PROJECT_NUMBER=${PROJECT_NUMBER},BASIC_AGENT_ID=${BASIC_AGENT_ID},SCALED_AGENT_ID=${SCALED_AGENT_ID},KC_AGENT_ID=${KC_AGENT_ID},OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID},ENVIRONMENT_LABEL=${ENVIRONMENT_LABEL:-demo},SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT:-}" \
  --quiet

# --allow-unauthenticated is a separate IAM step that may fail if the org policy
# blocks allUsers bindings. Apply it best-effort after the deploy succeeds.
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --quiet 2>/dev/null || true

URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')
CANONICAL_URL="https://${SERVICE_NAME}-${PROJECT_NUMBER}.${REGION}.run.app"
echo ""
echo "=== Live Website Deployed! ==="
echo "  Canonical URL: ${CANONICAL_URL}"
echo "  Regional URL:  ${URL}"
echo "  Auth: Google Sign-In enabled"
echo "  Note: Add ${CANONICAL_URL} as authorized JavaScript origin in OAuth client config"
