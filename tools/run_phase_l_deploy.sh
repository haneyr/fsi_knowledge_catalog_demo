#!/bin/bash
set -e

export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-alitch-ca-demo}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"

echo "=== Step 1: In-place BigQuery column renames (preserves table metadata, descriptions & Dataplex entries) ==="
ALTER_SQL="
ALTER TABLE \`${PROJECT_ID}.retail_bronze.bronze_merch_assortments\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_bronze.bronze_merch_assortments\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_bronze_nokc.bronze_merch_assortments\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_bronze_nokc.bronze_merch_assortments\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;

ALTER TABLE \`${PROJECT_ID}.retail_silver.silver_merch_assortments\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_silver.silver_merch_assortments\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_silver.silver_merch_assortments\` RENAME COLUMN IF EXISTS total_return_pct TO sell_through_pct;
ALTER TABLE \`${PROJECT_ID}.retail_silver_nokc.silver_merch_assortments\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_silver_nokc.silver_merch_assortments\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_silver_nokc.silver_merch_assortments\` RENAME COLUMN IF EXISTS total_return_pct TO sell_through_pct;

ALTER TABLE \`${PROJECT_ID}.retail_bronze.bronze_assortment_performance\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_bronze_nokc.bronze_assortment_performance\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;

ALTER TABLE \`${PROJECT_ID}.retail_silver.silver_assortment_performance\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_silver_nokc.silver_assortment_performance\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;

ALTER TABLE \`${PROJECT_ID}.retail_gold.gold_assortment_performance\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_gold.gold_assortment_performance\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_gold.gold_assortment_performance\` RENAME COLUMN IF EXISTS total_return_pct TO sell_through_pct;
ALTER TABLE \`${PROJECT_ID}.retail_gold.gold_assortment_performance\` RENAME COLUMN IF EXISTS avg_sharpe_ratio TO gmroi;
ALTER TABLE \`${PROJECT_ID}.retail_gold_nokc.gold_assortment_performance\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_gold_nokc.gold_assortment_performance\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_gold_nokc.gold_assortment_performance\` RENAME COLUMN IF EXISTS total_return_pct TO sell_through_pct;
ALTER TABLE \`${PROJECT_ID}.retail_gold_nokc.gold_assortment_performance\` RENAME COLUMN IF EXISTS avg_sharpe_ratio TO gmroi;

ALTER TABLE \`${PROJECT_ID}.retail_gold.gold_category_manager_scorecard\` RENAME COLUMN IF EXISTS avg_sharpe_ratio TO gmroi;
ALTER TABLE \`${PROJECT_ID}.retail_gold_nokc.gold_category_manager_scorecard\` RENAME COLUMN IF EXISTS avg_sharpe_ratio TO gmroi;

ALTER TABLE \`${PROJECT_ID}.retail_bronze.bronze_inventory_positions\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_bronze.bronze_inventory_positions\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_bronze.bronze_inventory_positions\` RENAME COLUMN IF EXISTS unrealized_gain_loss TO markdown_exposure;
ALTER TABLE \`${PROJECT_ID}.retail_bronze_nokc.bronze_inventory_positions\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_bronze_nokc.bronze_inventory_positions\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_bronze_nokc.bronze_inventory_positions\` RENAME COLUMN IF EXISTS unrealized_gain_loss TO markdown_exposure;

ALTER TABLE \`${PROJECT_ID}.retail_silver.silver_inventory_positions\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_silver.silver_inventory_positions\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_silver.silver_inventory_positions\` RENAME COLUMN IF EXISTS unrealized_gain_loss TO markdown_exposure;
ALTER TABLE \`${PROJECT_ID}.retail_silver_nokc.silver_inventory_positions\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_silver_nokc.silver_inventory_positions\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_silver_nokc.silver_inventory_positions\` RENAME COLUMN IF EXISTS unrealized_gain_loss TO markdown_exposure;

ALTER TABLE \`${PROJECT_ID}.retail_bronze.bronze_carrier_feeds\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_bronze_nokc.bronze_carrier_feeds\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;

ALTER TABLE \`${PROJECT_ID}.retail_silver.silver_carrier_feeds\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_silver_nokc.silver_carrier_feeds\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;

ALTER TABLE \`${PROJECT_ID}.retail_snapshots.snapshot_quarterly_inventory_positions\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_snapshots.snapshot_quarterly_inventory_positions\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
ALTER TABLE \`${PROJECT_ID}.retail_snapshots_nokc.snapshot_quarterly_inventory_positions\` RENAME COLUMN IF EXISTS market_value TO current_retail_value;
ALTER TABLE \`${PROJECT_ID}.retail_snapshots_nokc.snapshot_quarterly_inventory_positions\` RENAME COLUMN IF EXISTS cost_basis TO inventory_at_cost;
"

echo "$ALTER_SQL" | bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --max_rows=0

echo "=== Step 2: Run deploy-bq.sh --refresh ==="
bash deploy-bq.sh --refresh

echo "=== Step 3: Run deploy-bq-nokc.sh --refresh ==="
bash deploy-bq-nokc.sh --refresh

echo "=== Step 4: Re-inject intentional DQ defects and trigger DQ rescans ==="
python3 scripts/15_inject_dirty_data.py

echo "=== Step 5: Also copy dirty bronze data to _nokc bronze tables & trigger DQ rescans on assortment/inventory tables ==="
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
from common import load_config, run_bq_query
from importlib import import_module
dirty_mod = import_module("15_inject_dirty_data")

cfg = load_config()
pid = cfg["project_id"]

# Sync dirty bronze tables to _nokc so both match
for inj in dirty_mod.INJECTIONS:
    ds, tbl = inj["table"].split(".")
    nokc_ds = f"{ds}_nokc"
    sql = f"DELETE FROM `{pid}.{nokc_ds}.{tbl}` WHERE TRUE; INSERT INTO `{pid}.{nokc_ds}.{tbl}` SELECT * FROM `{pid}.{ds}.{tbl}`;"
    run_bq_query(cfg, sql, f"sync {nokc_ds}.{tbl}")

# Trigger DQ rescans on assortment & inventory tables
extra_tables = [
    ("retail_bronze", "bronze_merch_assortments"),
    ("retail_silver", "silver_merch_assortments"),
    ("retail_bronze", "bronze_assortment_performance"),
    ("retail_silver", "silver_assortment_performance"),
    ("retail_gold", "gold_assortment_performance"),
    ("retail_gold", "gold_category_manager_scorecard"),
    ("retail_bronze", "bronze_inventory_positions"),
    ("retail_silver", "silver_inventory_positions"),
    ("retail_gold", "gold_inventory_allocation"),
    ("retail_gold", "gold_markdown_risk_var"),
]
dirty_mod.rerun_dq_scans(cfg, extra_tables)
print("PHASE_L_DEPLOY_COMPLETE")
PY
