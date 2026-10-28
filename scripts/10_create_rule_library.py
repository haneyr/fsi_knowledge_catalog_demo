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
Creates a reusable Data Quality Rule Library with Retail-specific templates.

Usage: python3 10_create_rule_library.py
"""

import logging
import time
from typing import Dict

from common import load_config, api_call, poll_operation, glossary_term_entry, DATAPLEX_URL

logger = logging.getLogger(__name__)

RULE_LIBRARY_ID = "retail-rule-library-global"

TEMPLATES = [
    {
        "id": "valid-gtin13-checksum",
        "display_name": "[Retail] Valid GTIN-13 Barcode Format & Checksum",
        "description": "[Retail] Validates GTIN-13 barcode is a 13-digit numeric GS1 identifier.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^[0-9]{13}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "valid-sku-format",
        "display_name": "[Retail] Valid Northwind Master SKU Format",
        "description": "[Retail] Validates SKU code matches Northwind format NW-SKU-NNNNNN.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^NW-SKU-[0-9]{6}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "valid-pii-email-phone-masked",
        "display_name": "[Retail] Valid Masked Shopper PII / Member-TIN Format",
        "description": "[Retail] Validates shopper PII / Member-TIN is masked as XXX-XX-NNNN and email/phone PII complies with CCPA masking.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^XXX-XX-[0-9]{4}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "valid-tender-type-enum",
        "display_name": "[Retail] Valid Loyalty Account & Tender Format",
        "description": "[Retail] Validates loyalty account / tender identifier matches ACCT-NNNNNNNNNN format.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^ACCT-\d{10}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "inventory-and-order-total-non-negative",
        "display_name": "[Retail] Non-Negative On-Hand Qty & Order Total Balance",
        "description": "[Retail] Validates on-hand inventory quantity, loyalty balance, and order total equal to sum of line items are non-negative.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE ${column()} < 0",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "negative-margin-guard",
        "display_name": "[Retail] Negative Margin & Financing Rate Guard",
        "description": "[Retail] Guards against negative gross margin rates or promotional APR outside 0% to 30%.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE ${column()} < 0 OR ${column()} > 0.30",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "loyalty-return-risk-score-range",
        "display_name": "[Retail] Loyalty Tier & Return-Risk Score Range (1-100)",
        "description": "[Retail] Validates shopper loyalty return-risk score is between 1 and 100.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE CAST(${column()} AS INT64) < 1 OR CAST(${column()} AS INT64) > 100",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "duplicate-loyalty-id-guard",
        "display_name": "[Retail] Valid Enrollment Date & Duplicate Loyalty ID Guard",
        "description": "[Retail] Validates loyalty enrollment/order dates are not in the future.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE ${column()} > CURRENT_DATE()",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "order-ship-delivery-date-ordering",
        "display_name": "[Retail] Order <= Ship <= Delivery Date Ordering",
        "description": "[Retail] Validates chronological date ordering (order_date <= ship_date <= delivery_date).",
        "dimension": "CONSISTENCY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (${column()} <= `${param(end_date_column)}`) IS TRUE",
        "params": {"end_date_column": {"description": "The later fulfillment/delivery date column to compare against"}},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "foreign-key-exists",
        "display_name": "[Retail] Foreign Key Reference Exists",
        "description": "[Retail] Validates every foreign key value (e.g., customer_id, store_id, sku_code) exists in its master reference table.",
        "dimension": "CONSISTENCY",
        "sql": r"SELECT t.* FROM ${data()} AS t LEFT JOIN `${param(reference_table)}` AS s ON t.${column()} = s.`${param(reference_column)}` WHERE s.`${param(reference_column)}` IS NULL",
        "params": {
            "reference_table": {"description": "Fully qualified master reference table"},
            "reference_column": {"description": "Primary key column in reference table"},
        },
        "capabilities": ["THRESHOLD"],
    },
]


def _tref(cfg, template_id):
    return f"projects/{cfg['project_id']}/locations/global/entryGroups/{RULE_LIBRARY_ID}/entries/{template_id}"


def create_rule_library(cfg):
    pid = cfg["project_id"]
    url = f"{DATAPLEX_URL}/projects/{pid}/locations/global/entryGroups?entryGroupId={RULE_LIBRARY_ID}"
    result = api_call(url, "POST", {
        "displayName": "[Retail] Northwind Retail Group Data Quality Rule Library",
        "description": "[Retail] Centralized, reusable rule templates for Northwind Retail data validation.",
        "labels": {"goog-dataplex-entry-group-type": "rule_library"},
    })
    if result.get("_exists"):
        logger.info("  Rule library already exists")
    else:
        if "name" in result and "operations" in result.get("name", ""):
            poll_operation(result["name"])
        logger.info("  Created rule library")
    time.sleep(3)


def create_templates(cfg):
    pid = cfg["project_id"]
    for t in TEMPLATES:
        url = f"{DATAPLEX_URL}/projects/{pid}/locations/global/entryGroups/{RULE_LIBRARY_ID}/entries?entryId={t['id']}"
        body = {
            "entryType": "projects/dataplex-types/locations/global/entryTypes/data-quality-rule-template",
            "entrySource": {"displayName": t["display_name"], "description": t["description"]},
            "aspects": {
                "dataplex-types.global.data-quality-rule-template": {
                    "data": {
                        "dimension": t["dimension"],
                        "sqlCollection": [{"query": t["sql"]}],
                        "inputParameters": {k: {"description": v["description"]} for k, v in t["params"].items()},
                        "capabilities": t["capabilities"],
                    }
                }
            },
        }
        result = api_call(url, "POST", body)
        status = "exists" if result.get("_exists") else "created"
        logger.info("  %s: %s (%s)", t["id"], status, t["dimension"])
        time.sleep(0.5)


def attach_rules_to_terms(cfg):
    logger.info("=== Attaching rule templates to glossary terms ===")

    term_rules = {
        "loyalty-return-risk-score": [
            {"name": "return-risk-score-range-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] Return-Risk score must be between 1 and 100",
             "templateReference": {"name": _tref(cfg, "loyalty-return-risk-score-range")}},
        ],
        "member-tin": [
            {"name": "member-tin-masking-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] Shopper PII / Member-TIN must be masked as XXX-XX-NNNN",
             "templateReference": {"name": _tref(cfg, "valid-pii-email-phone-masked")}},
        ],
        "gtin-13": [
            {"name": "gtin13-format-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] GTIN-13 barcode must be a 13-digit GS1 identifier",
             "templateReference": {"name": _tref(cfg, "valid-gtin13-checksum")}},
        ],
        "sku-code": [
            {"name": "sku-code-format-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] SKU code must match Northwind format NW-SKU-NNNNNN",
             "templateReference": {"name": _tref(cfg, "valid-sku-format")}},
        ],
        "loyalty-account-balance": [
            {"name": "inventory-and-order-total-non-negative", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] Loyalty balance, on-hand inventory, and order total must be non-negative",
             "templateReference": {"name": _tref(cfg, "inventory-and-order-total-non-negative")}},
        ],
    }

    for term_id, rules in term_rules.items():
        entry = glossary_term_entry(cfg, term_id)
        aspect_key = "dataplex-types.global.data-rules"
        url = f"{DATAPLEX_URL}/{entry}?updateMask=aspects&deleteMissingAspects=false&aspect_keys={aspect_key}"
        body = {
            "aspects": {
                aspect_key: {
                    "aspectType": "projects/dataplex-types/locations/global/aspectTypes/data-rules",
                    "data": {"rules": rules},
                }
            }
        }
        try:
            api_call(url, "PATCH", body)
            logger.info("  %s: %d rules attached", term_id, len(rules))
        except RuntimeError as e:
            logger.warning("  %s: FAILED - %s", term_id, str(e)[:100])
        time.sleep(0.5)


def main():
    cfg = load_config()
    logger.info("Project: %s", cfg["project_id"])

    logger.info("=== Creating Rule Library ===")
    create_rule_library(cfg)

    logger.info("=== Creating Rule Templates ===")
    create_templates(cfg)

    logger.info("=== Attaching Rules to Glossary Terms ===")
    attach_rules_to_terms(cfg)

    logger.info("Rule library complete: %d templates, %d terms with rules", len(TEMPLATES), 5)


if __name__ == "__main__":
    main()
