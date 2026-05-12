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
Creates definition entry links connecting glossary terms to BigQuery table columns.
120+ links across bronze, silver, and gold tables.

Usage: python3 06_create_glossary_links.py
"""

import logging
import time

from common import load_config, api_call, glossary_term_entry, bq_table_entry, DATAPLEX_URL

logger = logging.getLogger(__name__)

LINKS = [
    ("customer-id", "fsi_bronze", "bronze_customers", "customer_id"),
    ("tin", "fsi_bronze", "bronze_customers", "ssn"),
    ("customer-segment", "fsi_bronze", "bronze_customers", "customer_segment"),
    ("kyc", "fsi_bronze", "bronze_customers", "kyc_status"),
    ("checking-account", "fsi_bronze", "bronze_accounts", None),
    ("account-balance", "fsi_bronze", "bronze_accounts", "current_balance"),
    ("mortgage", "fsi_bronze", "bronze_loans", None),
    ("fico-score", "fsi_bronze", "bronze_loans", "fico_score_at_origination"),
    ("ltv-ratio", "fsi_bronze", "bronze_loans", "ltv_ratio"),
    ("dti-ratio", "fsi_bronze", "bronze_loans", "dti_ratio"),
    ("delinquency", "fsi_bronze", "bronze_loans", "delinquency_status"),
    ("risk-rating", "fsi_bronze", "bronze_loans", "risk_rating"),
    ("credit-card", "fsi_bronze", "bronze_credit_cards", "card_id"),
    ("apr", "fsi_bronze", "bronze_credit_cards", "apr"),
    ("wire-transfer", "fsi_bronze", "bronze_wire_transfers", "wire_id"),
    ("ach", "fsi_bronze", "bronze_ach_transfers", "ach_id"),
    ("ctr", "fsi_bronze", "bronze_wire_transfers", "requires_ctr"),
    ("sar", "fsi_bronze", "bronze_fraud_alerts", "sar_filed"),
    ("kyc", "fsi_bronze", "bronze_kyc_records", "kyc_id"),
    ("cdd", "fsi_bronze", "bronze_kyc_records", "due_diligence_level"),
    ("pep", "fsi_bronze", "bronze_kyc_records", "pep_flag"),
    ("beneficial-owner", "fsi_bronze", "bronze_kyc_records", "beneficial_owner_id"),
    ("branch", "fsi_bronze", "bronze_branches", "branch_id"),

    ("customer-id", "fsi_silver", "silver_customers", "customer_id"),
    ("tin", "fsi_silver", "silver_customers", "ssn_masked"),
    ("customer-segment", "fsi_silver", "silver_customers", "customer_segment"),
    ("account-balance", "fsi_silver", "silver_accounts", "current_balance"),
    ("fico-score", "fsi_silver", "silver_loans", "fico_score_at_origination"),
    ("ltv-ratio", "fsi_silver", "silver_loans", "ltv_ratio"),
    ("dti-ratio", "fsi_silver", "silver_loans", "dti_ratio"),
    ("delinquency", "fsi_silver", "silver_loans", "delinquency_status"),
    ("risk-rating", "fsi_silver", "silver_loans", "risk_rating"),
    ("credit-card", "fsi_silver", "silver_credit_cards", "card_id"),
    ("apr", "fsi_silver", "silver_credit_cards", "apr"),
    ("wire-transfer", "fsi_silver", "silver_wire_transfers", "wire_id"),
    ("ach", "fsi_silver", "silver_ach_transfers", "ach_id"),
    ("sar", "fsi_silver", "silver_fraud_alerts", "sar_filed"),

    ("aum", "fsi_bronze", "bronze_wm_clients", "total_aum"),
    ("portfolio", "fsi_bronze", "bronze_portfolios", "portfolio_id"),
    ("asset-allocation", "fsi_bronze", "bronze_holdings", "asset_class"),
    ("cusip", "fsi_bronze", "bronze_securities", "cusip"),
    ("isin", "fsi_bronze", "bronze_securities", "isin"),
    ("ticker-symbol", "fsi_bronze", "bronze_securities", "ticker"),
    ("financial-advisor", "fsi_bronze", "bronze_advisors", "advisor_id"),
    ("advisory-fee", "fsi_bronze", "bronze_fee_schedules", "fee_rate_bps"),
    ("benchmark", "fsi_bronze", "bronze_benchmarks", "benchmark_id"),
    ("sharpe-ratio", "fsi_bronze", "bronze_performance", "sharpe_ratio"),
    ("alpha", "fsi_bronze", "bronze_performance", "alpha"),

    ("aum", "fsi_silver", "silver_wm_clients", "total_aum"),
    ("portfolio", "fsi_silver", "silver_portfolios", "portfolio_id"),
    ("cusip", "fsi_silver", "silver_securities", "cusip"),
    ("isin", "fsi_silver", "silver_securities", "isin"),
    ("financial-advisor", "fsi_silver", "silver_advisors", "advisor_id"),

    ("general-ledger", "fsi_bronze", "bronze_gl_entries", "gl_entry_id"),
    ("general-ledger", "fsi_bronze", "bronze_gl_accounts", "gl_account_id"),
    ("cet1-ratio", "fsi_bronze", "bronze_regulatory_capital", "capital_ratio"),
    ("risk-weighted-assets", "fsi_bronze", "bronze_regulatory_capital", "risk_weighted_assets"),
    ("var", "fsi_bronze", "bronze_risk_exposures", "gross_exposure"),
    ("stress-testing", "fsi_bronze", "bronze_stress_tests", "stress_test_id"),
    ("call-report", "fsi_bronze", "bronze_regulatory_filings", "filing_id"),
    ("ofac-screening", "fsi_bronze", "bronze_wire_transfers", "ofac_hold"),

    ("general-ledger", "fsi_silver", "silver_gl_entries", "gl_entry_id"),
    ("cet1-ratio", "fsi_silver", "silver_regulatory_capital", "capital_ratio"),
    ("risk-weighted-assets", "fsi_silver", "silver_regulatory_capital", "risk_weighted_assets"),

    ("customer-id", "fsi_gold", "gold_customer_360", "customer_id"),
    ("aum", "fsi_gold", "gold_customer_360", "total_aum"),
    ("customer-segment", "fsi_gold", "gold_customer_360", "customer_segment"),
    ("delinquency", "fsi_gold", "gold_delinquency_analysis", "delinquency_status"),
    ("fico-score", "fsi_gold", "gold_loan_portfolio_summary", "avg_fico"),
    ("sar", "fsi_gold", "gold_fraud_analytics", "sar_count"),
    ("cet1-ratio", "fsi_gold", "gold_capital_adequacy", "capital_ratio"),
    ("net-interest-margin", "fsi_gold", "gold_net_interest_margin", "avg_interest_rate"),
    ("branch", "fsi_gold", "gold_branch_performance", "branch_id"),
    ("advisory-fee", "fsi_gold", "gold_fee_revenue", "avg_fee_rate_bps"),
    ("sharpe-ratio", "fsi_gold", "gold_advisor_scorecard", "avg_sharpe_ratio"),
    ("alpha", "fsi_gold", "gold_advisor_scorecard", "avg_alpha"),
    ("var", "fsi_gold", "gold_market_risk_var", "var_99_1d"),
]


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    multi = cfg["multi_region"]

    logger.info("Creating %d glossary definition links", len(LINKS))

    created = 0
    skipped = 0
    failed = 0

    for term_id, dataset, table, column in LINKS:
        col_suffix = f"-{column.replace('_', '-')}" if column else ""
        link_id = f"def-{term_id}-{table.replace('_', '-')}{col_suffix}"[:63]

        source_ref = {"name": bq_table_entry(cfg, dataset, table), "type": "SOURCE"}
        if column:
            source_ref["path"] = f"Schema.{column}"

        body = {
            "entryLinkType": "projects/dataplex-types/locations/global/entryLinkTypes/definition",
            "entryReferences": [
                source_ref,
                {"name": glossary_term_entry(cfg, term_id), "type": "TARGET"},
            ],
        }

        url = f"{DATAPLEX_URL}/projects/{pid}/locations/{multi}/entryGroups/@bigquery/entryLinks?entryLinkId={link_id}"
        try:
            result = api_call(url, "POST", body)
            if result.get("_exists"):
                skipped += 1
            else:
                created += 1
        except RuntimeError:
            failed += 1
        time.sleep(0.3)

    logger.info("Glossary links: %d created, %d existed, %d failed (of %d)", created, skipped, failed, len(LINKS))


if __name__ == "__main__":
    main()
