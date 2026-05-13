#!/usr/bin/env python3
"""
Runs data profile and insights scans on ALL tables, then applies the
generated insights descriptions to BigQuery table and column descriptions.

Usage: python3 11_run_scans_and_apply_insights.py
"""

import logging
import time
import json

from common import load_config, api_call, DATAPLEX_URL, ALL_TABLES

logger = logging.getLogger(__name__)

EVERY_TABLE = ALL_TABLES


def scan_id(dataset, table, scan_type):
    layer = dataset.replace("fsi_", "")
    tname = table.replace(f"{layer}_", "").replace("bronze_", "").replace("silver_", "").replace("gold_", "")
    return f"fsi-{layer}-{tname}-{scan_type}".replace("_", "-")


def bq_resource(cfg, dataset, table):
    return f"//bigquery.googleapis.com/projects/{cfg['project_id']}/datasets/{dataset}/tables/{table}"


def ensure_scan(cfg, dataset, table, stype, spec_body):
    pid = cfg["project_id"]
    loc = cfg["location"]
    sid = scan_id(dataset, table, stype)
    url = f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans/{sid}"

    try:
        api_call(url, "GET")
        return sid
    except RuntimeError as e:
        if "404" not in str(e):
            raise

    create_url = f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans?dataScanId={sid}"
    body = {
        **spec_body,
        "data": {"resource": bq_resource(cfg, dataset, table)},
        "displayName": f"{stype.title()}: {dataset}.{table}",
        "description": f"Data {stype} scan for {dataset}.{table}",
    }
    api_call(create_url, "POST", body)
    logger.info("  Created %s", sid)
    time.sleep(2)
    return sid


def run_scan(cfg, sid):
    pid = cfg["project_id"]
    loc = cfg["location"]
    run_url = f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans/{sid}:run"
    try:
        api_call(run_url, "POST", {})
        return True
    except RuntimeError as e:
        if "409" in str(e) or "ALREADY" in str(e).upper():
            return True
        logger.warning("  Failed to run %s: %s", sid, str(e)[:80])
        return False


def get_scan_result(cfg, sid):
    pid = cfg["project_id"]
    loc = cfg["location"]
    url = f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans/{sid}:getLatestScanResult"
    try:
        return api_call(url, "GET")
    except RuntimeError:
        return None


def wait_for_scans(cfg, scan_ids, timeout=1800):
    """Poll until all scans complete or timeout."""
    pid = cfg["project_id"]
    loc = cfg["location"]
    pending = set(scan_ids)
    start = time.time()

    while pending and (time.time() - start) < timeout:
        still_pending = set()
        for sid in pending:
            url = f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans/{sid}"
            try:
                result = api_call(url, "GET")
                state = result.get("executionStatus", {}).get("latestJobState", "UNKNOWN")
                if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                    continue
                still_pending.add(sid)
            except RuntimeError:
                still_pending.add(sid)

        pending = still_pending
        if pending:
            logger.info("  %d scans still running, waiting 30s...", len(pending))
            time.sleep(30)

    if pending:
        logger.warning("  %d scans still pending after timeout", len(pending))
    return pending


def apply_insights_to_bq(cfg):
    """Extract insights scan descriptions and apply them to BQ tables."""
    from google.cloud import bigquery
    bq_client = bigquery.Client(project=cfg["project_id"])
    pid = cfg["project_id"]

    updated_tables = 0
    updated_columns = 0

    for dataset, table in EVERY_TABLE:
        sid = scan_id(dataset, table, "insights")
        result = get_scan_result(cfg, sid)
        if not result:
            continue

        doc_result = result.get("dataDocumentationResult", {})
        if not doc_result:
            continue

        table_ref = f"{pid}.{dataset}.{table}"
        bq_table = bq_client.get_table(table_ref)
        changed = False

        table_doc = doc_result.get("descriptions", {}).get("description", "")
        if table_doc and (not bq_table.description or len(bq_table.description) < len(table_doc)):
            bq_table.description = table_doc
            changed = True
            updated_tables += 1

        column_docs = {}
        for col_desc in doc_result.get("columns", []):
            col_name = col_desc.get("columnName", "")
            col_doc = col_desc.get("description", "")
            if col_name and col_doc:
                column_docs[col_name] = col_doc

        if column_docs:
            new_schema = []
            for field in bq_table.schema:
                if field.name in column_docs and (not field.description or len(field.description) < len(column_docs[field.name])):
                    new_field = field.to_api_repr()
                    new_field["description"] = column_docs[field.name]
                    new_schema.append(bigquery.SchemaField.from_api_repr(new_field))
                    updated_columns += 1
                else:
                    new_schema.append(field)
            bq_table.schema = new_schema
            changed = True

        if changed:
            try:
                bq_client.update_table(bq_table, ["description", "schema"])
                logger.info("  %s: updated (table desc + %d cols)", table, len(column_docs))
            except Exception as e:
                logger.warning("  %s: failed to update - %s", table, str(e)[:100])

    return updated_tables, updated_columns


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    loc = cfg["location"]
    logger.info("Project: %s | Tables: %d", pid, len(EVERY_TABLE))

    # Phase 1: Ensure profile scans exist for all tables
    logger.info("=== Phase 1: Creating/verifying profile scans ===")
    profile_sids = []
    for dataset, table in EVERY_TABLE:
        sid = ensure_scan(cfg, dataset, table, "profile", {
            "dataProfileSpec": {"samplingPercent": 25},
        })
        profile_sids.append(sid)
        time.sleep(0.3)
    logger.info("  %d profile scans ready", len(profile_sids))

    # Phase 2: Ensure insights scans exist for all tables
    logger.info("=== Phase 2: Creating/verifying insights scans ===")
    insights_sids = []
    for dataset, table in EVERY_TABLE:
        sid = ensure_scan(cfg, dataset, table, "insights", {
            "type": "DATA_DOCUMENTATION",
            "dataDocumentationSpec": {},
        })
        insights_sids.append(sid)
        time.sleep(0.3)
    logger.info("  %d insights scans ready", len(insights_sids))

    # Phase 3: Run all profile scans
    logger.info("=== Phase 3: Running profile scans ===")
    profile_running = 0
    for sid in profile_sids:
        if run_scan(cfg, sid):
            profile_running += 1
        time.sleep(0.5)
    logger.info("  %d profile scans started", profile_running)

    # Phase 4: Run all insights scans
    logger.info("=== Phase 4: Running insights scans ===")
    insights_running = 0
    for sid in insights_sids:
        if run_scan(cfg, sid):
            insights_running += 1
        time.sleep(0.5)
    logger.info("  %d insights scans started", insights_running)

    # Phase 5: Wait for insights scans to complete
    logger.info("=== Phase 5: Waiting for insights scans to complete (up to 30 min) ===")
    still_pending = wait_for_scans(cfg, insights_sids, timeout=1800)
    completed = len(insights_sids) - len(still_pending)
    logger.info("  %d/%d insights scans completed", completed, len(insights_sids))

    # Phase 6: Apply insights descriptions to BigQuery
    logger.info("=== Phase 6: Applying insights to BigQuery table/column descriptions ===")
    updated_tables, updated_columns = apply_insights_to_bq(cfg)
    logger.info("  Updated %d table descriptions, %d column descriptions", updated_tables, updated_columns)

    logger.info("=" * 60)
    logger.info("SCAN AND INSIGHTS COMPLETE")
    logger.info("  Profile scans: %d", len(profile_sids))
    logger.info("  Insights scans: %d", len(insights_sids))
    logger.info("  BQ tables updated: %d", updated_tables)
    logger.info("  BQ columns updated: %d", updated_columns)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
