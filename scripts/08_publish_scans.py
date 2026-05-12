#!/usr/bin/env python3
####################################################################################
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
"""
Sets published labels on BQ tables and saves Data Insights descriptions.

Usage: python3 08_publish_scans.py
"""

import logging
import time

from common import (
    load_config, api_call, get_access_token, run_bq_query,
    DATAPLEX_URL, BQ_URL, SCAN_TABLES, scan_id,
)
import requests as http_requests

logger = logging.getLogger(__name__)


def set_published_labels(cfg):
    pid = cfg["project_id"]
    loc = cfg.get("region", "us-central1")
    headers = {"Authorization": f"Bearer {get_access_token()}", "Content-Type": "application/json"}

    logger.info("Setting published labels on %d tables...", len(SCAN_TABLES))
    for dataset, table in SCAN_TABLES:
        profile_scan = scan_id(dataset, table, "profile")
        insights_scan = scan_id(dataset, table, "insights")
        quality_scan = scan_id(dataset, table, "quality")
        url = f"{BQ_URL}/projects/{pid}/datasets/{dataset}/tables/{table}"
        labels = {
            "dataplex-dp-published-project": pid,
            "dataplex-dp-published-location": loc,
            "dataplex-dp-published-scan": profile_scan,
            "dataplex-data-documentation-published-project": pid,
            "dataplex-data-documentation-published-location": loc,
            "dataplex-data-documentation-published-scan": insights_scan,
            "dataplex-dq-published-project": pid,
            "dataplex-dq-published-location": loc,
            "dataplex-dq-published-scan": quality_scan,
        }
        resp = http_requests.patch(url, json={"labels": labels}, headers=headers)
        if resp.status_code != 200:
            logger.warning("Labels failed for %s.%s: %s", dataset, table, resp.status_code)
        time.sleep(0.3)
    logger.info("Labels set")


def save_insights_descriptions(cfg):
    pid = cfg["project_id"]
    loc = cfg.get("region", "us-central1")

    logger.info("Saving Data Insights descriptions to tables...")
    saved = 0
    for dataset, table in SCAN_TABLES:
        sid = scan_id(dataset, table, "insights")
        try:
            resp = api_call(f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans/{sid}/jobs?pageSize=1", "GET")
            jobs = resp.get("dataScanJobs", [])
            if not jobs or jobs[0].get("state") != "SUCCEEDED":
                continue
            job_name = jobs[0]["name"]
            result_resp = api_call(f"{DATAPLEX_URL}/{job_name}?view=FULL", "GET")
            table_result = result_resp.get("dataDocumentationResult", {}).get("tableResult", {})
            overview = table_result.get("overview", "")
            fields = table_result.get("schema", {}).get("fields", [])
            if not fields:
                continue

            if overview:
                escaped = overview.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
                run_bq_query(cfg, f"ALTER TABLE `{pid}.{dataset}.{table}` SET OPTIONS (description = '{escaped}')")

            alter_parts = []
            for field in fields:
                col = field.get("name", "")
                desc = field.get("description", "")
                if col and desc:
                    escaped = desc.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
                    alter_parts.append(f"ALTER COLUMN `{col}` SET OPTIONS (description = '{escaped}')")
            if alter_parts:
                run_bq_query(cfg, f"ALTER TABLE `{pid}.{dataset}.{table}` " + ", ".join(alter_parts))
                saved += 1
        except RuntimeError as e:
            logger.warning("Failed insights for %s.%s: %s", dataset, table, str(e)[:80])
        time.sleep(0.5)
    logger.info("Saved descriptions for %d tables", saved)


def main():
    cfg = load_config()
    set_published_labels(cfg)
    save_insights_descriptions(cfg)
    logger.info("Publish complete")


if __name__ == "__main__":
    main()
