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

echo "=== Deploying FSI KC Demo Website (Live Mode) to Cloud Run ==="
echo "  Project: ${PROJECT_ID}"
echo "  Agents: basic=${BASIC_AGENT_ID} scaled=${SCALED_AGENT_ID} kc=${KC_AGENT_ID}"

# Enable required APIs (idempotent)
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com orgpolicy.googleapis.com \
  --project="${PROJECT_ID}" --quiet 2>/dev/null

# Grant Cloud Build permissions to compute SA
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder" --quiet 2>/dev/null | tail -1

# Override org policies for public access (idempotent)
gcloud org-policies reset constraints/iam.allowedPolicyMemberDomains \
  --project="${PROJECT_ID}" 2>/dev/null || true

gcloud resource-manager org-policies set-policy --project="${PROJECT_ID}" /dev/stdin 2>/dev/null <<'POLICY' || true
constraint: constraints/iam.allowedPolicyMemberDomains
listPolicy:
  allValues: ALLOW
POLICY

gcloud org-policies set-policy --project="${PROJECT_ID}" /dev/stdin 2>/dev/null <<'POLICY' || true
name: projects/${PROJECT_NUMBER}/policies/run.managed.requireInvokerIam
spec:
  rules:
  - enforce: false
POLICY

echo "  Waiting 10s for policy propagation..."
sleep 10

cd "${SCRIPT_DIR}"
gcloud run deploy "${SERVICE_NAME}" \
  --source=. \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --no-invoker-iam-check \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},PROJECT_NUMBER=${PROJECT_NUMBER},BASIC_AGENT_ID=${BASIC_AGENT_ID},SCALED_AGENT_ID=${SCALED_AGENT_ID},KC_AGENT_ID=${KC_AGENT_ID}" \
  --quiet

URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')
echo ""
echo "=== Live Website Deployed! ==="
echo "  URL: ${URL}"
