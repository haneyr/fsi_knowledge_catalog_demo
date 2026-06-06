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

# Grant baseline IAM to all agent identities in the project via principalSet.
# Individual dataset-level grants are applied after each agent deploys.
grant_agent_identity_permissions() {
    echo "=== Granting baseline IAM to agent identities ==="
    PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' 2>/dev/null) || true
    if [ -z "${PROJECT_NUMBER}" ]; then
        echo "  Skipping (cannot resolve project number)"
        return 0
    fi

    ORG_ID=$(gcloud projects describe "${PROJECT_ID}" --format='value(parent.id)' 2>/dev/null) || true
    if [ -z "${ORG_ID}" ]; then
        echo "  Skipping (cannot resolve org ID — agent identity requires an org)"
        return 0
    fi

    PRINCIPAL_SET="principalSet://agents.global.org-${ORG_ID}.system.id.goog/attribute.platformContainer/aiplatform/projects/${PROJECT_NUMBER}"

    for role in roles/serviceusage.serviceUsageConsumer roles/browser roles/aiplatform.expressUser roles/aiplatform.agentContextEditor roles/bigquery.jobUser; do
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="${PRINCIPAL_SET}" --role="${role}" --quiet 2>/dev/null || true
        echo "  Granted ${role} to all agents"
    done
    echo "Agent identity baseline permissions configured."
}

# Grant dataset-level BQ access to a specific agent identity.
# Usage: grant_dataset_access <agent_engine_id> <dataset1> <dataset2> ...
grant_dataset_access() {
    local AGENT_ID="$1"; shift
    local PROJECT_NUMBER
    PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' 2>/dev/null) || true
    local ORG_ID
    ORG_ID=$(gcloud projects describe "${PROJECT_ID}" --format='value(parent.id)' 2>/dev/null) || true

    if [ -z "${PROJECT_NUMBER}" ] || [ -z "${ORG_ID}" ] || [ -z "${AGENT_ID}" ]; then
        echo "  Skipping dataset grants (missing project number, org ID, or agent ID)"
        return 0
    fi

    local PRINCIPAL="principal://agents.global.org-${ORG_ID}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${AGENT_ID}"

    for ds in "$@"; do
        python3 -c "
from google.cloud import bigquery
client = bigquery.Client(project='${PROJECT_ID}')
dataset = client.get_dataset('${ds}')
entry = bigquery.AccessEntry('READER', 'iamMember', '${PRINCIPAL}')
entries = list(dataset.access_entries)
if entry not in entries:
    entries.append(entry)
    dataset.access_entries = entries
    client.update_dataset(dataset, ['access_entries'])
    print('  Granted READER on ${ds}')
else:
    print('  Already has access to ${ds}')
" 2>/dev/null || echo "  Warning: could not grant access on ${ds}"
    done

    # Grant WRITER on agent_analytics for BQ Agent Analytics plugin
    python3 -c "
from google.cloud import bigquery
client = bigquery.Client(project='${PROJECT_ID}')
dataset = client.get_dataset('agent_analytics')
entry = bigquery.AccessEntry('WRITER', 'iamMember', '${PRINCIPAL}')
entries = list(dataset.access_entries)
if entry not in entries:
    entries.append(entry)
    dataset.access_entries = entries
    client.update_dataset(dataset, ['access_entries'])
    print('  Granted WRITER on agent_analytics')
else:
    print('  Already has access to agent_analytics')
" 2>/dev/null || echo "  Warning: could not grant access on agent_analytics"
}

NOKC_DATASETS="fsi_bronze_nokc fsi_silver_nokc fsi_gold_nokc fsi_reference_nokc fsi_dashboards_nokc fsi_staging_nokc fsi_snapshots_nokc fsi_audit_nokc"
ENRICHED_DATASETS="fsi_bronze fsi_silver fsi_gold fsi_reference fsi_dashboards fsi_staging fsi_snapshots fsi_audit fsi_scan_results"

