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
