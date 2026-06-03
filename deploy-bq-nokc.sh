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

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT before running this script}"
LOCATION="us"

REFRESH_MODE=false
if [[ "${1:-}" == "--refresh" ]]; then
    REFRESH_MODE=true
    echo "=== Refresh mode: TRUNCATE + INSERT from enriched tables ==="
fi

# Source → _nokc dataset mapping
DATASETS=(
    fsi_bronze
    fsi_silver
    fsi_gold
    fsi_reference
    fsi_dashboards
    fsi_staging
    fsi_snapshots
    fsi_audit
)

echo "=== Creating _nokc datasets ==="
for ds in "${DATASETS[@]}"; do
    bq --project_id="${PROJECT_ID}" mk --location="${LOCATION}" \
        --dataset "${PROJECT_ID}:${ds}_nokc" 2>/dev/null || echo "  ${ds}_nokc already exists"
done

echo "=== Copying tables to _nokc datasets ==="
TOTAL=0
for ds in "${DATASETS[@]}"; do
    tables=$(bq ls --project_id="${PROJECT_ID}" "${ds}" 2>/dev/null | awk 'NR>2 {print $1}' | grep -v '^$')
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
