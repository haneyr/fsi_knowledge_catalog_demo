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
Creates 5 FSI data products with assets, documentation, and refresh-cadence contracts.

Usage: python3 05_create_data_products.py
"""

import logging
import time

from common import load_config, api_call, poll_operation, set_entry_aspect, DATAPLEX_URL

logger = logging.getLogger(__name__)


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    pn = cfg["project_number"]
    multi = cfg["multi_region"]
    owner = cfg.get("gcp_account_name", "admin@meridianbank.com")
    base = f"{DATAPLEX_URL}/projects/{pid}/locations/{multi}"

    PRODUCTS = [
        {
            "id": "fsi-customer-intelligence-360",
            "display_name": "Customer Intelligence 360",
            "description": "Unified customer view across retail banking and wealth management. Contains PII — access restricted under GLBA.",
            "assets": [
                ("retail-customers", "fsi_silver", "silver_customers"),
                ("wm-clients", "fsi_silver", "silver_wm_clients"),
                ("kyc-records", "fsi_silver", "silver_kyc_records"),
                ("customer-360", "fsi_gold", "gold_customer_360"),
                ("aml-risk", "fsi_gold", "gold_aml_risk_scoring"),
            ],
            "contract": {"frequency": "Daily", "refreshTime": "02:00 ET", "thresholdInMinutes": 30, "cronSchedule": "0 2 * * *"},
        },
        {
            "id": "fsi-lending-credit-risk",
            "display_name": "Lending & Credit Risk",
            "description": "Loan portfolio analytics, delinquency tracking, and credit risk metrics for the lending division.",
            "assets": [
                ("loans", "fsi_silver", "silver_loans"),
                ("loan-payments", "fsi_silver", "silver_loan_payments"),
                ("portfolio-summary", "fsi_gold", "gold_loan_portfolio_summary"),
                ("delinquency", "fsi_gold", "gold_delinquency_analysis"),
            ],
            "contract": {"frequency": "Daily", "refreshTime": "03:00 ET", "thresholdInMinutes": 60, "cronSchedule": "0 3 * * *"},
        },
        {
            "id": "fsi-wealth-management-analytics",
            "display_name": "Wealth Management Analytics",
            "description": "Portfolio performance, advisor scorecards, AUM trends, and fee revenue for the FORTUNA wealth platform.",
            "assets": [
                ("portfolios", "fsi_silver", "silver_portfolios"),
                ("holdings", "fsi_silver", "silver_holdings"),
                ("performance", "fsi_gold", "gold_portfolio_performance"),
                ("advisor-scorecard", "fsi_gold", "gold_advisor_scorecard"),
                ("client-revenue", "fsi_gold", "gold_client_revenue"),
                ("asset-allocation", "fsi_gold", "gold_asset_allocation"),
            ],
            "contract": {"frequency": "Daily", "refreshTime": "04:00 ET", "thresholdInMinutes": 60, "cronSchedule": "0 4 * * *"},
        },
        {
            "id": "fsi-regulatory-compliance",
            "display_name": "Regulatory & Compliance",
            "description": "BSA/AML monitoring, capital adequacy, stress testing, and regulatory filing data for the compliance team.",
            "assets": [
                ("fraud-analytics", "fsi_gold", "gold_fraud_analytics"),
                ("aml-scoring", "fsi_gold", "gold_aml_risk_scoring"),
                ("capital-adequacy", "fsi_gold", "gold_capital_adequacy"),
                ("regulatory-dashboard", "fsi_gold", "gold_regulatory_dashboard"),
            ],
            "contract": {"frequency": "Daily", "refreshTime": "06:00 ET", "thresholdInMinutes": 120, "cronSchedule": "0 6 * * 1-5"},
        },
        {
            "id": "fsi-financial-performance",
            "display_name": "Financial Performance",
            "description": "NIM, fee revenue, branch P&L, balance sheet, and operational metrics for executive reporting.",
            "assets": [
                ("nim", "fsi_gold", "gold_net_interest_margin"),
                ("fee-revenue", "fsi_gold", "gold_fee_revenue"),
                ("branch-perf", "fsi_gold", "gold_branch_performance"),
                ("balance-sheet", "fsi_gold", "gold_balance_sheet_summary"),
            ],
            "contract": {"frequency": "Monthly", "refreshTime": "00:00 ET", "thresholdInMinutes": 300, "cronSchedule": "0 0 5 * *"},
        },
    ]

    for product in PRODUCTS:
        logger.info("--- %s ---", product["id"])

        result = api_call(f"{base}/dataProducts?dataProductId={product['id']}", "POST", {
            "displayName": product["display_name"],
            "description": product["description"],
            "ownerEmails": [owner],
        })
        if result.get("_exists"):
            logger.info("  Product exists")
        else:
            if "name" in result and "operations" in result.get("name", ""):
                poll_operation(result["name"])
            logger.info("  Created product")
        time.sleep(3)

        for asset_id, dataset, table in product["assets"]:
            ar = api_call(f"{base}/dataProducts/{product['id']}/dataAssets?dataAssetId={asset_id}", "POST", {
                "resource": f"//bigquery.googleapis.com/projects/{pid}/datasets/{dataset}/tables/{table}"
            })
            if not ar.get("_exists"):
                if "name" in ar and "operations" in ar.get("name", ""):
                    poll_operation(ar["name"])
                logger.info("  Added asset: %s.%s", dataset, table)
            time.sleep(1)

        entry = f"projects/{pn}/locations/{multi}/entryGroups/@dataplex/entries/projects/{pn}/locations/{multi}/dataProducts/{product['id']}"
        try:
            set_entry_aspect(cfg, entry, "refresh-cadence", product["contract"], is_system=True)
            logger.info("  Contract set: %s", product["contract"]["frequency"])
        except RuntimeError as e:
            logger.warning("  Contract failed: %s", str(e)[:80])
        time.sleep(1)

    logger.info("Data products complete: %d products", len(PRODUCTS))


if __name__ == "__main__":
    main()
