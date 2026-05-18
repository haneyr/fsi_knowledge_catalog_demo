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
Creates and runs Dataplex data profile, data quality, and data insights scans
for all FSI medallion tables with financial-services-specific quality rules.

Usage: python3 02_create_scans.py
"""

import logging
import time

from common import load_config, api_call, DATAPLEX_URL, SCAN_TABLES, scan_id

logger = logging.getLogger(__name__)


def bq_resource(cfg, dataset, table):
    return f"//bigquery.googleapis.com/projects/{cfg['project_id']}/datasets/{dataset}/tables/{table}"


def build_quality_rules():
    rules = {}

    rules[("fsi_bronze", "bronze_customers")] = [
        {"column": "customer_id", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "customer-id-not-null"},
        {"column": "customer_id", "regexExpectation": {"regex": r"^CUST-\d{8}$"}, "dimension": "VALIDITY", "name": "customer-id-format"},
        {"column": "first_name", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "first-name-not-null"},
        {"column": "last_name", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "last-name-not-null"},
        {"column": "kyc_status", "setExpectation": {"values": ["Verified", "Pending"]}, "dimension": "VALIDITY", "name": "kyc-status-valid"},
        {"tableConditionExpectation": {"sqlExpression": "COUNT(*) >= 10000"}, "dimension": "VOLUME", "name": "min-row-count"},
    ]

    rules[("fsi_bronze", "bronze_accounts")] = [
        {"column": "account_id", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "account-id-not-null"},
        {"column": "customer_id", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "customer-id-not-null"},
        {"column": "account_type", "setExpectation": {"values": ["CHECKING", "SAVINGS", "MONEY_MARKET", "CD", "IRA"]}, "dimension": "VALIDITY", "name": "account-type-valid"},
        {"column": "current_balance", "rangeExpectation": {"minValue": "0"}, "dimension": "VALIDITY", "name": "balance-non-negative"},
    ]

    rules[("fsi_bronze", "bronze_loans")] = [
        {"column": "loan_id", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "loan-id-not-null"},
        {"column": "customer_id", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "customer-id-not-null"},
        {"column": "original_amount", "rangeExpectation": {"minValue": "0", "strictMinEnabled": True}, "dimension": "VALIDITY", "name": "amount-positive"},
        {"column": "interest_rate", "rangeExpectation": {"minValue": "0", "maxValue": "0.30"}, "dimension": "VALIDITY", "name": "rate-range"},
        {"column": "fico_score_at_origination", "rangeExpectation": {"minValue": "300", "maxValue": "850"}, "dimension": "VALIDITY", "name": "fico-range"},
        {"column": "risk_rating", "setExpectation": {"values": ["Pass", "Special Mention", "Substandard", "Doubtful", "Loss"]}, "dimension": "VALIDITY", "name": "risk-rating-valid"},
    ]

    rules[("fsi_silver", "silver_customers")] = [
        {"column": "customer_id", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "pk-not-null"},
        {"column": "customer_id", "uniquenessExpectation": {}, "dimension": "UNIQUENESS", "name": "pk-unique"},
        {"column": "ssn_masked", "regexExpectation": {"regex": r"^XXX-XX-\d{4}$"}, "dimension": "VALIDITY", "name": "ssn-masked-format", "ignoreNull": True},
        {"rowConditionExpectation": {"sqlExpression": "date_of_birth <= CURRENT_DATE()"}, "dimension": "VALIDITY", "name": "dob-not-future"},
    ]

    rules[("fsi_silver", "silver_loans")] = [
        {"column": "loan_id", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "pk-not-null"},
        {"column": "loan_id", "uniquenessExpectation": {}, "dimension": "UNIQUENESS", "name": "pk-unique"},
        {"column": "original_amount", "rangeExpectation": {"minValue": "0"}, "dimension": "VALIDITY", "name": "amount-non-negative"},
        {"column": "current_balance", "rangeExpectation": {"minValue": "0"}, "dimension": "VALIDITY", "name": "balance-non-negative"},
        {"rowConditionExpectation": {"sqlExpression": "current_balance <= original_amount * 1.5"}, "dimension": "CONSISTENCY", "name": "balance-vs-original", "threshold": 0.95},
    ]

    rules[("fsi_gold", "gold_customer_360")] = [
        {"column": "customer_id", "nonNullExpectation": {}, "dimension": "COMPLETENESS", "name": "pk-not-null"},
        {"column": "customer_id", "uniquenessExpectation": {}, "dimension": "UNIQUENESS", "name": "pk-unique"},
        {"column": "total_relationship_value", "rangeExpectation": {"minValue": "0"}, "dimension": "VALIDITY", "name": "relationship-value-non-negative"},
        {"column": "total_deposit_balance", "rangeExpectation": {"minValue": "0"}, "dimension": "VALIDITY", "name": "deposits-non-negative"},
    ]

    rules[("fsi_gold", "gold_loan_portfolio_summary")] = [
        {"column": "loan_count", "rangeExpectation": {"minValue": "0"}, "dimension": "VALIDITY", "name": "count-non-negative"},
        {"column": "delinquency_rate_pct", "rangeExpectation": {"minValue": "0", "maxValue": "100"}, "dimension": "VALIDITY", "name": "rate-pct-range"},
    ]

    return rules


def create_and_run_scan(cfg, dataset, table, stype, spec_body):
    pid = cfg["project_id"]
    loc = cfg["location"]
    sid = scan_id(dataset, table, stype)
    url = f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans?dataScanId={sid}"

    body = {
        **spec_body,
        "data": {"resource": bq_resource(cfg, dataset, table)},
        "displayName": f"{stype.title()}: {dataset}.{table}",
        "description": f"Data {stype} scan for {dataset}.{table}",
    }

    result = api_call(url, "POST", body)
    if result.get("_exists"):
        logger.info("  [%s] %s already exists", stype, sid)
    else:
        logger.info("  [%s] Created %s", stype, sid)
        time.sleep(3)

    run_url = f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans/{sid}:run"
    try:
        api_call(run_url, "POST", {})
        logger.info("  [%s] Started %s", stype, sid)
    except RuntimeError as e:
        logger.warning("  [%s] Failed to run %s: %s", stype, sid, str(e)[:100])
    time.sleep(0.5)


def main():
    cfg = load_config()
    logger.info("Project: %s | Location: %s", cfg["project_id"], cfg["location"])

    quality_rules = build_quality_rules()

    logger.info("=" * 60)
    logger.info("PHASE 1: Data Profile Scans (%d tables)", len(SCAN_TABLES))
    for dataset, table in SCAN_TABLES:
        create_and_run_scan(cfg, dataset, table, "profile", {
            "dataProfileSpec": {"samplingPercent": 25},
        })

    logger.info("=" * 60)
    logger.info("PHASE 2: Data Insights Scans (%d tables)", len(SCAN_TABLES))
    for dataset, table in SCAN_TABLES:
        create_and_run_scan(cfg, dataset, table, "insights", {
            "type": "DATA_DOCUMENTATION",
            "dataDocumentationSpec": {},
        })

    logger.info("=" * 60)
    logger.info("PHASE 3: Data Quality Scans (%d tables)", len(SCAN_TABLES))
    total_rules = 0
    for dataset, table in SCAN_TABLES:
        table_rules = quality_rules.get((dataset, table), [
            {"tableConditionExpectation": {"sqlExpression": "COUNT(*) > 0"}, "dimension": "VOLUME", "name": "has-rows"},
        ])
        total_rules += len(table_rules)
        create_and_run_scan(cfg, dataset, table, "quality", {
            "dataQualitySpec": {"rules": table_rules},
        })

    logger.info("=" * 60)
    logger.info("SCAN CREATION COMPLETE")
    logger.info("  Profile scans:  %d", len(SCAN_TABLES))
    logger.info("  Insights scans: %d", len(SCAN_TABLES))
    logger.info("  Quality scans:  %d (total rules: %d)", len(SCAN_TABLES), total_rules)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
