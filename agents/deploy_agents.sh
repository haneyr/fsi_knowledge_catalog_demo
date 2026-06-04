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

# Create per-agent service accounts with dataset-scoped BQ access
create_agent_service_accounts() {
    echo "=== Creating per-agent service accounts ==="
    PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' 2>/dev/null) || true
    if [ -z "${PROJECT_NUMBER}" ]; then
        echo "  Skipping SA creation (cannot resolve project number)"
        return 0
    fi

    for sa in fsi-agent-nokc fsi-agent-kc; do
        if gcloud iam service-accounts describe "${sa}@${PROJECT_ID}.iam.gserviceaccount.com" \
            --project="${PROJECT_ID}" >/dev/null 2>&1; then
            echo "  ${sa} already exists"
        else
            gcloud iam service-accounts create "${sa}" \
                --display-name="Agent SA (${sa})" \
                --project="${PROJECT_ID}" 2>/dev/null
            echo "  Created ${sa}"
        fi
    done

    # Grant jobUser at project level (both SAs need to run queries)
    for sa in fsi-agent-nokc fsi-agent-kc; do
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${sa}@${PROJECT_ID}.iam.gserviceaccount.com" \
            --role="roles/bigquery.jobUser" --quiet 2>/dev/null || true
    done

    # Dataset-scoped dataViewer: nokc SA → _nokc datasets only
    for ds in fsi_bronze_nokc fsi_silver_nokc fsi_gold_nokc fsi_reference_nokc fsi_dashboards_nokc fsi_staging_nokc fsi_snapshots_nokc fsi_audit_nokc; do
        python3 -c "
from google.cloud import bigquery
client = bigquery.Client(project='${PROJECT_ID}')
dataset = client.get_dataset('${ds}')
entry = bigquery.AccessEntry('READER', 'userByEmail', 'fsi-agent-nokc@${PROJECT_ID}.iam.gserviceaccount.com')
entries = list(dataset.access_entries)
if entry not in entries:
    entries.append(entry)
    dataset.access_entries = entries
    client.update_dataset(dataset, ['access_entries'])
    print('  Granted dataViewer on ${ds} to fsi-agent-nokc')
else:
    print('  fsi-agent-nokc already has access to ${ds}')
" 2>/dev/null || echo "  Warning: could not grant access on ${ds}"
    done

    # Dataset-scoped dataViewer: kc SA → enriched datasets only
    for ds in fsi_bronze fsi_silver fsi_gold fsi_reference fsi_dashboards fsi_staging fsi_snapshots fsi_audit fsi_scan_results; do
        python3 -c "
from google.cloud import bigquery
client = bigquery.Client(project='${PROJECT_ID}')
dataset = client.get_dataset('${ds}')
entry = bigquery.AccessEntry('READER', 'userByEmail', 'fsi-agent-kc@${PROJECT_ID}.iam.gserviceaccount.com')
entries = list(dataset.access_entries)
if entry not in entries:
    entries.append(entry)
    dataset.access_entries = entries
    client.update_dataset(dataset, ['access_entries'])
    print('  Granted dataViewer on ${ds} to fsi-agent-kc')
else:
    print('  fsi-agent-kc already has access to ${ds}')
" 2>/dev/null || echo "  Warning: could not grant access on ${ds}"
    done

    # Agent Engine SA needs serviceAccountUser on both agent SAs
    AGENT_ENGINE_SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
    for sa in fsi-agent-nokc fsi-agent-kc; do
        gcloud iam service-accounts add-iam-policy-binding \
            "${sa}@${PROJECT_ID}.iam.gserviceaccount.com" \
            --member="serviceAccount:${AGENT_ENGINE_SA}" \
            --role="roles/iam.serviceAccountUser" \
            --project="${PROJECT_ID}" --quiet 2>/dev/null || true
        echo "  Agent Engine SA can act as ${sa}"
    done

    echo "Agent service accounts configured."
}

# Grant required IAM permissions to the Agent Engine service account
grant_agent_engine_permissions() {
    echo "=== Granting IAM permissions to Agent Engine service account ==="
    PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' 2>/dev/null) || true
    if [ -z "${PROJECT_NUMBER}" ]; then
        echo "  Skipping IAM grants (cannot resolve project number — may lack resourcemanager access in CI)"
        return 0
    fi
    SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

    for role in roles/bigquery.jobUser roles/bigquery.dataViewer roles/bigquery.dataEditor roles/dataplex.viewer roles/dataplex.catalogEditor roles/datalineage.viewer; do
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

    # Generate .agent_engine_config.json with per-agent SA
    for agent_dir in agent_basic agent_scaled; do
        cat > "${SCRIPT_DIR}/${agent_dir}/.agent_engine_config.json" << EOF
{
    "service_account": "fsi-agent-nokc@${PROJECT_ID}.iam.gserviceaccount.com"
}
EOF
    done
    cat > "${SCRIPT_DIR}/agent_kc/.agent_engine_config.json" << EOF
{
    "service_account": "fsi-agent-kc@${PROJECT_ID}.iam.gserviceaccount.com"
}
EOF
}

extract_agent_id() {
    grep -oP 'reasoningEngines/\K[0-9]+' | tail -1
}

deploy_basic() {
    echo "=== Deploying FSI Basic Agent ==="
    local output
    output=$(adk deploy agent_engine \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --display_name="FSI Basic Agent" \
        "${SCRIPT_DIR}/agent_basic" 2>&1)
    echo "$output"
    BASIC_AGENT_ID=$(echo "$output" | extract_agent_id)
    export BASIC_AGENT_ID
    echo "Basic agent deployed: ${BASIC_AGENT_ID}"
}

deploy_scaled() {
    echo "=== Deploying FSI Scaled Agent ==="
    local output
    output=$(adk deploy agent_engine \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --display_name="FSI Scaled Agent" \
        "${SCRIPT_DIR}/agent_scaled" 2>&1)
    echo "$output"
    SCALED_AGENT_ID=$(echo "$output" | extract_agent_id)
    export SCALED_AGENT_ID
    echo "Scaled agent deployed: ${SCALED_AGENT_ID}"
}

deploy_kc() {
    echo "=== Deploying FSI KC Agent ==="
    local output
    output=$(adk deploy agent_engine \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --display_name="FSI KC Agent" \
        "${SCRIPT_DIR}/agent_kc" 2>&1)
    echo "$output"
    KC_AGENT_ID=$(echo "$output" | extract_agent_id)
    export KC_AGENT_ID
    echo "KC agent deployed: ${KC_AGENT_ID}"
}

# Generate .env files
create_env_files

# Deploy based on argument
case "${1:-all}" in
    basic)
        deploy_basic
        grant_agent_engine_permissions
        ;;
    scaled)
        deploy_scaled
        grant_agent_engine_permissions
        ;;
    kc)
        deploy_kc
        grant_agent_engine_permissions
        ;;
    all)
        create_agent_service_accounts
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
    for pair in "basic-agent-id:${BASIC_AGENT_ID}" "scaled-agent-id:${SCALED_AGENT_ID}" "kc-agent-id:${KC_AGENT_ID}"; do
        secret="${pair%%:*}"
        value="${pair#*:}"
        if [ -n "${value}" ]; then
            printf '%s' "${value}" | gcloud secrets versions add "${secret}" \
                --project="${PROJECT_ID}" --data-file=- --quiet
            echo "  ${secret} = ${value}"
        fi
    done
fi
