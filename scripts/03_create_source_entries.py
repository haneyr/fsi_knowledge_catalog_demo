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
Creates source system catalog entries for ORION (DB2), LUMEN (Salesforce),
and HELIOS (SAP) in Knowledge Catalog.

Usage: python3 03_create_source_entries.py
"""

import logging
import time

from common import (
    load_config, api_call, DATAPLEX_URL,
    entry_group_location, entry_type_location,
)

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
        "entry_group": "retail-orion-store-pos",
        "instance_id": "orion-ibmi-pos",
        "instance_type": "retail-ibmi-instance",
        "schema_id": "orion-pos-schema",
        "schema_type": "retail-ibmi-schema",
        "table_type": "retail-ibmi-table",
        "platform": "IBM",
        "system": "NCR POS on IBM i",
        "instance_name": "ORION_PROD",
        "instance_desc": "Production IBM DB2 z/OS v13.1 mainframe. 2-way LPAR, 128GB, DASD. IBM CDC replication to BigQuery.",
        "schema_name": "STORE_POS",
        "schema_desc": "Core retail schema: 14 CDC-replicated tables, ~100M+ rows.",
        "fqn_prefix": "db2:orion-prod.STORE_POS",
        "resource_prefix": "//db2.northwindretail.internal/instances/ORION_PROD/schemas/STORE_POS",
        "tables": [
            ("customers-table", "CUSTOMERS", "Master customer file (500K rows)", [
                ("CUSTOMER_ID","VARCHAR(12)","REQUIRED","PK"),("FIRST_NAME","VARCHAR(100)","REQUIRED","First name"),("LAST_NAME","VARCHAR(100)","REQUIRED","Last name"),("DATE_OF_BIRTH","DATE","NULLABLE","DOB"),("Member-TIN","VARCHAR(11)","REQUIRED","Member-TIN (encrypted)"),("CUSTOMER_TYPE","VARCHAR(20)","REQUIRED","Individual/Joint/Trust/Business"),("KYC_RISK_RATING","VARCHAR(10)","NULLABLE","Low/Medium/High"),("PRIMARY_STORE_ID","VARCHAR(10)","REQUIRED","Home store"),
            ]),
            ("accounts-table", "ACCOUNTS", "Loyalty Credit accounts (1.2M rows)", [
                ("ACCOUNT_ID","VARCHAR(14)","REQUIRED","PK"),("CUSTOMER_ID","VARCHAR(12)","REQUIRED","FK"),("ACCOUNT_TYPE","VARCHAR(20)","REQUIRED","Type"),("CURRENT_BALANCE","DECIMAL(15,2)","REQUIRED","Balance"),("INTEREST_RATE","DECIMAL(8,4)","NULLABLE","Rate"),("STORE_ID","VARCHAR(10)","REQUIRED","Store"),
            ]),
            ("transactions-table", "TRANSACTIONS", "Transaction journal (25M rows)", [
                ("TRANSACTION_ID","VARCHAR(16)","REQUIRED","PK"),("ACCOUNT_ID","VARCHAR(14)","REQUIRED","FK"),("TRANSACTION_TYPE","VARCHAR(20)","REQUIRED","Type"),("AMOUNT","DECIMAL(15,2)","REQUIRED","Amount"),("TRANSACTION_DATE","TIMESTAMP","REQUIRED","Date"),("CHANNEL","VARCHAR(10)","REQUIRED","Channel"),
            ]),
            ("bnpl_plans-table", "BNPL_PLANS", "BNPL Plan assortment (300K rows)", [
                ("BNPL_PLAN_ID","VARCHAR(12)","REQUIRED","PK"),("CUSTOMER_ID","VARCHAR(12)","REQUIRED","FK"),("PLAN_TYPE","VARCHAR(20)","REQUIRED","Type"),("ORIGINAL_AMOUNT","DECIMAL(15,2)","REQUIRED","Originated"),("CURRENT_BALANCE","DECIMAL(15,2)","REQUIRED","Outstanding"),("INTEREST_RATE","DECIMAL(8,4)","REQUIRED","Rate"),("RETURN_RISK_SCORE","INT","NULLABLE","Return-Risk at origination"),("RISK_RATING","VARCHAR(20)","REQUIRED","Pass/SM/Sub/Doubtful"),
            ]),
            ("credit-cards-table", "CREDIT_CARDS", "Card accounts (400K rows)", [
                ("CARD_ID","VARCHAR(12)","REQUIRED","PK"),("CUSTOMER_ID","VARCHAR(12)","REQUIRED","FK"),("CREDIT_LIMIT","DECIMAL(12,2)","REQUIRED","Limit"),("CURRENT_BALANCE","DECIMAL(12,2)","REQUIRED","Balance"),("APR","DECIMAL(8,4)","REQUIRED","APR"),
            ]),
        ],
    },
    {
        "entry_group": "retail-lumen-commerce-loyalty",
        "instance_id": "lumen-sfcc",
        "instance_type": "retail-sfcc-instance",
        "schema_id": "lumen-commerce-schema",
        "schema_type": "retail-sfcc-schema",
        "table_type": "retail-sfcc-table",
        "platform": "Salesforce",
        "system": "Commerce Cloud",
        "instance_name": "LUMEN_PROD",
        "instance_desc": "[Retail] Production Salesforce Commerce Cloud. Digital Commerce & Loyalty platform. Commerce Export API to BigQuery.",
        "schema_name": "DIGITAL_COMMERCE",
        "schema_desc": "[Retail] Digital Commerce & Loyalty module: 13 API-replicated tables.",
        "fqn_prefix": "custom:lumen-prod.DIGITAL_COMMERCE",
        "resource_prefix": "//salesforce.northwindretail.internal/instances/LUMEN_PROD/schemas/DIGITAL_COMMERCE",
        "tables": [
            ("wm-clients-table", "WM_CLIENTS", "HNW/UHNW clients (50K rows)", [
                ("WM_CLIENT_ID","VARCHAR(10)","REQUIRED","PK"),("FIRST_NAME","VARCHAR(100)","REQUIRED","First name"),("LAST_NAME","VARCHAR(100)","REQUIRED","Last name"),("CLIENT_TIER","VARCHAR(10)","REQUIRED","HNW/UHNW/Affluent"),("TOTAL_AUM","DECIMAL(15,2)","REQUIRED","AUM"),("RISK_TOLERANCE","VARCHAR(30)","REQUIRED","Risk profile"),("PRIMARY_ADVISOR_ID","VARCHAR(10)","REQUIRED","Advisor FK"),
            ]),
            ("assortments-table", "MERCH_ASSORTMENTS", "Investment assortments (80K rows)", [
                ("ASSORTMENT_ID","VARCHAR(12)","REQUIRED","PK"),("WM_CLIENT_ID","VARCHAR(10)","REQUIRED","FK"),("MARKET_VALUE","DECIMAL(15,2)","REQUIRED","MV"),("COST_BASIS","DECIMAL(15,2)","REQUIRED","Cost"),("BENCHMARK_ID","VARCHAR(10)","NULLABLE","Benchmark"),("ADVISOR_ID","VARCHAR(10)","REQUIRED","Advisor"),
            ]),
            ("holdings-table", "HOLDINGS", "Security positions (500K rows)", [
                ("HOLDING_ID","VARCHAR(12)","REQUIRED","PK"),("ASSORTMENT_ID","VARCHAR(12)","REQUIRED","FK"),("SECURITY_ID","VARCHAR(10)","REQUIRED","FK"),("QUANTITY","DECIMAL(15,4)","REQUIRED","Shares/units"),("MARKET_VALUE","DECIMAL(15,2)","REQUIRED","MV"),("ASSET_CLASS","VARCHAR(30)","REQUIRED","Asset class"),("SECTOR","VARCHAR(30)","NULLABLE","Sector"),
            ]),
            ("product_skus-table", "PRODUCT_SKUS", "Security master (50K rows)", [
                ("SECURITY_ID","VARCHAR(10)","REQUIRED","PK"),("GTIN","VARCHAR(9)","NULLABLE","GTIN"),("SKU","VARCHAR(12)","NULLABLE","SKU"),("TICKER","VARCHAR(10)","NULLABLE","Ticker"),("SECURITY_TYPE","VARCHAR(20)","REQUIRED","Type"),("ASSET_CLASS","VARCHAR(20)","REQUIRED","Asset class"),
            ]),
        ],
    },
    {
        "entry_group": "retail-helios-merch-supply",
        "instance_id": "helios-s4retail",
        "instance_type": "retail-sap-instance",
        "schema_id": "helios-merch-schema",
        "schema_type": "retail-sap-schema",
        "table_type": "retail-sap-table",
        "platform": "SAP",
        "system": "S/4HANA",
        "instance_name": "HELIOS_PROD",
        "instance_desc": "[Retail] Production SAP S/4HANA Retail. Merchandising, Supply Chain & Finance. SAP SLT replication to BigQuery.",
        "schema_name": "MERCH_FINANCE",
        "schema_desc": "[Retail] Merchandising, Supply Chain & Finance schema: 13 SAP SLT-replicated tables.",
        "fqn_prefix": "custom:helios-prod.MERCH_FINANCE",
        "resource_prefix": "//sap.northwindretail.internal/instances/HELIOS_PROD/schemas/MERCH_FINANCE",
        "tables": [
            ("gl-entries-table", "GL_ENTRIES", "General ledger entries (10M rows)", [
                ("GL_ENTRY_ID","VARCHAR(16)","REQUIRED","PK"),("GL_ACCOUNT_ID","VARCHAR(10)","REQUIRED","FK"),("POSTING_DATE","DATE","REQUIRED","Post date"),("ENTRY_TYPE","VARCHAR(10)","REQUIRED","Debit/Credit"),("AMOUNT","DECIMAL(15,2)","REQUIRED","Amount"),("FISCAL_YEAR","VARCHAR(6)","REQUIRED","FY"),
            ]),
            ("regulatory-capital-table", "REGULATORY_CAPITAL", "PCI-DSS III capital (1K rows)", [
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
    eg_loc = entry_group_location(cfg)      # entry groups + entries: multi-region (#20)
    et_loc = entry_type_location(cfg)       # entryType references: global (#20)
    DP = DATAPLEX_URL

    for sys_cfg in SYSTEMS:
        EG = f"projects/{pid}/locations/{eg_loc}/entryGroups/{sys_cfg['entry_group']}"
        ET = lambda t: f"projects/{pid}/locations/{et_loc}/entryTypes/{t}"

        logger.info("=== %s (%s) ===", sys_cfg["instance_name"], sys_cfg["system"])

        api_call(f"{DP}/{EG}/entries?entryId={sys_cfg['instance_id']}", "POST", {
            "entryType": ET(sys_cfg["instance_type"]),
            "fullyQualifiedName": sys_cfg["fqn_prefix"].split(".")[0],
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
                "entrySource": {"resource": f"{sys_cfg['resource_prefix']}/tables/{name}", "displayName": name if name.startswith("[Retail]") else f"[Retail] {name}", "description": desc if desc.startswith("[Retail]") else f"[Retail] {desc}", "system": sys_cfg["system"], "platform": sys_cfg["platform"]},
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
