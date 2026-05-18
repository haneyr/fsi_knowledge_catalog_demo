#!/bin/bash
# Deploys all BigQuery datasets and tables using the bq CLI.
# Use this when Terraform is not available.
#
# Usage:
#   bash deploy-bq.sh              # First deploy (CREATE OR REPLACE)
#   bash deploy-bq.sh --refresh    # Refresh data only (TRUNCATE + INSERT, preserves metadata)

set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT before running this script}"
LOCATION="us"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REFRESH_MODE=false

if [[ "${1:-}" == "--refresh" ]]; then
    REFRESH_MODE=true
    echo "=== Refresh mode: TRUNCATE + INSERT (preserves metadata) ==="
fi

run_sql_file() {
    local sql_file="$1"
    local table
    table=$(basename "${sql_file}" .sql)
    local sql
    sql=$(sed "s/\${project_id}/${PROJECT_ID}/g" "${sql_file}")

    if ${REFRESH_MODE}; then
        # Transform CREATE OR REPLACE TABLE ... AS SELECT into TRUNCATE + INSERT
        # Views are left as-is (CREATE OR REPLACE VIEW is safe)
        if echo "$sql" | head -1 | grep -q 'CREATE OR REPLACE TABLE'; then
            local table_fqn
            table_fqn=$(echo "$sql" | head -1 | grep -oP '`[^`]+`')
            local select_part
            select_part=$(echo "$sql" | sed '1s/CREATE OR REPLACE TABLE[^A]*AS//')
            sql="DELETE FROM ${table_fqn} WHERE TRUE;
INSERT INTO ${table_fqn}
${select_part}"
        fi
    fi

    echo "  ${table}..."
    echo "$sql" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 2>&1 | tail -1
}

if ! ${REFRESH_MODE}; then
    echo "=== Creating BigQuery Datasets ==="
    for ds in fsi_bronze fsi_silver fsi_gold fsi_scan_results fsi_staging fsi_snapshots fsi_audit fsi_reference fsi_dashboards; do
        bq --project_id="${PROJECT_ID}" mk --location="${LOCATION}" --dataset "${PROJECT_ID}:${ds}" 2>/dev/null || echo "  ${ds} already exists"
    done
fi

echo "=== Bronze Tables (40) ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/bronze_"*.sql; do
    run_sql_file "${sql_file}"
done

echo "=== Silver Tables (40) ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/silver_"*.sql; do
    run_sql_file "${sql_file}"
done

echo "=== Gold Tables (20) ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/gold_"*.sql; do
    run_sql_file "${sql_file}"
done

echo "=== Staging Tables ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/staging_"*.sql; do
    run_sql_file "${sql_file}"
done

echo "=== Snapshot Tables ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/snapshot_"*.sql; do
    run_sql_file "${sql_file}"
done

echo "=== Audit Tables ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/audit_"*.sql; do
    run_sql_file "${sql_file}"
done

echo "=== Reference Tables ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-reference/sql/"*.sql; do
    run_sql_file "${sql_file}"
done

echo "=== Dashboard Views ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-dashboards/sql/"*.sql; do
    run_sql_file "${sql_file}"
done

echo "=== BigQuery Deploy Complete ==="
echo "Total: $(find "${SCRIPT_DIR}/modules" -name '*.sql' | wc -l) SQL files executed"
if ${REFRESH_MODE}; then
    echo "Mode: REFRESH (metadata preserved)"
fi
