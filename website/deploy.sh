#!/bin/bash
set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="fsi-kc-demo-ui"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Deploying FSI KC Demo Website to Cloud Run ==="
echo "  Project: ${PROJECT_ID}"
echo "  Region: ${REGION}"

# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com orgpolicy.googleapis.com \
  --project="${PROJECT_ID}" --quiet 2>/dev/null

# Grant Cloud Build permissions to compute SA
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder" --quiet 2>/dev/null | tail -1

# Override org policies to allow public Cloud Run access
echo "  Configuring org policies for public access..."
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

echo "  Waiting 30s for policy propagation..."
sleep 30

# Deploy to Cloud Run
cd "${SCRIPT_DIR}"
gcloud run deploy "${SERVICE_NAME}" \
  --source=. \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --no-invoker-iam-check \
  --memory=512Mi \
  --cpu=1 \
  --timeout=120 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION}" \
  --quiet

URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')
echo ""
echo "=== Website Deployed! ==="
echo "  URL: ${URL}"
