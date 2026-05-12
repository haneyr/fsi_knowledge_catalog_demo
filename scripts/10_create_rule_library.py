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
Creates a reusable Data Quality Rule Library with FSI-specific templates.

Usage: python3 10_create_rule_library.py
"""

import logging
import time
from typing import Dict

from common import load_config, api_call, poll_operation, glossary_term_entry, DATAPLEX_URL

logger = logging.getLogger(__name__)

RULE_LIBRARY_ID = "fsi-rule-library-global"

TEMPLATES = [
    {
        "id": "valid-cusip-format",
        "display_name": "Valid CUSIP Format",
        "description": "Validates 9-character CUSIP format (alphanumeric).",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^[A-Z0-9]{9}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "valid-isin-format",
        "display_name": "Valid ISIN Format",
        "description": "Validates 12-character ISIN format (2-letter country + 9 alphanum + check digit).",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "valid-ssn-tin-masked",
        "display_name": "Valid Masked SSN/TIN Format",
        "description": "Validates SSN/TIN is masked as XXX-XX-NNNN.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^XXX-XX-[0-9]{4}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "valid-account-id-format",
        "display_name": "Valid Account ID Format",
        "description": "Validates account ID matches ACCT-NNNNNNNNNN format.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^ACCT-\d{10}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "balance-non-negative",
        "display_name": "Balance Non-Negative",
        "description": "Validates financial balance columns are non-negative.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE ${column()} < 0",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "interest-rate-range",
        "display_name": "Interest Rate In Valid Range",
        "description": "Validates interest rate is between 0% and 30%.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE ${column()} < 0 OR ${column()} > 0.30",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "fico-score-range",
        "display_name": "FICO Score Range",
        "description": "Validates FICO score is between 300 and 850.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE CAST(${column()} AS INT64) < 300 OR CAST(${column()} AS INT64) > 850",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "date-not-future",
        "display_name": "Date Not In Future",
        "description": "Validates a date column does not contain future dates.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE ${column()} > CURRENT_DATE()",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "date-ordering",
        "display_name": "Date Column Ordering",
        "description": "Validates one date column is on or before another (e.g., origination <= maturity).",
        "dimension": "CONSISTENCY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (${column()} <= `${param(end_date_column)}`) IS TRUE",
        "params": {"end_date_column": {"description": "The later date column to compare against"}},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "foreign-key-exists",
        "display_name": "Foreign Key Reference Exists",
        "description": "Validates every value in a column exists in a reference table.",
        "dimension": "CONSISTENCY",
        "sql": r"SELECT t.* FROM ${data()} AS t LEFT JOIN `${param(reference_table)}` AS s ON t.${column()} = s.`${param(reference_column)}` WHERE s.`${param(reference_column)}` IS NULL",
        "params": {
            "reference_table": {"description": "Fully qualified reference table"},
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
        "displayName": "Meridian National Bank Data Quality Rule Library",
        "description": "Centralized, reusable rule templates for FSI data validation.",
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
    term_rules = {
        "fico-score": [
            {"name": "fico-range-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "FICO score must be 300-850",
             "templateReference": {"name": _tref(cfg, "fico-score-range")}},
        ],
        "tin": [
            {"name": "tin-masking-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "TIN/SSN must be masked as XXX-XX-NNNN",
             "templateReference": {"name": _tref(cfg, "valid-ssn-tin-masked")}},
        ],
        "cusip": [
            {"name": "cusip-format-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "CUSIP must be 9 alphanumeric characters",
             "templateReference": {"name": _tref(cfg, "valid-cusip-format")}},
        ],
        "isin": [
            {"name": "isin-format-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "ISIN must be 12-character international format",
             "templateReference": {"name": _tref(cfg, "valid-isin-format")}},
        ],
        "account-balance": [
            {"name": "balance-non-negative", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "Account balance must be non-negative",
             "templateReference": {"name": _tref(cfg, "balance-non-negative")}},
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
