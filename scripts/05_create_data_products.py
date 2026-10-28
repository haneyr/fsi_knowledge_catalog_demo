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
Creates 5 Retail data products with assets, documentation, and refresh-cadence contracts.

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
    owner = cfg.get("gcp_account_name", "admin@northwindretail.com")
    base = f"{DATAPLEX_URL}/projects/{pid}/locations/{multi}"

    PRODUCTS = [
        {
            "id": "retail-customer-loyalty-360",
            "display_name": "[Retail] Customer & Loyalty 360",
            "description": "[Retail] Unified shopper profile across store POS (ORION) and digital commerce & loyalty (LUMEN). Contains PII and marketing consent — governed under CCPA/CPRA and GDPR.",
            "assets": [
                ("retail-customers", "retail_silver", "silver_customers"),
                ("vip-members", "retail_silver", "silver_vip_members"),
                ("privacy-consents", "retail_silver", "silver_privacy_consents"),
                ("customer-360", "retail_gold", "gold_customer_360"),
                ("promo-fraud-risk", "retail_gold", "gold_promo_fraud_scoring"),
            ],
            "contract": {"frequency": "Daily", "refreshTime": "02:00 ET", "thresholdInMinutes": 30, "cronSchedule": "0 2 * * *"},
        },
        {
            "id": "retail-pricing-promo-margin",
            "display_name": "[Retail] Pricing, Promotion & Margin",
            "description": "[Retail] Promotional discount impact, BNPL financing plans, return-risk scoring, and gross margin analysis across stores and e-commerce.",
            "assets": [
                ("bnpl-plans", "retail_silver", "silver_bnpl_plans"),
                ("bnpl-payments", "retail_silver", "silver_bnpl_payments"),
                ("bnpl-summary", "retail_gold", "gold_bnpl_plan_summary"),
                ("bnpl-delinquency", "retail_gold", "gold_bnpl_delinquency_analysis"),
            ],
            "contract": {"frequency": "Daily", "refreshTime": "03:00 ET", "thresholdInMinutes": 60, "cronSchedule": "0 3 * * *"},
        },
        {
            "id": "retail-merch-inventory",
            "display_name": "[Retail] Merchandising & Inventory",
            "description": "[Retail] Curated seasonal assortments, category manager scorecards, on-hand/in-transit inventory positions, and GMROI metrics from LUMEN and HELIOS.",
            "assets": [
                ("assortments", "retail_silver", "silver_merch_assortments"),
                ("inventory-positions", "retail_silver", "silver_inventory_positions"),
                ("assortment-perf", "retail_gold", "gold_assortment_performance"),
                ("category-scorecard", "retail_gold", "gold_category_manager_scorecard"),
                ("vip-revenue", "retail_gold", "gold_vip_member_revenue"),
                ("inventory-alloc", "retail_gold", "gold_inventory_allocation"),
            ],
            "contract": {"frequency": "Daily", "refreshTime": "04:00 ET", "thresholdInMinutes": 60, "cronSchedule": "0 4 * * *"},
        },
        {
            "id": "retail-privacy-consent-pci",
            "display_name": "[Retail] Privacy, Consent & PCI Compliance",
            "description": "[Retail] CCPA/CPRA consumer privacy consent, PCI-DSS payment card compliance, return/promo fraud analytics, and working capital governance.",
            "assets": [
                ("return-fraud", "retail_gold", "gold_return_fraud_analytics"),
                ("promo-fraud", "retail_gold", "gold_promo_fraud_scoring"),
                ("working-capital", "retail_gold", "gold_working_capital_adequacy"),
                ("compliance-dash", "retail_gold", "gold_compliance_dashboard"),
            ],
            "contract": {"frequency": "Daily", "refreshTime": "06:00 ET", "thresholdInMinutes": 120, "cronSchedule": "0 6 * * 1-5"},
        },
        {
            "id": "retail-store-channel-performance",
            "display_name": "[Retail] Store & Channel Performance",
            "description": "[Retail] Gross margin percentage, promotional fee impact, physical store P&L, omnichannel revenue, and retail balance sheet metrics for executive reporting.",
            "assets": [
                ("gross-margin", "retail_gold", "gold_gross_margin_analysis"),
                ("promo-margin", "retail_gold", "gold_promo_margin_impact"),
                ("store-perf", "retail_gold", "gold_store_performance"),
                ("financial-summary", "retail_gold", "gold_financial_summary"),
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
