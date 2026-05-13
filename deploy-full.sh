#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

####################################################################################
# FSI Knowledge Catalog Demo — Full End-to-End Deployment
#
# This script orchestrates the complete deployment:
#   1. Creates a new GCP project (or uses existing)
#   2. Enables APIs and links billing
#   3. Creates BigQuery datasets and 128+ tables with synthetic data
#   4. Creates all Knowledge Catalog resources (glossary, scans, aspects, etc.)
#   5. Deploys 3 agents to Vertex AI Agent Engine with BQ analytics
#
# Prerequisites:
#   - gcloud CLI authenticated (gcloud auth login)
#   - Application Default Credentials (gcloud auth application-default login)
#   - pip install google-adk google-cloud-aiplatform google-cloud-bigquery google-auth requests
#
# Usage:
#   # New project:
#   export ORG_ID=your-org-id
#   export BILLING_ACCOUNT=your-billing-account-id
#   bash deploy-full.sh
#
#   # Existing project:
#   export GOOGLE_CLOUD_PROJECT=your-existing-project-id
#   bash deploy-full.sh
####################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Step 0: Project setup
# ---------------------------------------------------------------------------
if [ -z "${GOOGLE_CLOUD_PROJECT}" ]; then
    SUFFIX=$(python3 -c "import random, string; print(''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))")
    export GOOGLE_CLOUD_PROJECT="fsi-kc-demo-${SUFFIX}"
    echo "=== Creating new project: ${GOOGLE_CLOUD_PROJECT} ==="

    if [ -z "${ORG_ID}" ] || [ -z "${BILLING_ACCOUNT}" ]; then
        echo "ERROR: Set ORG_ID and BILLING_ACCOUNT for new project creation"
        echo "  export ORG_ID=your-org-id"
        echo "  export BILLING_ACCOUNT=your-billing-account-id"
        exit 1
    fi

    gcloud projects create "${GOOGLE_CLOUD_PROJECT}" \
        --name="FSI Knowledge Catalog Demo" \
        --organization="${ORG_ID}"
    gcloud billing projects link "${GOOGLE_CLOUD_PROJECT}" \
        --billing-account="${BILLING_ACCOUNT}"
else
    echo "=== Using existing project: ${GOOGLE_CLOUD_PROJECT} ==="
fi

export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
PROJECT_NUMBER=$(gcloud projects describe "${GOOGLE_CLOUD_PROJECT}" --format='value(projectNumber)')

# ---------------------------------------------------------------------------
# Step 1: Enable APIs
# ---------------------------------------------------------------------------
echo "=== Enabling APIs ==="
gcloud services enable \
    bigquery.googleapis.com \
    dataplex.googleapis.com \
    datalineage.googleapis.com \
    aiplatform.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    cloudaicompanion.googleapis.com \
    --project="${GOOGLE_CLOUD_PROJECT}"

gcloud config set project "${GOOGLE_CLOUD_PROJECT}"
gcloud auth application-default set-quota-project "${GOOGLE_CLOUD_PROJECT}" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Step 2: Generate scripts/config.json
# ---------------------------------------------------------------------------
echo "=== Generating config.json ==="
cat > "${SCRIPT_DIR}/scripts/config.json" << EOF
{
  "project_id": {"sensitive": false, "type": "string", "value": "${GOOGLE_CLOUD_PROJECT}"},
  "project_number": {"sensitive": false, "type": "string", "value": "${PROJECT_NUMBER}"},
  "region": {"sensitive": false, "type": "string", "value": "${GOOGLE_CLOUD_LOCATION}"},
  "multi_region": {"sensitive": false, "type": "string", "value": "us"},
  "gcp_account_name": {"sensitive": false, "type": "string", "value": "$(gcloud config get-value account 2>/dev/null)"}
}
EOF

# ---------------------------------------------------------------------------
# Step 3: Create BigQuery tables (128 SQL files)
# ---------------------------------------------------------------------------
echo "=== Deploying BigQuery tables ==="
bash "${SCRIPT_DIR}/deploy-bq.sh"

# ---------------------------------------------------------------------------
# Step 4: Create all Knowledge Catalog resources
# ---------------------------------------------------------------------------
echo "=== Running post-deploy scripts ==="
bash "${SCRIPT_DIR}/post_deploy.sh"

# ---------------------------------------------------------------------------
# Step 5: Create agent_analytics dataset
# ---------------------------------------------------------------------------
echo "=== Creating agent_analytics dataset ==="
bq --project_id="${GOOGLE_CLOUD_PROJECT}" mk --location=US \
    --dataset "${GOOGLE_CLOUD_PROJECT}:agent_analytics" 2>/dev/null || \
    echo "  agent_analytics dataset already exists"

# ---------------------------------------------------------------------------
# Step 6: Deploy agents to Agent Engine
# ---------------------------------------------------------------------------
echo "=== Deploying agents to Vertex AI Agent Engine ==="
bash "${SCRIPT_DIR}/agents/deploy_agents.sh"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "FSI KNOWLEDGE CATALOG DEMO — DEPLOYMENT COMPLETE"
echo "============================================================"
echo "  Project:    ${GOOGLE_CLOUD_PROJECT}"
echo "  Region:     ${GOOGLE_CLOUD_LOCATION}"
echo ""
echo "  BigQuery:   https://console.cloud.google.com/bigquery?project=${GOOGLE_CLOUD_PROJECT}"
echo "  Dataplex:   https://console.cloud.google.com/dataplex?project=${GOOGLE_CLOUD_PROJECT}"
echo "  Agents:     https://console.cloud.google.com/vertex-ai/agents?project=${GOOGLE_CLOUD_PROJECT}"
echo "  Analytics:  SELECT * FROM \`${GOOGLE_CLOUD_PROJECT}.agent_analytics.*\`"
echo "============================================================"
