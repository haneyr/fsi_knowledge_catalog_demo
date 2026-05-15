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
    ATLAS_BRONZE, FORTUNA_BRONZE, ARGUS_BRONZE, BRONZE_TABLES, SILVER_TABLES,
)

logger = logging.getLogger(__name__)


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    base = f"{LINEAGE_URL}/projects/{pid}/locations/{cfg['multi_region']}"

    def bq_fqn(ds, tbl):
        return f"bigquery:{pid}.{ds}.{tbl}"

    atlas_src = {
        "CUSTOMERS": "db2:atlas-prod.CORE_BANKING.CUSTOMERS",
        "ACCOUNTS": "db2:atlas-prod.CORE_BANKING.ACCOUNTS",
        "TRANSACTIONS": "db2:atlas-prod.CORE_BANKING.TRANSACTIONS",
        "LOANS": "db2:atlas-prod.CORE_BANKING.LOANS",
        "LOAN_PAYMENTS": "db2:atlas-prod.CORE_BANKING.LOAN_PAYMENTS",
        "CREDIT_CARDS": "db2:atlas-prod.CORE_BANKING.CREDIT_CARDS",
        "CARD_TRANSACTIONS": "db2:atlas-prod.CORE_BANKING.CARD_TRANSACTIONS",
        "FRAUD_ALERTS": "db2:atlas-prod.CORE_BANKING.FRAUD_ALERTS",
        "KYC_RECORDS": "db2:atlas-prod.CORE_BANKING.KYC_RECORDS",
        "BRANCHES": "db2:atlas-prod.CORE_BANKING.BRANCHES",
        "EMPLOYEES": "db2:atlas-prod.CORE_BANKING.EMPLOYEES",
        "WIRE_TRANSFERS": "db2:atlas-prod.CORE_BANKING.WIRE_TRANSFERS",
        "ACH_TRANSFERS": "db2:atlas-prod.CORE_BANKING.ACH_TRANSFERS",
        "ATM_TRANSACTIONS": "db2:atlas-prod.CORE_BANKING.ATM_TRANSACTIONS",
    }

    fortuna_src = {
        "WM_CLIENTS": "oracle:fortuna-prod.WEALTH_MGMT.WM_CLIENTS",
        "PORTFOLIOS": "oracle:fortuna-prod.WEALTH_MGMT.PORTFOLIOS",
        "HOLDINGS": "oracle:fortuna-prod.WEALTH_MGMT.HOLDINGS",
        "TRADES": "oracle:fortuna-prod.WEALTH_MGMT.TRADES",
        "SECURITIES": "oracle:fortuna-prod.WEALTH_MGMT.SECURITIES",
        "ADVISORS": "oracle:fortuna-prod.WEALTH_MGMT.ADVISORS",
        "PERFORMANCE": "oracle:fortuna-prod.WEALTH_MGMT.PERFORMANCE",
        "FEE_SCHEDULES": "oracle:fortuna-prod.WEALTH_MGMT.FEE_SCHEDULES",
        "BENCHMARKS": "oracle:fortuna-prod.WEALTH_MGMT.BENCHMARKS",
        "CLIENT_GOALS": "oracle:fortuna-prod.WEALTH_MGMT.CLIENT_GOALS",
        "RISK_PROFILES": "oracle:fortuna-prod.WEALTH_MGMT.RISK_PROFILES",
        "DISTRIBUTIONS": "oracle:fortuna-prod.WEALTH_MGMT.DISTRIBUTIONS",
        "CUSTODIAN_FEEDS": "oracle:fortuna-prod.WEALTH_MGMT.CUSTODIAN_FEEDS",
    }

    argus_src = {
        "GL_ENTRIES": "oracle:argus-prod.FINANCE_RISK.GL_ENTRIES",
        "GL_ACCOUNTS": "oracle:argus-prod.FINANCE_RISK.GL_ACCOUNTS",
        "COST_CENTERS": "oracle:argus-prod.FINANCE_RISK.COST_CENTERS",
        "REGULATORY_CAPITAL": "oracle:argus-prod.FINANCE_RISK.REGULATORY_CAPITAL",
        "RISK_EXPOSURES": "oracle:argus-prod.FINANCE_RISK.RISK_EXPOSURES",
        "COUNTERPARTIES": "oracle:argus-prod.FINANCE_RISK.COUNTERPARTIES",
        "MARKET_DATA": "oracle:argus-prod.FINANCE_RISK.MARKET_DATA",
        "STRESS_TESTS": "oracle:argus-prod.FINANCE_RISK.STRESS_TESTS",
        "AUDIT_EVENTS": "oracle:argus-prod.FINANCE_RISK.AUDIT_EVENTS",
        "REGULATORY_FILINGS": "oracle:argus-prod.FINANCE_RISK.REGULATORY_FILINGS",
        "INTEREST_RATES": "oracle:argus-prod.FINANCE_RISK.INTEREST_RATES",
        "FX_RATES": "oracle:argus-prod.FINANCE_RISK.FX_RATES",
        "COMPLIANCE_CASES": "oracle:argus-prod.FINANCE_RISK.COMPLIANCE_CASES",
    }

    # Process 1: ATLAS -> Bronze
    logger.info("Process 1: IBM CDC (ATLAS -> Bronze)")
    p1 = api_call(f"{base}/processes", "POST", {"displayName": "IBM CDC Replication - ATLAS to BigQuery", "origin": {"sourceType": "CUSTOM", "name": "ibm-cdc-atlas"}})
    r1 = api_call(f"{LINEAGE_URL}/{p1['name']}/runs", "POST", {"displayName": "ATLAS CDC", "startTime": "2026-04-30T00:00:00Z", "endTime": "2026-04-30T23:59:59Z", "state": "COMPLETED"})
    l1 = [{"source": {"fullyQualifiedName": fqn}, "target": {"fullyQualifiedName": bq_fqn("fsi_bronze", f"bronze_{name.lower()}")}}
          for name, fqn in atlas_src.items()]
    api_call(f"{LINEAGE_URL}/{r1['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T00:00:00Z", "endTime": "2026-04-30T23:59:59Z", "links": l1})
    logger.info("  %d links", len(l1))

    # Process 2: FORTUNA -> Bronze
    logger.info("Process 2: Temenos Extract API (FORTUNA -> Bronze)")
    p2 = api_call(f"{base}/processes", "POST", {"displayName": "Temenos Extract API - FORTUNA to BigQuery", "origin": {"sourceType": "CUSTOM", "name": "temenos-extract-fortuna"}})
    r2 = api_call(f"{LINEAGE_URL}/{p2['name']}/runs", "POST", {"displayName": "FORTUNA Extract", "startTime": "2026-04-30T01:00:00Z", "endTime": "2026-04-30T01:30:00Z", "state": "COMPLETED"})
    l2 = [{"source": {"fullyQualifiedName": fqn}, "target": {"fullyQualifiedName": bq_fqn("fsi_bronze", f"bronze_{name.lower()}")}}
          for name, fqn in fortuna_src.items()]
    api_call(f"{LINEAGE_URL}/{r2['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T01:00:00Z", "endTime": "2026-04-30T01:30:00Z", "links": l2})
    logger.info("  %d links", len(l2))

    # Process 3: ARGUS -> Bronze
    logger.info("Process 3: SAP SLT (ARGUS -> Bronze)")
    p3 = api_call(f"{base}/processes", "POST", {"displayName": "SAP SLT Replication - ARGUS to BigQuery", "origin": {"sourceType": "CUSTOM", "name": "sap-slt-argus"}})
    r3 = api_call(f"{LINEAGE_URL}/{p3['name']}/runs", "POST", {"displayName": "ARGUS SLT", "startTime": "2026-04-30T01:00:00Z", "endTime": "2026-04-30T01:45:00Z", "state": "COMPLETED"})
    l3 = [{"source": {"fullyQualifiedName": fqn}, "target": {"fullyQualifiedName": bq_fqn("fsi_bronze", f"bronze_{name.lower()}")}}
          for name, fqn in argus_src.items()]
    api_call(f"{LINEAGE_URL}/{r3['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T01:00:00Z", "endTime": "2026-04-30T01:45:00Z", "links": l3})
    logger.info("  %d links", len(l3))

    # Process 4: Bronze -> Silver
    logger.info("Process 4: Bronze to Silver Transform")
    p4 = api_call(f"{base}/processes", "POST", {"displayName": "FSI Medallion - Bronze to Silver Transform", "origin": {"sourceType": "CUSTOM", "name": "fsi-bronze-to-silver"}})
    r4 = api_call(f"{LINEAGE_URL}/{p4['name']}/runs", "POST", {"displayName": "Bronze to Silver", "startTime": "2026-04-30T02:00:00Z", "endTime": "2026-04-30T02:30:00Z", "state": "COMPLETED"})
    l4 = [{"source": {"fullyQualifiedName": bq_fqn(bds, btbl)}, "target": {"fullyQualifiedName": bq_fqn(sds, stbl)}}
          for (bds, btbl), (sds, stbl) in zip(BRONZE_TABLES, SILVER_TABLES)]
    api_call(f"{LINEAGE_URL}/{r4['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T02:00:00Z", "endTime": "2026-04-30T02:30:00Z", "links": l4})
    logger.info("  %d links", len(l4))

    # Process 5: Silver -> Gold
    logger.info("Process 5: Silver to Gold Aggregation")
    p5 = api_call(f"{base}/processes", "POST", {"displayName": "FSI Medallion - Silver to Gold Aggregation", "origin": {"sourceType": "CUSTOM", "name": "fsi-silver-to-gold"}})
    r5 = api_call(f"{LINEAGE_URL}/{p5['name']}/runs", "POST", {"displayName": "Silver to Gold", "startTime": "2026-04-30T02:30:00Z", "endTime": "2026-04-30T02:45:00Z", "state": "COMPLETED"})
    gold_sources = {
        "gold_customer_360": ["customers", "accounts", "loans", "credit_cards", "wm_clients"],
        "gold_account_summary": ["accounts", "transactions"],
        "gold_loan_portfolio_summary": ["loans"],
        "gold_delinquency_analysis": ["loans"],
        "gold_fraud_analytics": ["fraud_alerts"],
        "gold_aml_risk_scoring": ["customers", "kyc_records", "compliance_cases", "wire_transfers"],
        "gold_branch_performance": ["branches", "accounts", "loans", "transactions"],
        "gold_portfolio_performance": ["portfolios", "performance", "holdings", "benchmarks"],
        "gold_client_revenue": ["wm_clients", "fee_schedules", "portfolios", "trades"],
        "gold_asset_allocation": ["holdings"],
        "gold_advisor_scorecard": ["advisors", "portfolios", "performance", "trades"],
        "gold_fee_revenue": ["fee_schedules", "wm_clients"],
        "gold_net_interest_margin": ["accounts", "loans"],
        "gold_capital_adequacy": ["regulatory_capital"],
        "gold_market_risk_var": ["holdings", "market_data"],
        "gold_regulatory_dashboard": ["regulatory_capital", "kyc_records", "regulatory_filings"],
        "gold_balance_sheet_summary": ["accounts", "loans", "holdings", "regulatory_capital"],
    }
    l5 = []
    for gold_tbl, silver_tbls in gold_sources.items():
        for st in silver_tbls:
            l5.append({"source": {"fullyQualifiedName": bq_fqn("fsi_silver", f"silver_{st}")}, "target": {"fullyQualifiedName": bq_fqn("fsi_gold", gold_tbl)}})
    api_call(f"{LINEAGE_URL}/{r5['name']}/lineageEvents", "POST", {"startTime": "2026-04-30T02:30:00Z", "endTime": "2026-04-30T02:45:00Z", "links": l5})
    logger.info("  %d links", len(l5))

    total = len(l1) + len(l2) + len(l3) + len(l4) + len(l5)
    logger.info("Lineage complete: %d total links across 5 processes", total)


if __name__ == "__main__":
    main()