# Grant required IAM permissions to the Agent Engine service account
grant_agent_engine_permissions() {
    echo "=== Granting IAM permissions to Agent Engine service account ==="
    PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' 2>/dev/null) || true
    if [ -z "${PROJECT_NUMBER}" ]; then
        echo "  Skipping IAM grants (cannot resolve project number — may lack resourcemanager access in CI)"
        return 0
    fi
    SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

    for role in roles/bigquery.jobUser roles/bigquery.dataEditor roles/dataplex.viewer roles/dataplex.catalogEditor roles/datalineage.viewer; do
        if gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${SA}" \
            --role="${role}" --quiet 2>/dev/null | tail -1; then
            echo "  Granted ${role}"
        else
            echo "  Skipped ${role} (may lack IAM permissions in CI — grant manually or via bootstrap)"
        fi
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
    # All agents: opt out of Context-Aware Access mTLS binding so Agent
    # Identity tokens work with the sessions API (Preview limitation).
    for agent_dir in agent_basic agent_scaled agent_kc; do
        cat >> "${SCRIPT_DIR}/${agent_dir}/.env" << EOF
GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES=False
EOF
    done
    # KC agent needs additional env vars
    cat >> "${SCRIPT_DIR}/agent_kc/.env" << EOF
DATAPLEX_PROJECT=${PROJECT_ID}
EOF
    # Snowflake integration (optional)
    if [ -n "${SNOWFLAKE_ACCOUNT:-}" ]; then
        cat >> "${SCRIPT_DIR}/agent_kc/.env" << SFEOF
SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT}
SNOWFLAKE_AGENT_USER=${SNOWFLAKE_AGENT_USER:-}
SNOWFLAKE_AGENT_PASSWORD=${SNOWFLAKE_AGENT_PASSWORD:-}
SNOWFLAKE_WAREHOUSE=${SNOWFLAKE_WAREHOUSE:-NEXUS_WH}
SNOWFLAKE_DATABASE=${SNOWFLAKE_DATABASE:-NEXUS_MARKET_DATA}
SFEOF
        # Add snowflake-connector-python to KC agent requirements
        if ! grep -q snowflake-connector-python "${SCRIPT_DIR}/agent_kc/requirements.txt"; then
            echo "snowflake-connector-python>=3.0" >> "${SCRIPT_DIR}/agent_kc/requirements.txt"
        fi
        echo "  Added Snowflake config to KC agent"
    fi
    echo "Created .env files for all agents"
}

extract_agent_id() {
    grep -oP 'reasoningEngines/\K[0-9]+' | tail -1
}

# Read an existing agent ID from Secret Manager. Returns empty string if not found.
read_agent_id() {
    local secret_name="$1"
    gcloud secrets versions access latest --secret="${secret_name}" \
        --project="${PROJECT_ID}" 2>/dev/null || true
}

deploy_basic() {
    echo "=== Deploying FSI Basic Agent ==="
    local existing_id update_flag output
    existing_id=$(read_agent_id "basic-agent-id")
    update_flag=""
    if [ -n "${existing_id}" ]; then
        echo "  Updating existing agent: ${existing_id}"
        update_flag="--agent_engine_id=${existing_id}"
    fi
    output=$(adk deploy agent_engine \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --display_name="FSI Basic Agent" \
        ${update_flag} \
        "${SCRIPT_DIR}/agent_basic" 2>&1)
    echo "$output"
    BASIC_AGENT_ID=$(echo "$output" | extract_agent_id)
    export BASIC_AGENT_ID
    echo "Basic agent deployed: ${BASIC_AGENT_ID}"
    echo "  Granting _nokc dataset access..."
    grant_dataset_access "${BASIC_AGENT_ID}" ${NOKC_DATASETS}
}

