#!/bin/bash
# P2 — GCP Pre-Flight Script (idempotent)
# 1. Enables required APIs on alitch-ca-demo
# 2. Writes scripts/config.json
# 3. Attempts both org-policy overrides (iam.allowedPolicyMemberDomains & run.managed.requireInvokerIam)
# 4. Checks Agent Engine availability/quota in us-central1 and checks for retail_* collisions

set -euo pipefail

export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false

PROJECT_ID="alitch-ca-demo"
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
ACCOUNT_EMAIL=$(gcloud config get-value account 2>/dev/null || echo "admin@aelitchfield.altostrat.com")
REGION="us-central1"
MULTI_REGION="us"

echo "=== 1. Enabling Required APIs on ${PROJECT_ID} (${PROJECT_NUMBER}) ==="
APIS=(
  bigquery.googleapis.com
  dataplex.googleapis.com
  datalineage.googleapis.com
  aiplatform.googleapis.com
  cloudresourcemanager.googleapis.com
  iam.googleapis.com
  cloudaicompanion.googleapis.com
  run.googleapis.com
  cloudbuild.googleapis.com
  secretmanager.googleapis.com
  artifactregistry.googleapis.com
  datacatalog.googleapis.com
  orgpolicy.googleapis.com
)
gcloud services enable "${APIS[@]}" --project="${PROJECT_ID}" --quiet
echo "Verified enabled APIs:"
gcloud services list --enabled --project="${PROJECT_ID}" \
  --filter="config.name:(bigquery.googleapis.com OR dataplex.googleapis.com OR datalineage.googleapis.com OR aiplatform.googleapis.com OR cloudresourcemanager.googleapis.com OR iam.googleapis.com OR cloudaicompanion.googleapis.com OR run.googleapis.com OR cloudbuild.googleapis.com OR secretmanager.googleapis.com OR artifactregistry.googleapis.com OR datacatalog.googleapis.com OR orgpolicy.googleapis.com)" \
  --format="value(config.name)" | sort

echo ""
echo "=== 2. Writing scripts/config.json ==="
cat > scripts/config.json <<EOF
{
  "project_id": "${PROJECT_ID}",
  "project_number": "${PROJECT_NUMBER}",
  "region": "${REGION}",
  "multi_region": "${MULTI_REGION}",
  "gcp_account_name": "${ACCOUNT_EMAIL}"
}
EOF
echo "Wrote scripts/config.json (project_id=${PROJECT_ID}, project_number=${PROJECT_NUMBER}, region=${REGION}, multi_region=${MULTI_REGION}, gcp_account_name=${ACCOUNT_EMAIL})"

echo ""
echo "=== 3. Attempting Org-Policy Overrides ==="
ORG_POLICY_STATUS="SUCCESS"
echo "Applying override for iam.allowedPolicyMemberDomains (ListConstraint: allowAll: true)..."
if gcloud org-policies set-policy --project="${PROJECT_ID}" /dev/stdin <<POLICY 2>&1; then
name: projects/${PROJECT_NUMBER}/policies/iam.allowedPolicyMemberDomains
spec:
  rules:
  - allowAll: true
POLICY
  echo "  [OK] iam.allowedPolicyMemberDomains -> allowAll: true"
else
  echo "  [FALLBACK] iam.allowedPolicyMemberDomains override returned error/PERMISSION_DENIED"
  ORG_POLICY_STATUS="FALLBACK_IAM_INVOKER"
fi

echo "Applying override for run.managed.requireInvokerIam (BooleanConstraint: enforce: false)..."
if gcloud org-policies set-policy --project="${PROJECT_ID}" /dev/stdin <<POLICY 2>&1; then
name: projects/${PROJECT_NUMBER}/policies/run.managed.requireInvokerIam
spec:
  rules:
  - enforce: false
POLICY
  echo "  [OK] run.managed.requireInvokerIam -> enforce: false"
else
  echo "  [FALLBACK] run.managed.requireInvokerIam override returned error/PERMISSION_DENIED"
  ORG_POLICY_STATUS="FALLBACK_IAM_INVOKER"
fi
echo "Org-Policy Outcome: ${ORG_POLICY_STATUS}"

echo ""
echo "=== 4. Confirming Vertex AI Agent Engine Availability & Checking Collisions ==="
TOKEN=$(gcloud auth print-access-token)
AE_RESP=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
  "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines")
AE_CODE=$(echo "${AE_RESP}" | grep "HTTP_STATUS:" | cut -d: -f2)
echo "Agent Engine API (us-central1) HTTP status: ${AE_CODE}"
echo "${AE_RESP}" | grep -v "HTTP_STATUS:" | python3 -c "
import sys, json
data = json.load(sys.stdin)
engines = data.get('reasoningEngines', [])
print(f'Existing ReasoningEngines: {len(engines)}')
for e in engines:
    print('  -', e.get('name', '').split('/')[-1], '|', e.get('displayName', ''))
"

echo ""
echo "=== 5. Checking for Retail Namespace Collisions ==="
echo -n "BigQuery retail_* datasets: "
bq ls --project_id="${PROJECT_ID}" --format=json | python3 -c "
import sys, json
ds = json.load(sys.stdin) or []
retail_ds = [d['datasetReference']['datasetId'] for d in ds if d['datasetReference']['datasetId'].startswith('retail_')]
all_ds = [d['datasetReference']['datasetId'] for d in ds]
print(f'{len(retail_ds)} retail_* collisions (existing non-retail datasets: {len(all_ds)}: {all_ds[:5]}...)')
"

echo -n "Dataplex retail-* glossaries (us): "
curl -s -H "Authorization: Bearer ${TOKEN}" \
  "https://dataplex.googleapis.com/v1/projects/${PROJECT_ID}/locations/us/glossaries" | python3 -c "
import sys, json
g = json.load(sys.stdin).get('glossaries', [])
rg = [x['name'].split('/')[-1] for x in g if 'retail' in x['name']]
print(f'{len(rg)} retail-* collisions (existing glossaries: {[x[\"name\"].split(\"/\")[-1] for x in g]})')
"

echo -n "Dataplex retail-* data products (us): "
curl -s -H "Authorization: Bearer ${TOKEN}" \
  "https://dataplex.googleapis.com/v1/projects/${PROJECT_ID}/locations/us/dataProducts" | python3 -c "
import sys, json
dp = json.load(sys.stdin).get('dataProducts', [])
rdp = [x['name'].split('/')[-1] for x in dp if 'retail' in x['name']]
print(f'{len(rdp)} retail-* collisions (existing data products: {len(dp)})')
"

echo -n "Cloud Run retail-* services (us-central1): "
gcloud run services list --project="${PROJECT_ID}" --region="${REGION}" --filter="metadata.name~retail" --format="value(metadata.name)" | wc -l
