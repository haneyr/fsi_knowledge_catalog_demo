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
Creates a Data Catalog taxonomy with policy tags for PII classification,
then applies column-level policy tags to sensitive BigQuery columns.

The KC agent can reference these tags when answering questions about
data sensitivity and access controls.

Usage: python3 16_create_policy_tags.py
"""

import logging
import os
import time

import google.auth
import google.auth.transport.requests
import requests as http_requests
from google.cloud import bigquery

from common import load_config

logger = logging.getLogger(__name__)

CATALOG_URL = "https://datacatalog.googleapis.com/v1"


def _get_token():
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _api(method, url, body=None):
    headers = {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}
    if method == "GET":
        resp = http_requests.get(url, headers=headers)
    elif method == "POST":
        resp = http_requests.post(url, headers=headers, json=body)
    elif method == "PATCH":
        resp = http_requests.patch(url, headers=headers, json=body)
    else:
        raise ValueError(f"Unknown method: {method}")
    if resp.status_code in (200, 201):
        return resp.json() if resp.text.strip() else {}
    if resp.status_code == 409:
        return {"_exists": True}
    raise RuntimeError(f"{method} {url} -> {resp.status_code}: {resp.text[:300]}")


# Overridable because taxonomy display names are deduplicated server-side per
# project+location; a stuck/reserved name would otherwise dead-end this step.
# Keep the override set on every subsequent run, or reruns will create a second
# taxonomy under the default name and repoint the column tags to it.
_RAW_TAXONOMY_DISPLAY = os.environ.get("RETAIL_TAXONOMY_DISPLAY_NAME") or "Retail Demo Sensitivity Taxonomy - alitch"
# Data Catalog taxonomy/policyTag displayNames allow only letters, numbers, spaces, hyphens, and underscores.
TAXONOMY_DISPLAY = _RAW_TAXONOMY_DISPLAY.replace("(", "- ").replace(")", "").replace("[", "").replace("]", "").strip()

POLICY_TAGS = [
    {
        "id": "highly-sensitive",
        "display_name": "Retail - Highly Sensitive PII",
        "description": "[Retail] Direct identifiers: Member-TIN/TIN, date of birth. Requires encryption at rest and column-level masking. Subject to CCPA, FCRA, and state privacy laws.",
    },
    {
        "id": "sensitive",
        "display_name": "Retail - Sensitive PII",
        "description": "[Retail] Personal identifiers: name, email, phone, address. Requires access controls and audit logging. Subject to CCPA and CAN-SPAM.",
    },
    {
        "id": "confidential",
        "display_name": "Retail - Confidential Financial",
        "description": "[Retail] Non-public financial data: Return-Risk scores, APR, AUM, account balances. Internal use only. Subject to Regulation FD and internal information barriers.",
    },
    {
        "id": "internal",
        "display_name": "Retail - Internal",
        "description": "[Retail] Business operational data not for external distribution. Standard access controls apply.",
    },
]

COLUMN_TAGS = [
    ("retail_bronze", "bronze_customers", "member_tin", "highly-sensitive"),
    ("retail_bronze", "bronze_customers", "date_of_birth", "highly-sensitive"),
    ("retail_silver", "silver_customers", "member_tin_masked", "highly-sensitive"),
    ("retail_silver", "silver_customers", "date_of_birth", "highly-sensitive"),

    ("retail_bronze", "bronze_customers", "first_name", "sensitive"),
    ("retail_bronze", "bronze_customers", "last_name", "sensitive"),
    ("retail_bronze", "bronze_customers", "email", "sensitive"),
    ("retail_bronze", "bronze_customers", "phone", "sensitive"),
    ("retail_bronze", "bronze_customers", "address_line1", "sensitive"),
    ("retail_silver", "silver_customers", "first_name", "sensitive"),
    ("retail_silver", "silver_customers", "last_name", "sensitive"),
    ("retail_silver", "silver_customers", "email", "sensitive"),
    ("retail_silver", "silver_customers", "phone", "sensitive"),
    ("retail_silver", "silver_customers", "address_line1", "sensitive"),
    ("retail_gold", "gold_customer_360", "first_name", "sensitive"),
    ("retail_gold", "gold_customer_360", "last_name", "sensitive"),
    ("retail_bronze", "bronze_vip_members", "first_name", "sensitive"),
    ("retail_bronze", "bronze_vip_members", "last_name", "sensitive"),
    ("retail_bronze", "bronze_vip_members", "tax_id", "highly-sensitive"),
    ("retail_silver", "silver_vip_members", "first_name", "sensitive"),
    ("retail_silver", "silver_vip_members", "last_name", "sensitive"),
    ("retail_silver", "silver_vip_members", "tax_id_masked", "highly-sensitive"),

    ("retail_bronze", "bronze_bnpl_plans", "return_risk_score_at_signup", "confidential"),
    ("retail_silver", "silver_bnpl_plans", "return_risk_score_at_signup", "confidential"),
    ("retail_bronze", "bronze_store_cards", "apr", "confidential"),
    ("retail_silver", "silver_store_cards", "apr", "confidential"),
    ("retail_bronze", "bronze_vip_members", "total_aum", "confidential"),
    ("retail_silver", "silver_vip_members", "total_aum", "confidential"),
    ("retail_gold", "gold_customer_360", "total_aum", "confidential"),
    ("retail_gold", "gold_customer_360", "total_relationship_value", "confidential"),
    ("retail_bronze", "bronze_loyalty_accounts", "current_balance", "confidential"),
    ("retail_silver", "silver_loyalty_accounts", "current_balance", "confidential"),
]


def _find_taxonomy(url):
    """Poll the taxonomy list until the target appears (read-after-write lag)."""
    for attempt in range(10):
        if attempt:
            time.sleep(5 * (attempt + 1))
        list_resp = _api("GET", url)
        for t in list_resp.get("taxonomies", []):
            if t.get("displayName") == TAXONOMY_DISPLAY:
                return t["name"]
    return None


def create_taxonomy(pid, location="us"):
    url = f"{CATALOG_URL}/projects/{pid}/locations/{location}/taxonomies"
    body = {
        "displayName": TAXONOMY_DISPLAY,
        "description": "[Retail] Data classification taxonomy for Northwind Retail Group Retail demo. Defines sensitivity levels for column-level policy enforcement.",
        "activatedPolicyTypes": ["FINE_GRAINED_ACCESS_CONTROL"],
    }
    result = _api("POST", url, body)
    if not result.get("_exists"):
        logger.info("  Created taxonomy: %s", result.get("name"))
        return result["name"]

    logger.info("  Taxonomy already exists, waiting for it to appear in listings...")
    name = _find_taxonomy(url)
    if name:
        return name
    raise RuntimeError(
        f"Taxonomy '{TAXONOMY_DISPLAY}' returned 409 but didn't appear in listings after "
        f"retries. The display name may be reserved server-side; re-run with "
        f"RETAIL_TAXONOMY_DISPLAY_NAME=<alternate name> (and keep it set for future runs)."
    )


def create_policy_tags(taxonomy_name):
    tag_map = {}
    for tag in POLICY_TAGS:
        url = f"{CATALOG_URL}/{taxonomy_name}/policyTags"
        body = {
            "displayName": tag["display_name"],
            "description": tag["description"],
        }
        try:
            result = _api("POST", url, body)
            if result.get("_exists"):
                list_resp = _api("GET", url)
                for pt in list_resp.get("policyTags", []):
                    if pt.get("displayName") == tag["display_name"]:
                        tag_map[tag["id"]] = pt["name"]
                        break
            else:
                tag_map[tag["id"]] = result["name"]
                logger.info("  Created policy tag: %s", tag["display_name"])
        except RuntimeError as e:
            if "already exists" in str(e).lower():
                list_resp = _api("GET", url)
                for pt in list_resp.get("policyTags", []):
                    if pt.get("displayName") == tag["display_name"]:
                        tag_map[tag["id"]] = pt["name"]
                        break
            else:
                logger.warning("  Failed to create %s: %s", tag["id"], str(e)[:100])
        time.sleep(0.5)

    return tag_map


def apply_column_tags(pid, tag_map):
    bq_client = bigquery.Client(project=pid)
    tagged = 0
    failed = 0

    tables_cache = {}

    for dataset, table, column, tag_id in COLUMN_TAGS:
        tag_name = tag_map.get(tag_id)
        if not tag_name:
            logger.warning("  No policy tag for %s, skipping %s.%s.%s", tag_id, dataset, table, column)
            failed += 1
            continue

        table_ref = f"{pid}.{dataset}.{table}"

        if table_ref not in tables_cache:
            try:
                tables_cache[table_ref] = bq_client.get_table(table_ref)
            except Exception as e:
                logger.warning("  Table %s not found: %s", table_ref, str(e)[:60])
                failed += 1
                continue

        bq_table = tables_cache[table_ref]
        new_schema = []
        found = False

        for field in bq_table.schema:
            if field.name == column:
                found = True
                field_dict = field.to_api_repr()
                field_dict["policyTags"] = {"names": [tag_name]}
                new_schema.append(bigquery.SchemaField.from_api_repr(field_dict))
            else:
                new_schema.append(field)

        if not found:
            logger.warning("  Column %s not found in %s", column, table_ref)
            failed += 1
            continue

        bq_table.schema = new_schema
        try:
            bq_client.update_table(bq_table, ["schema"])
            tagged += 1
        except Exception as e:
            logger.warning("  Failed to tag %s.%s: %s", table, column, str(e)[:100])
            failed += 1

        tables_cache[table_ref] = bq_client.get_table(table_ref)

    return tagged, failed


def main():
    cfg = load_config()
    pid = cfg["project_id"]

    import subprocess
    subprocess.run(["gcloud", "services", "enable", "datacatalog.googleapis.com",
                     f"--project={pid}"], capture_output=True)
    logger.info("Enabled Data Catalog API")
    time.sleep(3)

    logger.info("=== Creating taxonomy ===")
    taxonomy_name = create_taxonomy(pid)
    logger.info("  Taxonomy: %s", taxonomy_name)

    logger.info("=== Creating policy tags ===")
    tag_map = create_policy_tags(taxonomy_name)
    logger.info("  Tags created: %d", len(tag_map))
    for tag_id, tag_name in tag_map.items():
        logger.info("    %s: %s", tag_id, tag_name)

    logger.info("=== Applying column-level policy tags ===")
    tagged, failed = apply_column_tags(pid, tag_map)

    logger.info("=== Granting fine-grained reader on taxonomy ===")
    pn = cfg.get("project_number", "")
    if not pn:
        pn = subprocess.run(
            ["gcloud", "projects", "describe", pid, "--format=value(projectNumber)"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    active_user = subprocess.run(
        ["gcloud", "config", "get-value", "account"],
        capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    principals = [
        f"serviceAccount:service-{pn}@gcp-sa-aiplatform-re.iam.gserviceaccount.com",
        f"serviceAccount:service-{pn}@gcp-sa-dataplex.iam.gserviceaccount.com",
        f"serviceAccount:{pn}-compute@developer.gserviceaccount.com",
    ]
    if active_user:
        principals.append(f"user:{active_user}")
    for sa in principals:
        subprocess.run([
            "gcloud", "data-catalog", "taxonomies", "add-iam-policy-binding", taxonomy_name,
            "--location=us", f"--project={pid}",
            f"--member={sa}", "--role=roles/datacatalog.categoryFineGrainedReader",
            "--quiet",
        ], capture_output=True)
        logger.info("  Granted fine-grained reader to %s", sa.split(":")[-1][:40])

    logger.info("=" * 60)
    logger.info("POLICY TAGS COMPLETE")
    logger.info("  Taxonomy: %s", TAXONOMY_DISPLAY)
    logger.info("  Policy tags: %d", len(tag_map))
    logger.info("  Columns tagged: %d", tagged)
    logger.info("  Failed: %d", failed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
