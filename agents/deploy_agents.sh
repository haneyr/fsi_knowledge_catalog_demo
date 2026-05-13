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
# FSI Knowledge Catalog Demo — Deploy Agents to Vertex AI Agent Engine
#
# Prerequisites:
#   1. pip install google-adk google-cloud-aiplatform google-cloud-bigquery
#   2. gcloud auth login && gcloud auth application-default login
#   3. Set PROJECT_ID below or export GOOGLE_CLOUD_PROJECT
#
# Usage:
#   bash agents/deploy_agents.sh                    # Deploy all 3 agents
#   bash agents/deploy_agents.sh basic              # Deploy only basic agent
#   bash agents/deploy_agents.sh scaled             # Deploy only scaled agent
#   bash agents/deploy_agents.sh kc                 # Deploy only KC agent
####################################################################################

set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT before running this script}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Grant required IAM permissions to the Agent Engine service account
grant_agent_engine_permissions() {
    echo "=== Granting IAM permissions to Agent Engine service account ==="
    PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
    SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

    for role in roles/bigquery.jobUser roles/bigquery.dataViewer roles/bigquery.dataEditor roles/dataplex.viewer roles/dataplex.catalogEditor roles/datalineage.viewer; do
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${SA}" \
            --role="${role}" --quiet 2>/dev/null | tail -1
        echo "  Granted ${role}"
    done
    echo "Agent Engine SA permissions configured."
}

# Create .env files for each agent
create_env_files() {
    for agent_dir in agent_basic agent_scaled agent_kc; do
        cat > "${SCRIPT_DIR}/${agent_dir}/.env" << EOF
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
GOOGLE_CLOUD_LOCATION=${REGION}
GOOGLE_GENAI_USE_VERTEXAI=True
BQ_ANALYTICS_DATASET=agent_analytics
EOF
    done
    # KC agent needs additional env vars
    cat >> "${SCRIPT_DIR}/agent_kc/.env" << EOF
DATAPLEX_PROJECT=${PROJECT_ID}
EOF
    echo "Created .env files for all agents"
}

deploy_basic() {
    echo "=== Deploying FSI Basic Agent ==="
    adk deploy agent_engine \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --display_name="FSI Basic Agent" \
        "${SCRIPT_DIR}/agent_basic"
    echo "Basic agent deployed."
}

deploy_scaled() {
    echo "=== Deploying FSI Scaled Agent ==="
    adk deploy agent_engine \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --display_name="FSI Scaled Agent" \
        "${SCRIPT_DIR}/agent_scaled"
    echo "Scaled agent deployed."
}

deploy_kc() {
    echo "=== Deploying FSI KC Agent ==="
    adk deploy agent_engine \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --display_name="FSI KC Agent" \
        "${SCRIPT_DIR}/agent_kc"
    echo "KC agent deployed."
}

# Grant permissions and generate .env files
grant_agent_engine_permissions
create_env_files

# Deploy based on argument
case "${1:-all}" in
    basic)  deploy_basic ;;
    scaled) deploy_scaled ;;
    kc)     deploy_kc ;;
    all)
        deploy_basic
        deploy_scaled
        deploy_kc
        ;;
    *)
        echo "Usage: $0 [basic|scaled|kc|all]"
        exit 1
        ;;
esac

echo ""
echo "=== Deployment Complete ==="
echo "View your agents at:"
echo "  https://console.cloud.google.com/vertex-ai/agents?project=${PROJECT_ID}"
