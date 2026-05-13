#!/bin/bash
# Deploys all BigQuery datasets and tables using the bq CLI.
# Use this when Terraform is not available.

set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT before running this script}"
LOCATION="us"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Creating BigQuery Datasets ==="
for ds in fsi_bronze fsi_silver fsi_gold fsi_scan_results fsi_staging fsi_snapshots fsi_audit fsi_reference fsi_dashboards; do
  bq --project_id="${PROJECT_ID}" mk --location="${LOCATION}" --dataset "${PROJECT_ID}:${ds}" 2>/dev/null || echo "  ${ds} already exists"
done

echo "=== Creating Bronze Tables (40) ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/bronze_"*.sql; do
  table=$(basename "${sql_file}" .sql)
  echo "  ${table}..."
  sed "s/\${project_id}/${PROJECT_ID}/g" "${sql_file}" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 2>&1 | tail -1
done

echo "=== Creating Silver Tables (40) ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/silver_"*.sql; do
  table=$(basename "${sql_file}" .sql)
  echo "  ${table}..."
  sed "s/\${project_id}/${PROJECT_ID}/g" "${sql_file}" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 2>&1 | tail -1
done

echo "=== Creating Gold Tables (20) ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/gold_"*.sql; do
  table=$(basename "${sql_file}" .sql)
  echo "  ${table}..."
  sed "s/\${project_id}/${PROJECT_ID}/g" "${sql_file}" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 2>&1 | tail -1
done

echo "=== Creating Staging Tables ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/staging_"*.sql; do
  table=$(basename "${sql_file}" .sql)
  echo "  ${table}..."
  sed "s/\${project_id}/${PROJECT_ID}/g" "${sql_file}" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 2>&1 | tail -1
done

echo "=== Creating Snapshot Tables ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/snapshot_"*.sql; do
  table=$(basename "${sql_file}" .sql)
  echo "  ${table}..."
  sed "s/\${project_id}/${PROJECT_ID}/g" "${sql_file}" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 2>&1 | tail -1
done

echo "=== Creating Audit Tables ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-medallion/sql/audit_"*.sql; do
  table=$(basename "${sql_file}" .sql)
  echo "  ${table}..."
  sed "s/\${project_id}/${PROJECT_ID}/g" "${sql_file}" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 2>&1 | tail -1
done

echo "=== Creating Reference Tables ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-reference/sql/"*.sql; do
  table=$(basename "${sql_file}" .sql)
  echo "  ${table}..."
  sed "s/\${project_id}/${PROJECT_ID}/g" "${sql_file}" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 2>&1 | tail -1
done

echo "=== Creating Dashboard Views ==="
for sql_file in "${SCRIPT_DIR}/modules/bigquery-dashboards/sql/"*.sql; do
  table=$(basename "${sql_file}" .sql)
  echo "  ${table}..."
  sed "s/\${project_id}/${PROJECT_ID}/g" "${sql_file}" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0 2>&1 | tail -1
done

echo "=== BigQuery Deploy Complete ==="
echo "Total: $(find "${SCRIPT_DIR}/modules" -name '*.sql' | wc -l) SQL files executed"
