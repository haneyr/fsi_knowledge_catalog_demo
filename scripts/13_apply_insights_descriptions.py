#!/usr/bin/env python3
"""
Extracts Data Insights scan results and applies the AI-generated descriptions
to BigQuery table descriptions and column descriptions.

Usage: python3 13_apply_insights_descriptions.py
"""

import logging
import time
import json

import requests as http_requests
import google.auth
import google.auth.transport.requests
from google.cloud import bigquery

from common import load_config, DATAPLEX_URL, ALL_TABLES

logger = logging.getLogger(__name__)


def _get_token():
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def scan_id(dataset, table):
    layer = dataset.replace("fsi_", "")
    tname = table.replace(f"{layer}_", "").replace("bronze_", "").replace("silver_", "").replace("gold_", "")
    return f"fsi-{layer}-{tname}-insights".replace("_", "-")


def get_latest_job(token, pid, loc, sid):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans/{sid}/jobs?pageSize=1"
    resp = http_requests.get(url, headers=headers)
    if resp.status_code != 200:
        return None
    jobs = resp.json().get("dataScanJobs", [])
    if not jobs:
        return None
    job = jobs[0]
    if job.get("state") != "SUCCEEDED":
        return None
    return job["name"]


def get_job_results(token, job_name):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{DATAPLEX_URL}/{job_name}?view=FULL"
    resp = http_requests.get(url, headers=headers)
    if resp.status_code != 200:
        return None, {}
    data = resp.json()
    doc = data.get("dataDocumentationResult", {})
    table_result = doc.get("tableResult", {})
    overview = table_result.get("overview", "")
    schema = table_result.get("schema", {})
    column_descs = {}
    for field in schema.get("fields", []):
        name = field.get("name", "")
        desc = field.get("description", "")
        if name and desc:
            column_descs[name] = desc
    return overview, column_descs


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    loc = cfg["location"]
    token = _get_token()

    bq_client = bigquery.Client(project=pid)

    updated_tables = 0
    updated_columns = 0
    skipped = 0

    logger.info("Applying Data Insights descriptions to %d tables...", len(ALL_TABLES))

    for dataset, table in ALL_TABLES:
        sid = scan_id(dataset, table)

        job_name = get_latest_job(token, pid, loc, sid)
        if not job_name:
            skipped += 1
            continue

        overview, column_descs = get_job_results(token, job_name)
        if not overview and not column_descs:
            skipped += 1
            continue

        table_ref = f"{pid}.{dataset}.{table}"
        try:
            bq_table = bq_client.get_table(table_ref)
        except Exception:
            logger.warning("  %s: table not found in BQ", table_ref)
            skipped += 1
            continue

        changed = False

        if overview:
            bq_table.description = overview
            changed = True
            updated_tables += 1

        if column_descs:
            new_schema = []
            cols_updated = 0
            for field in bq_table.schema:
                if field.name in column_descs:
                    new_field = field.to_api_repr()
                    new_field["description"] = column_descs[field.name]
                    new_schema.append(bigquery.SchemaField.from_api_repr(new_field))
                    cols_updated += 1
                else:
                    new_schema.append(field)
            if cols_updated > 0:
                bq_table.schema = new_schema
                updated_columns += cols_updated
                changed = True

        if changed:
            try:
                bq_client.update_table(bq_table, ["description", "schema"])
                logger.info("  %s: table desc + %d column descs", table, len(column_descs))
            except Exception as e:
                logger.warning("  %s: update failed - %s", table, str(e)[:100])

        time.sleep(0.2)

        if (updated_tables + skipped) % 20 == 0 and updated_tables > 0:
            token = _get_token()

    logger.info("=" * 60)
    logger.info("INSIGHTS APPLICATION COMPLETE")
    logger.info("  Tables with descriptions: %d", updated_tables)
    logger.info("  Column descriptions added: %d", updated_columns)
    logger.info("  Skipped (no results): %d", skipped)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