deploy_scaled() {
    echo "=== Deploying FSI Scaled Agent ==="
    local existing_id update_flag output
    existing_id=$(read_agent_id "scaled-agent-id")
    update_flag=""
    if [ -n "${existing_id}" ]; then
        echo "  Updating existing agent: ${existing_id}"
        update_flag="--agent_engine_id=${existing_id}"
    fi
    output=$(adk deploy agent_engine \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --display_name="FSI Scaled Agent" \
        ${update_flag} \
        "${SCRIPT_DIR}/agent_scaled" 2>&1)
    echo "$output"
    SCALED_AGENT_ID=$(echo "$output" | extract_agent_id)
    export SCALED_AGENT_ID
    echo "Scaled agent deployed: ${SCALED_AGENT_ID}"
    echo "  Granting _nokc dataset access..."
    grant_dataset_access "${SCALED_AGENT_ID}" ${NOKC_DATASETS}
}

deploy_kc() {
    echo "=== Deploying FSI KC Agent ==="
    local existing_id update_flag output
    existing_id=$(read_agent_id "kc-agent-id")
    update_flag=""
    if [ -n "${existing_id}" ]; then
        echo "  Updating existing agent: ${existing_id}"
        update_flag="--agent_engine_id=${existing_id}"
    fi
    output=$(adk deploy agent_engine \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --display_name="FSI KC Agent" \
        ${update_flag} \
        "${SCRIPT_DIR}/agent_kc" 2>&1)
    echo "$output"
    KC_AGENT_ID=$(echo "$output" | extract_agent_id)
    export KC_AGENT_ID
    echo "KC agent deployed: ${KC_AGENT_ID}"
    echo "  Granting enriched dataset access..."
    grant_dataset_access "${KC_AGENT_ID}" ${ENRICHED_DATASETS}
    # KC agent needs Knowledge Catalog roles for search and lineage
    local PROJECT_NUMBER ORG_ID KC_PRINCIPAL
    PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' 2>/dev/null) || true
    ORG_ID=$(gcloud projects describe "${PROJECT_ID}" --format='value(parent.id)' 2>/dev/null) || true
    if [ -n "${PROJECT_NUMBER}" ] && [ -n "${ORG_ID}" ]; then
        KC_PRINCIPAL="principal://agents.global.org-${ORG_ID}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${KC_AGENT_ID}"
        for role in roles/dataplex.viewer roles/dataplex.catalogEditor roles/datalineage.viewer; do
            gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
                --member="${KC_PRINCIPAL}" --role="${role}" --quiet 2>/dev/null || true
            echo "  Granted ${role} to KC agent"
        done
    fi
}

# Generate .env files
create_env_files

# Deploy based on argument
case "${1:-all}" in
    basic)
        grant_agent_identity_permissions
        deploy_basic
        grant_agent_engine_permissions
        ;;
    scaled)
        grant_agent_identity_permissions
        deploy_scaled
        grant_agent_engine_permissions
        ;;
    kc)
        grant_agent_identity_permissions
        deploy_kc
        grant_agent_engine_permissions
        ;;
    all)
        grant_agent_identity_permissions
        deploy_basic
        grant_agent_engine_permissions
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

# --- Persist agent IDs to Secret Manager (CI mode) ---
if [ "${PERSIST_AGENT_IDS:-}" = "1" ]; then
    echo "=== Persisting agent IDs to Secret Manager ==="
    for pair in "basic-agent-id:${BASIC_AGENT_ID:-}" "scaled-agent-id:${SCALED_AGENT_ID:-}" "kc-agent-id:${KC_AGENT_ID:-}"; do
        secret="${pair%%:*}"
        value="${pair#*:}"
        if [ -n "${value}" ]; then
            printf '%s' "${value}" | gcloud secrets versions add "${secret}" \
                --project="${PROJECT_ID}" --data-file=- --quiet
            echo "  ${secret} = ${value}"
        fi
    done
fi
