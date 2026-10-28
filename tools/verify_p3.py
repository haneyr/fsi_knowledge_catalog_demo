#!/usr/bin/env python3
"""Verify Phase P3 Data Layer deployment in alitch-ca-demo."""
import os
os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE", "false")
from google.cloud import bigquery

PROJECT_ID = "alitch-ca-demo"
REQUIRED_LABELS = {
    "use-case": "retail",
    "demo": "retail-knowledge-catalog",
    "owner": "alitch",
    "env": "demo",
}
GOVERNED_DATASETS = [
    "retail_bronze", "retail_silver", "retail_gold", "retail_reference",
    "retail_dashboards", "retail_staging", "retail_snapshots", "retail_audit",
    "retail_scan_results", "retail_agent_analytics",
]
NOKC_DATASETS = [
    "retail_bronze_nokc", "retail_silver_nokc", "retail_gold_nokc",
    "retail_reference_nokc", "retail_dashboards_nokc", "retail_staging_nokc",
    "retail_snapshots_nokc", "retail_audit_nokc",
]

client = bigquery.Client(project=PROJECT_ID)

print("=== 1. Dataset Labels & [Retail] Descriptions ===")
all_ds_ok = True
for ds_id in GOVERNED_DATASETS + NOKC_DATASETS:
    ds = client.get_dataset(f"{PROJECT_ID}.{ds_id}")
    desc = ds.description or ""
    labels = ds.labels or {}
    has_prefix = desc.startswith("[Retail] ")
    has_labels = all(labels.get(k) == v for k, v in REQUIRED_LABELS.items())
    status = "PASS" if (has_prefix and has_labels) else "FAIL"
    if status == "FAIL":
        all_ds_ok = False
    print(f"  [{status}] {ds_id}: labels={has_labels}, [Retail]_desc={has_prefix}")

print("\n=== 2. Table Counts & Non-Zero Row Counts (Governed Datasets) ===")
total_gov_tables = 0
empty_tables = []
for ds_id in GOVERNED_DATASETS[:8]:
    tables = list(client.list_tables(f"{PROJECT_ID}.{ds_id}"))
    total_gov_tables += len(tables)
    non_empty = 0
    for t_item in tables:
        if t_item.table_type == "VIEW":
            non_empty += 1
        else:
            t_obj = client.get_table(t_item.reference)
            if (t_obj.num_rows or 0) > 0:
                non_empty += 1
            else:
                empty_tables.append(f"{ds_id}.{t_item.table_id}")
    print(f"  {ds_id}: {len(tables)} tables/views ({non_empty}/{len(tables)} non-empty)")

print(f"Total governed tables/views: {total_gov_tables} (empty: {len(empty_tables)})")

print("\n=== 3. Table Counts (_nokc Shadow Datasets) ===")
total_nokc_tables = 0
for ds_id in NOKC_DATASETS:
    tables = list(client.list_tables(f"{PROJECT_ID}.{ds_id}"))
    total_nokc_tables += len(tables)
    print(f"  {ds_id}: {len(tables)} tables")
print(f"Total _nokc tables: {total_nokc_tables}")
