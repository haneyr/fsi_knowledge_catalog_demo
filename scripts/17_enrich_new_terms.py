#!/usr/bin/env python3
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

"""
Enrich new glossary terms with synonym links, related links, and
definition links to BigQuery tables/columns.

Creates the AML term and adds relationships for: AML, Basel III,
Wire Transfer, BSA, Sharpe Ratio, Stress Testing, Liquidity Risk,
Charge-Off, ACH Transfer.

Usage: python3 scripts/17_enrich_new_terms.py
"""

import json
import logging
import os
import sys

import google.auth
import google.auth.transport.requests
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATAPLEX_URL = "https://dataplex.googleapis.com/v1"
GLOSSARY_ID = "meridian-national-bank-glossary-us"


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            raw = json.load(f)
        cfg = {}
        for k, v in raw.items():
            cfg[k] = v.get("value", v) if isinstance(v, dict) else v
        return cfg
    pid = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    import subprocess
    pn = subprocess.run(
        ["gcloud", "projects", "describe", pid, "--format=value(projectNumber)"],
        capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    return {"project_id": pid, "project_number": pn, "multi_region": "us"}


def get_token():
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def api_call(url, method, body=None):
    headers = {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"}
    if method == "POST":
        resp = requests.post(url, headers=headers, json=body, timeout=30)
    else:
        resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code in (200, 409):
        return resp.json() if resp.status_code == 200 else None
    logger.warning("API %s %s -> %d: %s", method, url.split("?")[0].split("/")[-1], resp.status_code, resp.text[:200])
    return None


def glossary_term_entry(cfg, term_id):
    pn = cfg["project_number"]
    loc = cfg["multi_region"]
    return (
        f"projects/{pn}/locations/{loc}/entryGroups/@dataplex/entries/"
        f"projects/{pn}/locations/{loc}/glossaries/{GLOSSARY_ID}/terms/{term_id}"
    )


def bq_table_entry(cfg, dataset, table):
    pn = cfg["project_number"]
    pid = cfg["project_id"]
    loc = cfg["multi_region"]
    return (
        f"projects/{pn}/locations/{loc}/entryGroups/@bigquery/entries/"
        f"bigquery.googleapis.com/projects/{pid}/datasets/{dataset}/tables/{table}"
    )


def create_term(cfg, term_id, display_name, description, category_id):
    pid = cfg["project_id"]
    loc = cfg["multi_region"]
    parent = f"projects/{pid}/locations/{loc}/glossaries/{GLOSSARY_ID}/categories/{category_id}"
    url = (
        f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}"
        f"/glossaries/{GLOSSARY_ID}/terms?termId={term_id}"
    )
    body = {
        "displayName": display_name,
        "description": description,
        "parent": parent,
    }
    result = api_call(url, "POST", body)
    if result:
        logger.info("Created term: %s", display_name)
    return result


def create_synonym_link(cfg, term_a, term_b):
    pid = cfg["project_id"]
    loc = cfg["multi_region"]
    link_id = f"syn-{term_a}-{term_b}"
    url = (
        f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}"
        f"/entryGroups/@dataplex/entryLinks?entryLinkId={link_id}"
    )
    body = {
        "entryLinkType": "projects/dataplex-types/locations/global/entryLinkTypes/synonym",
        "entryReferences": [
            {"name": glossary_term_entry(cfg, term_a), "type": "UNSPECIFIED"},
            {"name": glossary_term_entry(cfg, term_b), "type": "UNSPECIFIED"},
        ],
    }
    result = api_call(url, "POST", body)
    if result:
        logger.info("Created synonym: %s <-> %s", term_a, term_b)


def create_related_link(cfg, term_a, term_b):
    pid = cfg["project_id"]
    loc = cfg["multi_region"]
    link_id = f"rel-{term_a}-{term_b}"
    url = (
        f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}"
        f"/entryGroups/@dataplex/entryLinks?entryLinkId={link_id}"
    )
    body = {
        "entryLinkType": "projects/dataplex-types/locations/global/entryLinkTypes/related",
        "entryReferences": [
            {"name": glossary_term_entry(cfg, term_a), "type": "UNSPECIFIED"},
            {"name": glossary_term_entry(cfg, term_b), "type": "UNSPECIFIED"},
        ],
    }
    result = api_call(url, "POST", body)
    if result:
        logger.info("Created related: %s <-> %s", term_a, term_b)


def create_definition_link(cfg, term_id, dataset, table, column=None):
    pid = cfg["project_id"]
    loc = cfg["multi_region"]
    col_suffix = f"-{column.replace('_', '-')}" if column else ""
    link_id = f"def-{term_id}-{table.replace('_', '-')}{col_suffix}"
    if len(link_id) > 63:
        link_id = link_id[:63]

    source_ref = {"name": bq_table_entry(cfg, dataset, table), "type": "SOURCE"}
    if column:
        source_ref["path"] = f"Schema.{column}"

    url = (
        f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}"
        f"/entryGroups/@bigquery/entryLinks?entryLinkId={link_id}"
    )
    body = {
        "entryLinkType": "projects/dataplex-types/locations/global/entryLinkTypes/definition",
        "entryReferences": [
            source_ref,
            {"name": glossary_term_entry(cfg, term_id), "type": "TARGET"},
        ],
    }
    result = api_call(url, "POST", body)
    if result:
        tgt = f"{table}.{column}" if column else table
        logger.info("Created definition: %s -> %s", term_id, tgt)


# === New term to create ===
NEW_TERMS = [
    ("aml", "AML (Anti-Money Laundering)",
     "A set of laws, regulations, and procedures intended to prevent criminals from "
     "disguising illegally obtained funds as legitimate income. Banks must implement "
     "AML programs including customer due diligence, transaction monitoring, and "
     "suspicious activity reporting under the Bank Secrecy Act.",
     "bsa-aml"),
]

