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
Creates comprehensive definition links between glossary terms and BigQuery
data assets (tables and columns) using the Dataplex entryLinks API.

Covers all 83 glossary terms with links to relevant tables and columns
across bronze, silver, and gold layers. Uses entryLinkType "definition"
per https://docs.cloud.google.com/dataplex/docs/manage-glossaries#links-terms-asset

Usage: python3 14_link_glossary_to_assets.py
"""

import logging
import time

from common import load_config, api_call, glossary_term_entry, bq_table_entry, DATAPLEX_URL

logger = logging.getLogger(__name__)

# (term_id, dataset, table, column_or_None)
# column=None means table-level link; column="col_name" means column-level link
LINKS = [
    # =========================================================================
    # Customer & Identity
    # =========================================================================
    # customer-id
    ("customer-id", "fsi_bronze", "bronze_customers", "customer_id"),
    ("customer-id", "fsi_silver", "silver_customers", "customer_id"),
    ("customer-id", "fsi_gold", "gold_customer_360", "customer_id"),
    ("customer-id", "fsi_gold", "gold_account_summary", "customer_id"),
    # kyc
    ("kyc", "fsi_bronze", "bronze_kyc_records", None),
    ("kyc", "fsi_silver", "silver_kyc_records", None),
    ("kyc", "fsi_gold", "gold_customer_360", "kyc_status"),
    ("kyc", "fsi_gold", "gold_customer_360", "kyc_risk_rating"),
    ("kyc", "fsi_gold", "gold_aml_risk_scoring", "kyc_risk_rating"),
    # cdd
    ("cdd", "fsi_bronze", "bronze_kyc_records", "due_diligence_level"),
    ("cdd", "fsi_gold", "gold_aml_risk_scoring", "due_diligence_level"),
    # edd
    ("edd", "fsi_bronze", "bronze_kyc_records", "due_diligence_level"),
    # beneficial-owner
    ("beneficial-owner", "fsi_bronze", "bronze_kyc_records", "beneficial_owner_id"),
    # pep
    ("pep", "fsi_bronze", "bronze_kyc_records", "pep_flag"),
    ("pep", "fsi_gold", "gold_aml_risk_scoring", "pep_count"),
    # customer-segment
    ("customer-segment", "fsi_bronze", "bronze_customers", "customer_segment"),
    ("customer-segment", "fsi_silver", "silver_customers", "customer_segment"),
    ("customer-segment", "fsi_gold", "gold_customer_360", "customer_segment"),
    ("customer-segment", "fsi_gold", "gold_aml_risk_scoring", "customer_segment"),
    # tin
    ("tin", "fsi_bronze", "bronze_customers", "ssn"),
    ("tin", "fsi_silver", "silver_customers", "ssn_masked"),

    # =========================================================================
    # Deposits & Accounts
    # =========================================================================
    # checking-account
    ("checking-account", "fsi_bronze", "bronze_accounts", None),
    ("checking-account", "fsi_gold", "gold_account_summary", "account_type"),
    # savings-account
    ("savings-account", "fsi_bronze", "bronze_accounts", None),
    # certificate-of-deposit
    ("certificate-of-deposit", "fsi_bronze", "bronze_accounts", None),
    # money-market-account
    ("money-market-account", "fsi_bronze", "bronze_accounts", None),
    # fdic-coverage
    ("fdic-coverage", "fsi_bronze", "bronze_accounts", None),
    # dormant-account
    ("dormant-account", "fsi_gold", "gold_account_summary", "is_dormant"),
    # account-balance
    ("account-balance", "fsi_bronze", "bronze_accounts", "current_balance"),
    ("account-balance", "fsi_silver", "silver_accounts", "current_balance"),
    ("account-balance", "fsi_gold", "gold_account_summary", "current_balance"),
    ("account-balance", "fsi_gold", "gold_customer_360", "total_deposit_balance"),

    # =========================================================================
    # Lending & Credit
    # =========================================================================
    # mortgage
    ("mortgage", "fsi_bronze", "bronze_loans", None),
    ("mortgage", "fsi_gold", "gold_loan_portfolio_summary", "loan_type"),
    # auto-loan
    ("auto-loan", "fsi_bronze", "bronze_loans", None),
    # heloc
    ("heloc", "fsi_bronze", "bronze_loans", None),
    # commercial-loan
    ("commercial-loan", "fsi_bronze", "bronze_loans", None),
    # fico-score
    ("fico-score", "fsi_bronze", "bronze_loans", "fico_score_at_origination"),
    ("fico-score", "fsi_silver", "silver_loans", "fico_score_at_origination"),
    ("fico-score", "fsi_gold", "gold_loan_portfolio_summary", "avg_fico"),
    ("fico-score", "fsi_gold", "gold_delinquency_analysis", "avg_origination_fico"),
    # ltv-ratio
    ("ltv-ratio", "fsi_bronze", "bronze_loans", "ltv_ratio"),
    ("ltv-ratio", "fsi_silver", "silver_loans", "ltv_ratio"),
    ("ltv-ratio", "fsi_gold", "gold_loan_portfolio_summary", "avg_ltv"),
    ("ltv-ratio", "fsi_gold", "gold_delinquency_analysis", "avg_ltv"),
    # dti-ratio
    ("dti-ratio", "fsi_bronze", "bronze_loans", "dti_ratio"),
    ("dti-ratio", "fsi_silver", "silver_loans", "dti_ratio"),
    ("dti-ratio", "fsi_gold", "gold_loan_portfolio_summary", "avg_dti"),
    # delinquency
    ("delinquency", "fsi_bronze", "bronze_loans", "delinquency_status"),
    ("delinquency", "fsi_silver", "silver_loans", "delinquency_status"),
    ("delinquency", "fsi_gold", "gold_loan_portfolio_summary", "delinquency_status"),
    ("delinquency", "fsi_gold", "gold_delinquency_analysis", None),
    # risk-rating
    ("risk-rating", "fsi_bronze", "bronze_loans", "risk_rating"),
    ("risk-rating", "fsi_silver", "silver_loans", "risk_rating"),
    ("risk-rating", "fsi_gold", "gold_loan_portfolio_summary", "risk_rating"),
    # charge-off
    ("charge-off", "fsi_gold", "gold_delinquency_analysis", "classified_count"),

    # =========================================================================
    # Cards & Payments
    # =========================================================================
    # credit-card
    ("credit-card", "fsi_bronze", "bronze_credit_cards", None),
    ("credit-card", "fsi_silver", "silver_credit_cards", None),
    ("credit-card", "fsi_gold", "gold_customer_360", "total_cards"),
    ("credit-card", "fsi_gold", "gold_customer_360", "total_card_balance"),
    # apr
    ("apr", "fsi_bronze", "bronze_credit_cards", "apr"),
    ("apr", "fsi_silver", "silver_credit_cards", "apr"),
    # interchange-fee
    ("interchange-fee", "fsi_bronze", "bronze_card_transactions", None),
    # chargeback
    ("chargeback", "fsi_bronze", "bronze_card_transactions", None),
    # ach
    ("ach", "fsi_bronze", "bronze_ach_transfers", None),
    ("ach", "fsi_silver", "silver_ach_transfers", None),
    # wire-transfer
    ("wire-transfer", "fsi_bronze", "bronze_wire_transfers", None),
    ("wire-transfer", "fsi_silver", "silver_wire_transfers", None),
    ("wire-transfer", "fsi_gold", "gold_aml_risk_scoring", "large_wire_volume"),
    # ctr
    ("ctr", "fsi_bronze", "bronze_wire_transfers", "requires_ctr"),
    ("ctr", "fsi_silver", "silver_wire_transfers", "requires_ctr"),

    # =========================================================================
    # Wealth & Investments
    # =========================================================================
    # aum
    ("aum", "fsi_bronze", "bronze_wm_clients", "total_aum"),
    ("aum", "fsi_silver", "silver_wm_clients", "total_aum"),
    ("aum", "fsi_gold", "gold_customer_360", "total_aum"),
    ("aum", "fsi_gold", "gold_advisor_scorecard", "total_aum"),
    ("aum", "fsi_gold", "gold_client_revenue", "total_aum"),
    # portfolio
    ("portfolio", "fsi_bronze", "bronze_portfolios", None),
    ("portfolio", "fsi_silver", "silver_portfolios", None),
    ("portfolio", "fsi_gold", "gold_portfolio_performance", None),
    # asset-allocation
    ("asset-allocation", "fsi_bronze", "bronze_holdings", "asset_class"),
    ("asset-allocation", "fsi_gold", "gold_asset_allocation", None),
    # benchmark
    ("benchmark", "fsi_bronze", "bronze_benchmarks", None),
    ("benchmark", "fsi_gold", "gold_portfolio_performance", "benchmark_id"),
    ("benchmark", "fsi_gold", "gold_portfolio_performance", "benchmark_name"),
    # alpha
    ("alpha", "fsi_gold", "gold_portfolio_performance", "avg_alpha"),
    ("alpha", "fsi_gold", "gold_advisor_scorecard", "avg_alpha"),
    # sharpe-ratio
    ("sharpe-ratio", "fsi_gold", "gold_portfolio_performance", "avg_sharpe_ratio"),
    ("sharpe-ratio", "fsi_gold", "gold_advisor_scorecard", "avg_sharpe_ratio"),
    # financial-advisor
    ("financial-advisor", "fsi_bronze", "bronze_advisors", None),
    ("financial-advisor", "fsi_silver", "silver_advisors", None),
    ("financial-advisor", "fsi_gold", "gold_advisor_scorecard", None),
    ("financial-advisor", "fsi_gold", "gold_client_revenue", "primary_advisor_id"),
    # advisory-fee
    ("advisory-fee", "fsi_bronze", "bronze_fee_schedules", "fee_rate_bps"),
    ("advisory-fee", "fsi_gold", "gold_fee_revenue", None),
    ("advisory-fee", "fsi_gold", "gold_advisor_scorecard", "avg_fee_bps"),
    ("advisory-fee", "fsi_gold", "gold_client_revenue", "avg_fee_rate_bps"),
    # fiduciary-duty
    ("fiduciary-duty", "fsi_bronze", "bronze_advisors", None),
    # accredited-investor
    ("accredited-investor", "fsi_bronze", "bronze_wm_clients", "client_tier"),

    # =========================================================================
    # Trading & Securities
    # =========================================================================
    # cusip
    ("cusip", "fsi_bronze", "bronze_securities", "cusip"),
    ("cusip", "fsi_silver", "silver_securities", "cusip"),
    # isin
    ("isin", "fsi_bronze", "bronze_securities", "isin"),
    ("isin", "fsi_silver", "silver_securities", "isin"),
    # ticker-symbol
    ("ticker-symbol", "fsi_bronze", "bronze_securities", "ticker"),
    ("ticker-symbol", "fsi_silver", "silver_securities", "ticker"),
    # trade-settlement
    ("trade-settlement", "fsi_bronze", "bronze_trades", None),
    ("trade-settlement", "fsi_silver", "silver_trades", None),
    # order-type
    ("order-type", "fsi_bronze", "bronze_trades", "order_type"),

    # =========================================================================
    # Risk Management
    # =========================================================================
    # var
    ("var", "fsi_gold", "gold_market_risk_var", None),
    ("var", "fsi_gold", "gold_market_risk_var", "var_99_1d"),
    ("var", "fsi_gold", "gold_market_risk_var", "var_95_1d"),
    ("var", "fsi_gold", "gold_market_risk_var", "var_99_10d"),
    # credit-risk
    ("credit-risk", "fsi_bronze", "bronze_risk_exposures", None),
    ("credit-risk", "fsi_gold", "gold_delinquency_analysis", None),
    ("credit-risk", "fsi_gold", "gold_loan_portfolio_summary", None),
    # market-risk
    ("market-risk", "fsi_gold", "gold_market_risk_var", None),
    ("market-risk", "fsi_gold", "gold_market_risk_var", "return_volatility"),
    # operational-risk
    ("operational-risk", "fsi_gold", "gold_operational_risk", None),
    # liquidity-risk
    ("liquidity-risk", "fsi_gold", "gold_liquidity_coverage", None),
    ("liquidity-risk", "fsi_gold", "gold_liquidity_coverage", "lcr_ratio"),
    # counterparty-risk
    ("counterparty-risk", "fsi_bronze", "bronze_counterparties", None),
    ("counterparty-risk", "fsi_silver", "silver_counterparties", None),
    ("counterparty-risk", "fsi_bronze", "bronze_risk_exposures", "counterparty_id"),
    # stress-testing
    ("stress-testing", "fsi_bronze", "bronze_stress_tests", None),
    ("stress-testing", "fsi_silver", "silver_stress_tests", None),

    # =========================================================================
    # Regulatory & Compliance
    # =========================================================================
    # sar
    ("sar", "fsi_bronze", "bronze_fraud_alerts", "sar_filed"),
    ("sar", "fsi_silver", "silver_fraud_alerts", "sar_filed"),
    ("sar", "fsi_gold", "gold_fraud_analytics", "sar_count"),
    ("sar", "fsi_gold", "gold_aml_risk_scoring", "sar_filings"),
    ("sar", "fsi_bronze", "bronze_compliance_cases", "sar_filed"),
    # bsa
    ("bsa", "fsi_bronze", "bronze_compliance_cases", None),
    ("bsa", "fsi_silver", "silver_compliance_cases", None),
    ("bsa", "fsi_gold", "gold_aml_risk_scoring", None),
    # ofac-screening
    ("ofac-screening", "fsi_bronze", "bronze_wire_transfers", "ofac_hold"),
    ("ofac-screening", "fsi_silver", "silver_wire_transfers", "ofac_hold"),
    ("ofac-screening", "fsi_gold", "gold_aml_risk_scoring", "sanctions_hit_count"),
    # basel-iii
    ("basel-iii", "fsi_gold", "gold_capital_adequacy", None),
    ("basel-iii", "fsi_gold", "gold_regulatory_dashboard", None),
    # cet1-ratio
    ("cet1-ratio", "fsi_bronze", "bronze_regulatory_capital", "capital_ratio"),
    ("cet1-ratio", "fsi_silver", "silver_regulatory_capital", "capital_ratio"),
    ("cet1-ratio", "fsi_gold", "gold_capital_adequacy", "capital_ratio"),
    ("cet1-ratio", "fsi_gold", "gold_capital_adequacy", "capital_component"),
    # dfast
    ("dfast", "fsi_bronze", "bronze_stress_tests", None),
    ("dfast", "fsi_gold", "gold_regulatory_dashboard", None),
    # call-report
    ("call-report", "fsi_bronze", "bronze_regulatory_filings", None),
    ("call-report", "fsi_silver", "silver_regulatory_filings", None),
    ("call-report", "fsi_staging", "staging_call_report_rc", None),
    ("call-report", "fsi_staging", "staging_call_report_ri", None),

    # =========================================================================
    # Financial Reporting
    # =========================================================================
    # net-interest-margin
    ("net-interest-margin", "fsi_gold", "gold_net_interest_margin", None),
    ("net-interest-margin", "fsi_gold", "gold_net_interest_margin", "avg_interest_rate"),
    # efficiency-ratio
    ("efficiency-ratio", "fsi_gold", "gold_branch_performance", None),
    # roaa
    ("roaa", "fsi_gold", "gold_balance_sheet_summary", None),
    # provision-for-credit-losses
    ("provision-for-credit-losses", "fsi_gold", "gold_delinquency_analysis", "classified_count"),
    # general-ledger
    ("general-ledger", "fsi_bronze", "bronze_gl_entries", None),
    ("general-ledger", "fsi_bronze", "bronze_gl_accounts", None),
    ("general-ledger", "fsi_silver", "silver_gl_entries", None),
    ("general-ledger", "fsi_silver", "silver_gl_accounts", None),
    ("general-ledger", "fsi_reference", "ref_gl_account_hierarchy", None),
    # risk-weighted-assets
    ("risk-weighted-assets", "fsi_bronze", "bronze_regulatory_capital", "risk_weighted_assets"),
    ("risk-weighted-assets", "fsi_silver", "silver_regulatory_capital", "risk_weighted_assets"),
    ("risk-weighted-assets", "fsi_gold", "gold_capital_adequacy", "risk_weighted_assets"),
    # allowance-for-credit-losses
    ("allowance-for-credit-losses", "fsi_gold", "gold_delinquency_analysis", None),

    # =========================================================================
    # Operations & Infrastructure
    # =========================================================================
    # branch
    ("branch", "fsi_bronze", "bronze_branches", None),
    ("branch", "fsi_silver", "silver_branches", None),
    ("branch", "fsi_gold", "gold_branch_performance", None),
    ("branch", "fsi_gold", "gold_customer_360", "home_branch_id"),
    ("branch", "fsi_gold", "gold_account_summary", "branch_id"),
    ("branch", "fsi_gold", "gold_net_interest_margin", "branch_id"),
    # core-banking-system
    ("core-banking-system", "fsi_bronze", "bronze_customers", "source_system"),
    # digital-channel
    ("digital-channel", "fsi_gold", "gold_transaction_patterns", "channel"),
    ("digital-channel", "fsi_bronze", "bronze_transactions", "channel"),
    ("digital-channel", "fsi_bronze", "bronze_atm_transactions", None),
]


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    pn = cfg["project_number"]
    multi = cfg["multi_region"]

    logger.info("Creating %d glossary-to-asset definition links", len(LINKS))

    created = 0
    skipped = 0
    failed = 0

    for term_id, dataset, table, column in LINKS:
        col_suffix = f"-{column.replace('_', '-')}" if column else ""
        link_id = f"def-{term_id}-{table.replace('_', '-')}{col_suffix}"
        if len(link_id) > 63:
            link_id = link_id[:63]

        table_entry = bq_table_entry(cfg, dataset, table)
        term_entry = glossary_term_entry(cfg, term_id)

        source_ref = {"name": table_entry, "type": "SOURCE"}
        if column:
            source_ref["path"] = f"Schema.{column}"

        body = {
            "entryLinkType": "projects/dataplex-types/locations/global/entryLinkTypes/definition",
            "entryReferences": [
                source_ref,
                {"name": term_entry, "type": "TARGET"},
            ],
        }

        url = (
            f"{DATAPLEX_URL}/projects/{pid}/locations/{multi}"
            f"/entryGroups/@bigquery/entryLinks?entryLinkId={link_id}"
        )
        try:
            result = api_call(url, "POST", body)
            if result.get("_exists"):
                skipped += 1
            else:
                created += 1
        except RuntimeError as e:
            if "already exists" in str(e).lower() or "409" in str(e):
                skipped += 1
            else:
                logger.warning("  Failed %s -> %s.%s: %s", term_id, table, column or "(table)", str(e)[:80])
                failed += 1
        time.sleep(0.5)

    logger.info("=" * 60)
    logger.info("GLOSSARY ASSET LINKS COMPLETE")
    logger.info("  Total: %d", len(LINKS))
    logger.info("  Created: %d", created)
    logger.info("  Already existed: %d", skipped)
    logger.info("  Failed: %d", failed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
