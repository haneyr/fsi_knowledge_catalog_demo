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
Creates data lineage: 3 source systems -> Bronze -> Silver -> Gold (80+ links).

Usage: python3 07_create_lineage.py
"""

import logging
import time

from common import (
    load_config, api_call, LINEAGE_URL,
    ORION_BRONZE, LUMEN_BRONZE, HELIOS_BRONZE, BRONZE_TABLES, SILVER_TABLES,
)

logger = logging.getLogger(__name__)


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    base = f"{LINEAGE_URL}/projects/{pid}/locations/{cfg['multi_region']}"

    def bq_fqn(ds, tbl):
        return f"bigquery:{pid}.{ds}.{tbl}"

    orion_src = {
        "CUSTOMERS": "db2:orion-prod.STORE_POS.CUSTOMERS",
        "ACCOUNTS": "db2:orion-prod.STORE_POS.ACCOUNTS",
        "TRANSACTIONS": "db2:orion-prod.STORE_POS.TRANSACTIONS",
        "BNPL_PLANS": "db2:orion-prod.STORE_POS.BNPL_PLANS",
        "BNPL_PAYMENTS": "db2:orion-prod.STORE_POS.BNPL_PAYMENTS",
        "CREDIT_CARDS": "db2:orion-prod.STORE_POS.CREDIT_CARDS",
        "CARD_TRANSACTIONS": "db2:orion-prod.STORE_POS.CARD_TRANSACTIONS",
        "FRAUD_ALERTS": "db2:orion-prod.STORE_POS.FRAUD_ALERTS",
        "KYC_RECORDS": "db2:orion-prod.STORE_POS.KYC_RECORDS",
        "STORES": "db2:orion-prod.STORE_POS.STORES",
        "EMPLOYEES": "db2:orion-prod.STORE_POS.EMPLOYEES",
        "WIRE_TRANSFERS": "db2:orion-prod.STORE_POS.WIRE_TRANSFERS",
        "ACH_TRANSFERS": "db2:orion-prod.STORE_POS.ACH_TRANSFERS",
        "ATM_TRANSACTIONS": "db2:orion-prod.STORE_POS.ATM_TRANSACTIONS",
    }

    lumen_src = {
        "WM_CLIENTS": "custom:lumen-prod.DIGITAL_COMMERCE.WM_CLIENTS",
        "MERCH_ASSORTMENTS": "custom:lumen-prod.DIGITAL_COMMERCE.MERCH_ASSORTMENTS",
        "HOLDINGS": "custom:lumen-prod.DIGITAL_COMMERCE.HOLDINGS",
        "TRADES": "custom:lumen-prod.DIGITAL_COMMERCE.TRADES",
        "PRODUCT_SKUS": "custom:lumen-prod.DIGITAL_COMMERCE.PRODUCT_SKUS",
        "ADVISORS": "custom:lumen-prod.DIGITAL_COMMERCE.ADVISORS",
        "PERFORMANCE": "custom:lumen-prod.DIGITAL_COMMERCE.PERFORMANCE",
        "FEE_SCHEDULES": "custom:lumen-prod.DIGITAL_COMMERCE.FEE_SCHEDULES",
        "BENCHMARKS": "custom:lumen-prod.DIGITAL_COMMERCE.BENCHMARKS",
        "CLIENT_GOALS": "custom:lumen-prod.DIGITAL_COMMERCE.CLIENT_GOALS",
        "RISK_PROFILES": "custom:lumen-prod.DIGITAL_COMMERCE.RISK_PROFILES",
        "DISTRIBUTIONS": "custom:lumen-prod.DIGITAL_COMMERCE.DISTRIBUTIONS",
        "CUSTODIAN_FEEDS": "custom:lumen-prod.DIGITAL_COMMERCE.CUSTODIAN_FEEDS",
    }

    helios_src = {
        "GL_ENTRIES": "custom:helios-prod.MERCH_FINANCE.GL_ENTRIES",
        "GL_ACCOUNTS": "custom:helios-prod.MERCH_FINANCE.GL_ACCOUNTS",
        "COST_CENTERS": "custom:helios-prod.MERCH_FINANCE.COST_CENTERS",
        "REGULATORY_CAPITAL": "custom:helios-prod.MERCH_FINANCE.REGULATORY_CAPITAL",
        "RISK_EXPOSURES": "custom:helios-prod.MERCH_FINANCE.RISK_EXPOSURES",
        "COUNTERPARTIES": "custom:helios-prod.MERCH_FINANCE.COUNTERPARTIES",
        "MARKET_DATA": "custom:helios-prod.MERCH_FINANCE.MARKET_DATA",
        "STRESS_TESTS": "custom:helios-prod.MERCH_FINANCE.STRESS_TESTS",
        "AUDIT_EVENTS": "custom:helios-prod.MERCH_FINANCE.AUDIT_EVENTS",
        "REGULATORY_FILINGS": "custom:helios-prod.MERCH_FINANCE.REGULATORY_FILINGS",
        "INTEREST_RATES": "custom:helios-prod.MERCH_FINANCE.INTEREST_RATES",
        "FX_RATES": "custom:helios-prod.MERCH_FINANCE.FX_RATES",
        "COMPLIANCE_CASES": "custom:helios-prod.MERCH_FINANCE.COMPLIANCE_CASES",
    }

    # Process 1: ORION -> Bronze
    logger.info("Process 1: IBM CDC (ORION -> Bronze)")
    p1 = api_call(f"{base}/processes", "POST", {"displayName": "IBM CDC Replication - ORION to BigQuery", "origin": {"sourceType": "CUSTOM", "name": "ibm-cdc-orion"}})
    r1 = api_call(f"{LINEAGE_URL}/{p1['name']}/runs", "POST", {"displayName": "ORION CDC", "startTime": "2026-04-30T00:00:00Z", "endTime": "2026-04-30T23:59:59Z", "state": "COMPLETED"})
    l1 = [{"source": {"fullyQualifiedName": fqn}, "target": {"fullyQualifiedName": bq_fqn("retail_bronze", f"bronze_{name.lower()}")}}
          for name, fqn in orion_src.items()]
    api_call(f"{LINEAGE_URL}/{r1['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T00:00:00Z", "endTime": "2026-04-30T23:59:59Z", "links": l1})
    logger.info("  %d links", len(l1))

    # Process 2: LUMEN -> Bronze
    logger.info("Process 2: Salesforce Extract API (LUMEN -> Bronze)")
    p2 = api_call(f"{base}/processes", "POST", {"displayName": "Salesforce Extract API - LUMEN to BigQuery", "origin": {"sourceType": "CUSTOM", "name": "salesforce-extract-lumen"}})
    r2 = api_call(f"{LINEAGE_URL}/{p2['name']}/runs", "POST", {"displayName": "LUMEN Extract", "startTime": "2026-04-30T01:00:00Z", "endTime": "2026-04-30T01:30:00Z", "state": "COMPLETED"})
    l2 = [{"source": {"fullyQualifiedName": fqn}, "target": {"fullyQualifiedName": bq_fqn("retail_bronze", f"bronze_{name.lower()}")}}
          for name, fqn in lumen_src.items()]
    api_call(f"{LINEAGE_URL}/{r2['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T01:00:00Z", "endTime": "2026-04-30T01:30:00Z", "links": l2})
    logger.info("  %d links", len(l2))

    # Process 3: HELIOS -> Bronze
    logger.info("Process 3: SAP SLT (HELIOS -> Bronze)")
    p3 = api_call(f"{base}/processes", "POST", {"displayName": "SAP SLT Replication - HELIOS to BigQuery", "origin": {"sourceType": "CUSTOM", "name": "sap-slt-helios"}})
    r3 = api_call(f"{LINEAGE_URL}/{p3['name']}/runs", "POST", {"displayName": "HELIOS SLT", "startTime": "2026-04-30T01:00:00Z", "endTime": "2026-04-30T01:45:00Z", "state": "COMPLETED"})
    l3 = [{"source": {"fullyQualifiedName": fqn}, "target": {"fullyQualifiedName": bq_fqn("retail_bronze", f"bronze_{name.lower()}")}}
          for name, fqn in helios_src.items()]
    api_call(f"{LINEAGE_URL}/{r3['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T01:00:00Z", "endTime": "2026-04-30T01:45:00Z", "links": l3})
    logger.info("  %d links", len(l3))

    # Process 4: Bronze -> Silver
    logger.info("Process 4: Bronze to Silver Transform")
    p4 = api_call(f"{base}/processes", "POST", {"displayName": "Retail Medallion - Bronze to Silver Transform", "origin": {"sourceType": "CUSTOM", "name": "retail-bronze-to-silver"}})
    r4 = api_call(f"{LINEAGE_URL}/{p4['name']}/runs", "POST", {"displayName": "Bronze to Silver", "startTime": "2026-04-30T02:00:00Z", "endTime": "2026-04-30T02:30:00Z", "state": "COMPLETED"})
    l4 = [{"source": {"fullyQualifiedName": bq_fqn(bds, btbl)}, "target": {"fullyQualifiedName": bq_fqn(sds, stbl)}}
          for (bds, btbl), (sds, stbl) in zip(BRONZE_TABLES, SILVER_TABLES)]
    api_call(f"{LINEAGE_URL}/{r4['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T02:00:00Z", "endTime": "2026-04-30T02:30:00Z", "links": l4})
    logger.info("  %d links", len(l4))

    # Process 5: Silver -> Gold
    logger.info("Process 5: Silver to Gold Aggregation")
    p5 = api_call(f"{base}/processes", "POST", {"displayName": "Retail Medallion - Silver to Gold Aggregation", "origin": {"sourceType": "CUSTOM", "name": "retail-silver-to-gold"}})
    r5 = api_call(f"{LINEAGE_URL}/{p5['name']}/runs", "POST", {"displayName": "Silver to Gold", "startTime": "2026-04-30T02:30:00Z", "endTime": "2026-04-30T02:45:00Z", "state": "COMPLETED"})
    gold_sources = {
        "gold_customer_360": ["customers", "accounts", "bnpl_plans", "credit_cards", "wm_clients"],
        "gold_loyalty_account_summary": ["accounts", "transactions"],
        "gold_bnpl_plan_summary": ["bnpl_plans"],
        "gold_bnpl_delinquency_analysis": ["bnpl_plans"],
        "gold_return_fraud_analytics": ["fraud_alerts"],
        "gold_promo_fraud_scoring": ["customers", "kyc_records", "compliance_cases", "wire_transfers"],
        "gold_store_performance": ["stores", "accounts", "bnpl_plans", "transactions"],
        "gold_assortment_performance": ["assortments", "performance", "holdings", "benchmarks"],
        "gold_vip_member_revenue": ["wm_clients", "fee_schedules", "assortments", "trades"],
        "gold_inventory_allocation": ["holdings"],
        "gold_category_manager_scorecard": ["advisors", "assortments", "performance", "trades"],
        "gold_promo_margin_impact": ["fee_schedules", "wm_clients"],
        "gold_gross_margin_analysis": ["accounts", "bnpl_plans"],
        "gold_working_capital_adequacy": ["regulatory_capital"],
        "gold_markdown_risk_var": ["holdings", "market_data"],
        "gold_compliance_dashboard": ["regulatory_capital", "kyc_records", "regulatory_filings"],
        "gold_financial_summary": ["accounts", "bnpl_plans", "holdings", "regulatory_capital"],
    }
    l5 = []
    for gold_tbl, silver_tbls in gold_sources.items():
        for st in silver_tbls:
            l5.append({"source": {"fullyQualifiedName": bq_fqn("retail_silver", f"silver_{st}")}, "target": {"fullyQualifiedName": bq_fqn("retail_gold", gold_tbl)}})
    api_call(f"{LINEAGE_URL}/{r5['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T02:30:00Z", "endTime": "2026-04-30T02:45:00Z", "links": l5})
    logger.info("  %d links", len(l5))

    total = len(l1) + len(l2) + len(l3) + len(l4) + len(l5)
    logger.info("Lineage complete: %d total links across 5 processes", total)


if __name__ == "__main__":
    main()