# === Synonym links (abbreviation <-> full term) ===
SYNONYM_LINKS = [
    ("bsa", "bsa-abbr"),           # Bank Secrecy Act <-> BSA abbrev
    ("aml", "sar"),                # AML closely related to SAR
    ("nim-abbr", "net-interest-margin"),
    ("acl-abbr", "allowance-for-credit-losses"),
]

# === Related term links ===
RELATED_LINKS = [
    # AML relationships
    ("aml", "bsa"),                # AML <-> BSA
    ("aml", "kyc"),                # AML <-> KYC
    ("aml", "sar"),                # AML <-> SAR
    ("aml", "cdd"),                # AML <-> CDD
    ("aml", "wire-transfer"),      # AML <-> Wire Transfer

    # Basel III relationships
    ("basel-iii", "cet1-ratio"),    # Basel III <-> CET1 Ratio
    ("basel-iii", "stress-testing"), # Basel III <-> Stress Testing
    ("basel-iii", "liquidity-risk"), # Basel III <-> Liquidity Risk

    # Wire Transfer relationships
    ("wire-transfer", "ach"),       # Wire Transfer <-> ACH Transfer
    ("wire-transfer", "bsa"),       # Wire Transfer <-> BSA (reportable)

    # Stress Testing relationships
    ("stress-testing", "cet1-ratio"),
    ("stress-testing", "liquidity-risk"),
    ("stress-testing", "dfast"),

    # Liquidity Risk relationships
    ("liquidity-risk", "cet1-ratio"),

    # Charge-Off relationships
    ("charge-off", "delinquency"),
    ("charge-off", "allowance-for-credit-losses"),
    ("charge-off", "risk-rating"),

    # Sharpe Ratio relationships
    ("sharpe-ratio", "alpha"),
    ("sharpe-ratio", "benchmark"),
    ("sharpe-ratio", "aum"),
]

# === Definition links (term -> table.column) ===
DEFINITION_LINKS = [
    # AML -> tables
    ("aml", "fsi_gold", "gold_aml_risk_scoring", None),
    ("aml", "fsi_gold", "gold_fraud_analytics", None),
    ("aml", "fsi_bronze", "bronze_compliance_cases", None),

    # Basel III -> tables
    ("basel-iii", "fsi_gold", "gold_capital_adequacy", None),
    ("basel-iii", "fsi_gold", "gold_regulatory_dashboard", None),
    ("basel-iii", "fsi_bronze", "bronze_regulatory_capital", None),

    # Wire Transfer -> tables
    ("wire-transfer", "fsi_silver", "silver_wire_transfers", None),
    ("wire-transfer", "fsi_bronze", "bronze_wire_transfers", None),

    # Stress Testing -> tables
    ("stress-testing", "fsi_bronze", "bronze_stress_tests", None),
    ("stress-testing", "fsi_gold", "gold_capital_adequacy", None),

    # Liquidity Risk -> tables
    ("liquidity-risk", "fsi_gold", "gold_liquidity_coverage", None),

    # Charge-Off -> tables/columns
    ("charge-off", "fsi_gold", "gold_loan_portfolio_summary", None),
    ("charge-off", "fsi_gold", "gold_delinquency_analysis", None),

    # ACH Transfer -> tables
    ("ach", "fsi_silver", "silver_ach_transfers", None),
    ("ach", "fsi_bronze", "bronze_ach_transfers", None),

    # Sharpe Ratio -> tables/columns
    ("sharpe-ratio", "fsi_gold", "gold_portfolio_performance", "avg_sharpe_ratio"),
    ("sharpe-ratio", "fsi_silver", "silver_performance", None),

    # BSA -> tables
    ("bsa", "fsi_gold", "gold_aml_risk_scoring", None),
    ("bsa", "fsi_gold", "gold_fraud_analytics", None),
    ("bsa", "fsi_bronze", "bronze_compliance_cases", None),
]


def main():
    cfg = load_config()
    logger.info("=" * 60)
    logger.info("Enriching glossary terms with links")
    logger.info("  Project: %s (%s)", cfg["project_id"], cfg["project_number"])
    logger.info("=" * 60)

    logger.info("--- Creating new terms ---")
    for term_id, display_name, description, category in NEW_TERMS:
        create_term(cfg, term_id, display_name, description, category)

    logger.info("--- Creating synonym links (%d) ---", len(SYNONYM_LINKS))
    for term_a, term_b in SYNONYM_LINKS:
        try:
            create_synonym_link(cfg, term_a, term_b)
        except Exception as e:
            logger.warning("Failed synonym %s<->%s: %s", term_a, term_b, e)

    logger.info("--- Creating related links (%d) ---", len(RELATED_LINKS))
    for term_a, term_b in RELATED_LINKS:
        try:
            create_related_link(cfg, term_a, term_b)
        except Exception as e:
            logger.warning("Failed related %s<->%s: %s", term_a, term_b, e)

    logger.info("--- Creating definition links (%d) ---", len(DEFINITION_LINKS))
    for term_id, dataset, table, column in DEFINITION_LINKS:
        try:
            create_definition_link(cfg, term_id, dataset, table, column)
        except Exception as e:
            logger.warning("Failed definition %s->%s: %s", term_id, table, e)

    logger.info("=" * 60)
    logger.info("Done. Created: %d terms, %d synonym, %d related, %d definition links",
                len(NEW_TERMS), len(SYNONYM_LINKS), len(RELATED_LINKS), len(DEFINITION_LINKS))


if __name__ == "__main__":
    main()
