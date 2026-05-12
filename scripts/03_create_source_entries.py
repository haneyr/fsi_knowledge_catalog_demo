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
Creates source system catalog entries for ATLAS (DB2), FORTUNA (Temenos),
and ARGUS (SAP) in Dataplex Knowledge Catalog.

Usage: python3 03_create_source_entries.py
"""

import logging
import time

from common import load_config, api_call, DATAPLEX_URL

logger = logging.getLogger(__name__)


def map_type(t):
    t = t.upper()
    if "INT" in t or "NUMBER" in t or "DECIMAL" in t: return "NUMBER"
    if "VARCHAR" in t or "CHAR" in t or "TEXT" in t: return "STRING"
    if t == "DATE": return "DATETIME"
    if "TIMESTAMP" in t: return "TIMESTAMP"
    return "OTHER"


SYSTEMS = [
    {
        "entry_group": "atlas-core-banking",
        "instance_id": "atlas-mainframe",
        "instance_type": "db2-instance",
        "schema_id": "atlas-core-schema",
        "schema_type": "db2-schema",
        "table_type": "db2-table",
        "platform": "IBM",
        "system": "DB2 for z/OS",
        "instance_name": "ATLAS_PROD",
        "instance_desc": "Production IBM DB2 z/OS v13.1 mainframe. 2-way LPAR, 128GB, DASD. IBM CDC replication to BigQuery.",
        "schema_name": "CORE_BANKING",
        "schema_desc": "Core banking schema: 14 CDC-replicated tables, ~100M+ rows.",
        "fqn_prefix": "db2:atlas-prod.CORE_BANKING",
        "resource_prefix": "//db2.meridianbank.internal/instances/ATLAS_PROD/schemas/CORE_BANKING",
        "tables": [
            ("customers-table", "CUSTOMERS", "Master customer file (500K rows)", [
                ("CUSTOMER_ID","VARCHAR(12)","REQUIRED","PK"),("FIRST_NAME","VARCHAR(100)","REQUIRED","First name"),("LAST_NAME","VARCHAR(100)","REQUIRED","Last name"),("DATE_OF_BIRTH","DATE","NULLABLE","DOB"),("SSN","VARCHAR(11)","REQUIRED","SSN (encrypted)"),("CUSTOMER_TYPE","VARCHAR(20)","REQUIRED","Individual/Joint/Trust/Business"),("KYC_RISK_RATING","VARCHAR(10)","NULLABLE","Low/Medium/High"),("HOME_BRANCH_ID","VARCHAR(10)","REQUIRED","Home branch"),
            ]),
            ("accounts-table", "ACCOUNTS", "Deposit accounts (1.2M rows)", [
                ("ACCOUNT_ID","VARCHAR(14)","REQUIRED","PK"),("CUSTOMER_ID","VARCHAR(12)","REQUIRED","FK"),("ACCOUNT_TYPE","VARCHAR(20)","REQUIRED","Type"),("CURRENT_BALANCE","DECIMAL(15,2)","REQUIRED","Balance"),("INTEREST_RATE","DECIMAL(8,4)","NULLABLE","Rate"),("BRANCH_ID","VARCHAR(10)","REQUIRED","Branch"),
            ]),
            ("transactions-table", "TRANSACTIONS", "Transaction journal (25M rows)", [
                ("TRANSACTION_ID","VARCHAR(16)","REQUIRED","PK"),("ACCOUNT_ID","VARCHAR(14)","REQUIRED","FK"),("TRANSACTION_TYPE","VARCHAR(20)","REQUIRED","Type"),("AMOUNT","DECIMAL(15,2)","REQUIRED","Amount"),("TRANSACTION_DATE","TIMESTAMP","REQUIRED","Date"),("CHANNEL","VARCHAR(10)","REQUIRED","Channel"),
            ]),
            ("loans-table", "LOANS", "Loan portfolio (300K rows)", [
                ("LOAN_ID","VARCHAR(12)","REQUIRED","PK"),("CUSTOMER_ID","VARCHAR(12)","REQUIRED","FK"),("LOAN_TYPE","VARCHAR(20)","REQUIRED","Type"),("ORIGINAL_AMOUNT","DECIMAL(15,2)","REQUIRED","Originated"),("CURRENT_BALANCE","DECIMAL(15,2)","REQUIRED","Outstanding"),("INTEREST_RATE","DECIMAL(8,4)","REQUIRED","Rate"),("FICO_SCORE","INT","NULLABLE","FICO at origination"),("RISK_RATING","VARCHAR(20)","REQUIRED","Pass/SM/Sub/Doubtful"),
            ]),
            ("credit-cards-table", "CREDIT_CARDS", "Card accounts (400K rows)", [
                ("CARD_ID","VARCHAR(12)","REQUIRED","PK"),("CUSTOMER_ID","VARCHAR(12)","REQUIRED","FK"),("CREDIT_LIMIT","DECIMAL(12,2)","REQUIRED","Limit"),("CURRENT_BALANCE","DECIMAL(12,2)","REQUIRED","Balance"),("APR","DECIMAL(8,4)","REQUIRED","APR"),
            ]),
        ],
    },
    {
        "entry_group": "fortuna-wealth-mgmt",
        "instance_id": "fortuna-t24",
        "instance_type": "temenos-instance",
        "schema_id": "fortuna-wealth-schema",
        "schema_type": "temenos-schema",
        "table_type": "temenos-table",
        "platform": "Temenos",
        "system": "T24 Transact",
        "instance_name": "FORTUNA_PROD",
        "instance_desc": "Production Temenos T24 R22. Wealth management platform. API extraction to BigQuery.",
        "schema_name": "WEALTH_MGMT",
        "schema_desc": "Wealth management module: 13 API-replicated tables.",
        "fqn_prefix": "temenos:fortuna-prod.WEALTH_MGMT",
        "resource_prefix": "//temenos.meridianbank.internal/instances/FORTUNA_PROD/schemas/WEALTH_MGMT",
        "tables": [
            ("wm-clients-table", "WM_CLIENTS", "HNW/UHNW clients (50K rows)", [
                ("WM_CLIENT_ID","VARCHAR(10)","REQUIRED","PK"),("FIRST_NAME","VARCHAR(100)","REQUIRED","First name"),("LAST_NAME","VARCHAR(100)","REQUIRED","Last name"),("CLIENT_TIER","VARCHAR(10)","REQUIRED","HNW/UHNW/Affluent"),("TOTAL_AUM","DECIMAL(15,2)","REQUIRED","AUM"),("RISK_TOLERANCE","VARCHAR(30)","REQUIRED","Risk profile"),("PRIMARY_ADVISOR_ID","VARCHAR(10)","REQUIRED","Advisor FK"),
            ]),
            ("portfolios-table", "PORTFOLIOS", "Investment portfolios (80K rows)", [
                ("PORTFOLIO_ID","VARCHAR(12)","REQUIRED","PK"),("WM_CLIENT_ID","VARCHAR(10)","REQUIRED","FK"),("MARKET_VALUE","DECIMAL(15,2)","REQUIRED","MV"),("COST_BASIS","DECIMAL(15,2)","REQUIRED","Cost"),("BENCHMARK_ID","VARCHAR(10)","NULLABLE","Benchmark"),("ADVISOR_ID","VARCHAR(10)","REQUIRED","Advisor"),
            ]),
            ("holdings-table", "HOLDINGS", "Security positions (500K rows)", [
                ("HOLDING_ID","VARCHAR(12)","REQUIRED","PK"),("PORTFOLIO_ID","VARCHAR(12)","REQUIRED","FK"),("SECURITY_ID","VARCHAR(10)","REQUIRED","FK"),("QUANTITY","DECIMAL(15,4)","REQUIRED","Shares/units"),("MARKET_VALUE","DECIMAL(15,2)","REQUIRED","MV"),("ASSET_CLASS","VARCHAR(30)","REQUIRED","Asset class"),("SECTOR","VARCHAR(30)","NULLABLE","Sector"),
            ]),
            ("securities-table", "SECURITIES", "Security master (50K rows)", [
                ("SECURITY_ID","VARCHAR(10)","REQUIRED","PK"),("CUSIP","VARCHAR(9)","NULLABLE","CUSIP"),("ISIN","VARCHAR(12)","NULLABLE","ISIN"),("TICKER","VARCHAR(10)","NULLABLE","Ticker"),("SECURITY_TYPE","VARCHAR(20)","REQUIRED","Type"),("ASSET_CLASS","VARCHAR(20)","REQUIRED","Asset class"),
            ]),
        ],
    },
    {
        "entry_group": "argus-finance-risk",
        "instance_id": "argus-s4hana",
        "instance_type": "sap-instance",
        "schema_id": "argus-finance-schema",
        "schema_type": "sap-schema",
        "table_type": "sap-table",
        "platform": "SAP",
        "system": "S/4HANA",
        "instance_name": "ARGUS_PROD",
        "instance_desc": "Production SAP S/4HANA 2023 FPS02. Finance and risk management. SLT replication to BigQuery.",
        "schema_name": "FINANCE_RISK",
        "schema_desc": "Finance and risk management schema: 13 SLT-replicated tables.",
        "fqn_prefix": "sap:argus-prod.FINANCE_RISK",
        "resource_prefix": "//sap.meridianbank.internal/instances/ARGUS_PROD/schemas/FINANCE_RISK",
        "tables": [
            ("gl-entries-table", "GL_ENTRIES", "General ledger entries (10M rows)", [
                ("GL_ENTRY_ID","VARCHAR(16)","REQUIRED","PK"),("GL_ACCOUNT_ID","VARCHAR(10)","REQUIRED","FK"),("POSTING_DATE","DATE","REQUIRED","Post date"),("ENTRY_TYPE","VARCHAR(10)","REQUIRED","Debit/Credit"),("AMOUNT","DECIMAL(15,2)","REQUIRED","Amount"),("FISCAL_YEAR","VARCHAR(6)","REQUIRED","FY"),
            ]),
            ("regulatory-capital-table", "REGULATORY_CAPITAL", "Basel III capital (1K rows)", [
                ("CAPITAL_ID","VARCHAR(10)","REQUIRED","PK"),("REPORTING_DATE","DATE","REQUIRED","Date"),("CAPITAL_COMPONENT","VARCHAR(30)","REQUIRED","CET1/T1/T2/Total"),("CAPITAL_AMOUNT","DECIMAL(18,0)","REQUIRED","Amount"),("RISK_WEIGHTED_ASSETS","DECIMAL(18,0)","REQUIRED","RWA"),("CAPITAL_RATIO","DECIMAL(8,4)","REQUIRED","Ratio"),
            ]),
            ("risk-exposures-table", "RISK_EXPOSURES", "Risk positions (100K rows)", [
                ("EXPOSURE_ID","VARCHAR(12)","REQUIRED","PK"),("RISK_TYPE","VARCHAR(20)","REQUIRED","Credit/Market/Op/Liquidity"),("COUNTERPARTY_ID","VARCHAR(10)","NULLABLE","FK"),("GROSS_EXPOSURE","DECIMAL(15,2)","REQUIRED","Gross"),("NET_EXPOSURE","DECIMAL(15,2)","REQUIRED","Net"),("PROBABILITY_OF_DEFAULT","DECIMAL(8,4)","NULLABLE","PD"),
            ]),
            ("counterparties-table", "COUNTERPARTIES", "Counterparty master (20K rows)", [
                ("COUNTERPARTY_ID","VARCHAR(10)","REQUIRED","PK"),("COUNTERPARTY_NAME","VARCHAR(200)","REQUIRED","Name"),("LEI","VARCHAR(20)","NULLABLE","LEI"),("INTERNAL_RATING","VARCHAR(5)","REQUIRED","Rating"),("TOTAL_EXPOSURE","DECIMAL(15,2)","REQUIRED","Exposure"),
            ]),
        ],
    },
]


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    loc = cfg.get("region", "us-central1")
    DP = DATAPLEX_URL

    for sys_cfg in SYSTEMS:
        EG = f"projects/{pid}/locations/{loc}/entryGroups/{sys_cfg['entry_group']}"
        ET = lambda t: f"projects/{pid}/locations/{loc}/entryTypes/{t}"

        logger.info("=== %s (%s) ===", sys_cfg["instance_name"], sys_cfg["system"])

        api_call(f"{DP}/{EG}/entries?entryId={sys_cfg['instance_id']}", "POST", {
            "entryType": ET(sys_cfg["instance_type"]),
            "fullyQualifiedName": f"{sys_cfg['fqn_prefix'].split('.')[0]}:{sys_cfg['instance_name'].lower()}",
            "entrySource": {"resource": f"{sys_cfg['resource_prefix'].rsplit('/', 2)[0]}", "displayName": sys_cfg["instance_name"], "description": sys_cfg["instance_desc"], "system": sys_cfg["system"], "platform": sys_cfg["platform"]},
            "aspects": {
                "dataplex-types.global.generic": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/generic", "data": {}},
                "dataplex-types.global.overview": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview", "data": {"content": f"<h2>{sys_cfg['instance_name']}</h2><p>{sys_cfg['instance_desc']}</p>"}},
            },
        })
        logger.info("  Instance: %s", sys_cfg["instance_id"])
        time.sleep(1)

        api_call(f"{DP}/{EG}/entries?entryId={sys_cfg['schema_id']}", "POST", {
            "entryType": ET(sys_cfg["schema_type"]),
            "parentEntry": f"{EG}/entries/{sys_cfg['instance_id']}",
            "fullyQualifiedName": sys_cfg["fqn_prefix"],
            "entrySource": {"resource": sys_cfg["resource_prefix"], "displayName": sys_cfg["schema_name"], "description": sys_cfg["schema_desc"], "system": sys_cfg["system"], "platform": sys_cfg["platform"]},
            "aspects": {
                "dataplex-types.global.generic": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/generic", "data": {}},
                "dataplex-types.global.overview": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview", "data": {"content": f"<h2>{sys_cfg['schema_name']}</h2><p>{sys_cfg['schema_desc']}</p>"}},
            },
        })
        logger.info("  Schema: %s", sys_cfg["schema_id"])
        time.sleep(1)

        for tid, name, desc, cols in sys_cfg["tables"]:
            fqn = f"{sys_cfg['fqn_prefix']}.{name}"
            schema_data = {"fields": [{"name": c[0], "dataType": c[1], "metadataType": map_type(c[1]), "mode": c[2], "description": c[3]} for c in cols]}
            result = api_call(f"{DP}/{EG}/entries?entryId={tid}", "POST", {
                "entryType": ET(sys_cfg["table_type"]),
                "parentEntry": f"{EG}/entries/{sys_cfg['schema_id']}",
                "fullyQualifiedName": fqn,
                "entrySource": {"resource": f"{sys_cfg['resource_prefix']}/tables/{name}", "displayName": name, "description": desc, "system": sys_cfg["system"], "platform": sys_cfg["platform"]},
                "aspects": {
                    "dataplex-types.global.generic": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/generic", "data": {}},
                    "dataplex-types.global.schema": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/schema", "data": schema_data},
                    "dataplex-types.global.overview": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview", "data": {"content": f"<h2>{name}</h2><p>{desc}</p>"}},
                },
            })
            status = "exists" if result.get("_exists") else "created"
            logger.info("  %s: %s (%d cols)", name, status, len(cols))
            time.sleep(0.5)

    total_tables = sum(len(s["tables"]) for s in SYSTEMS)
    logger.info("Source entries complete: %d systems, %d tables", len(SYSTEMS), total_tables)


if __name__ == "__main__":
    main()
