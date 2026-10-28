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
# Creates unenriched _nokc copies of all BigQuery datasets.
# Tables are copied via CREATE TABLE AS SELECT — no descriptions, no metadata.
#
# Must run AFTER deploy-bq.sh (needs source tables) and BEFORE post_deploy.sh
# (so Data Insights never touches _nokc datasets).
#
# Usage:
#   bash deploy-bq-nokc.sh              # First deploy
#   bash deploy-bq-nokc.sh --refresh    # Re-copy data (TRUNCATE + INSERT)
####################################################################################

set -e

# Disable gcloud mTLS client-cert helper (avoids Python 3.14 segfault in bq CLI)
export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false
export RETAIL_TAXONOMY_DISPLAY_NAME="${RETAIL_TAXONOMY_DISPLAY_NAME:-Retail Demo Sensitivity Taxonomy (alitch)}"

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT before running this script}"
LOCATION="us"

REFRESH_MODE=false
if [[ "${1:-}" == "--refresh" ]]; then
    REFRESH_MODE=true
    echo "=== Refresh mode: TRUNCATE + INSERT from enriched tables ==="
fi

# Source → _nokc dataset mapping
DATASETS=(
    retail_bronze
    retail_silver
    retail_gold
    retail_reference
    retail_dashboards
    retail_staging
    retail_snapshots
    retail_audit
)

echo "=== Creating _nokc datasets (8 shadow datasets with [Retail] descriptions & labels) ==="
for ds in "${DATASETS[@]}"; do
    desc="[Retail] Uncataloged shadow dataset (${ds}_nokc) for Scaled Agent comparison"
    bq --project_id="${PROJECT_ID}" mk --location="${LOCATION}" \
        --description="${desc}" \
        --label=use-case:retail --label=demo:retail-knowledge-catalog --label=owner:alitch --label=env:demo \
        --dataset "${PROJECT_ID}:${ds}_nokc" 2>/dev/null || \
    bq --project_id="${PROJECT_ID}" update \
        --description="${desc}" \
        --set_label=use-case:retail --set_label=demo:retail-knowledge-catalog --set_label=owner:alitch --set_label=env:demo \
        --dataset "${PROJECT_ID}:${ds}_nokc" >/dev/null 2>&1 || echo "  ${ds}_nokc already exists"
done

echo "=== Copying tables to _nokc datasets ==="
TOTAL=0
for ds in "${DATASETS[@]}"; do
    tables=$(bq ls --project_id="${PROJECT_ID}" --format=json "${ds}" 2>/dev/null | \
        python3 -c "import sys,json; [print(t['tableReference']['tableId']) for t in json.load(sys.stdin) if t.get('type') in ('TABLE','VIEW')]")
    for table in ${tables}; do
        TOTAL=$((TOTAL + 1))
        if ${REFRESH_MODE}; then
            echo "  ${ds}_nokc.${table} (refresh)..."
            bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 \
                "TRUNCATE TABLE \`${PROJECT_ID}.${ds}_nokc.${table}\`; INSERT INTO \`${PROJECT_ID}.${ds}_nokc.${table}\` SELECT * FROM \`${PROJECT_ID}.${ds}.${table}\`" 2>&1 | tail -1
        else
            echo "  ${ds}_nokc.${table}..."
            bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 \
                "CREATE OR REPLACE TABLE \`${PROJECT_ID}.${ds}_nokc.${table}\` AS SELECT * FROM \`${PROJECT_ID}.${ds}.${table}\`" 2>&1 | tail -1
        fi
    done
done

echo "=== _nokc Deploy Complete: ${TOTAL} tables copied ==="
