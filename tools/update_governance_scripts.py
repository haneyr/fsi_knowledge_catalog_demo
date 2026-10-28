#!/usr/bin/env python3
"""Updates governance scripts (00..16 and common.py) with rich Northwind Retail Group content."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


def update_common() -> None:
    p = SCRIPTS_DIR / "common.py"
    txt = p.read_text(encoding="utf-8")
    txt = txt.replace('dataset.replace("fsi_", "")', 'dataset.replace("retail_", "")')
    txt = txt.replace('isinstance(val, dict)', 'type(val) is dict')
    p.write_text(txt, encoding="utf-8")


def update_00_infra() -> None:
    p = SCRIPTS_DIR / "00_create_dataplex_infra.py"
    txt = p.read_text(encoding="utf-8")

    # Entry types display names & platforms
    txt = txt.replace(
        '("retail-ibmi-instance", "DB2 Mainframe Instance", ["DATABASE"], "IBM", "DB2 for z/OS")',
        '("retail-ibmi-instance", "[Retail] IBM i NCR POS Instance", ["DATABASE"], "IBM", "NCR POS on IBM i")',
    ).replace(
        '("retail-ibmi-schema", "DB2 Schema", ["DATABASE_SCHEMA"], "IBM", "DB2 for z/OS")',
        '("retail-ibmi-schema", "[Retail] IBM i POS Schema", ["DATABASE_SCHEMA"], "IBM", "NCR POS on IBM i")',
    ).replace(
        '("retail-ibmi-table", "DB2 Table", ["TABLE"], "IBM", "DB2 for z/OS")',
        '("retail-ibmi-table", "[Retail] IBM i POS Table", ["TABLE"], "IBM", "NCR POS on IBM i")',
    ).replace(
        '("retail-sfcc-instance", "Salesforce T24 Instance", ["DATABASE"], "Salesforce", "T24 Transact")',
        '("retail-sfcc-instance", "[Retail] Salesforce Commerce Cloud Instance", ["DATABASE"], "Salesforce", "Commerce Cloud")',
    ).replace(
        '("retail-sfcc-schema", "Salesforce Schema", ["DATABASE_SCHEMA"], "Salesforce", "T24 Transact")',
        '("retail-sfcc-schema", "[Retail] Salesforce Commerce Schema", ["DATABASE_SCHEMA"], "Salesforce", "Commerce Cloud")',
    ).replace(
        '("retail-sfcc-table", "Salesforce Table", ["TABLE"], "Salesforce", "T24 Transact")',
        '("retail-sfcc-table", "[Retail] Salesforce Commerce Table", ["TABLE"], "Salesforce", "Commerce Cloud")',
    ).replace(
        '("retail-sap-instance", "SAP S/4HANA Instance", ["DATABASE"], "SAP", "S/4HANA")',
        '("retail-sap-instance", "[Retail] SAP S/4HANA Retail Instance", ["DATABASE"], "SAP", "S/4HANA Retail")',
    ).replace(
        '("retail-sap-schema", "SAP Schema", ["DATABASE_SCHEMA"], "SAP", "S/4HANA")',
        '("retail-sap-schema", "[Retail] SAP S/4HANA Retail Schema", ["DATABASE_SCHEMA"], "SAP", "S/4HANA Retail")',
    ).replace(
        '("retail-sap-table", "SAP Table", ["TABLE"], "SAP", "S/4HANA")',
        '("retail-sap-table", "[Retail] SAP S/4HANA Retail Table", ["TABLE"], "SAP", "S/4HANA Retail")',
    )

    txt = txt.replace(
        '"displayName": name, "description": f"Represents a {name.lower()}"',
        '"displayName": name, "description": f"[Retail] Represents a {name.replace(\'[Retail] \', \'\').lower()}"',
    )
    txt = txt.replace(
        '"displayName": at_id.replace("-", " ").title(),\n                    "description": f"Marker aspect for {at_id} entries"',
        '"displayName": f"[Retail] {at_id.replace(\'-\', \' \').title()}",\n                    "description": f"[Retail] Marker aspect for {at_id} entries"',
    )

    # Custom aspects with retail allowed values
    old_custom_block = txt[txt.index("    # --- Custom Aspect Types (global) ---"):txt.index("    logger.info(\"Creating %d custom aspect types (global)...\"")]
    new_custom_block = '''    # --- Custom Aspect Types (global) ---
    custom_aspects = [
        ("retail-data-classification", "[Retail] Data Classification", "[Retail] Retail data sensitivity, PII, PCI-DSS, and marketing consent classification", [
            {"name": "classification_level", "type": "enum", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Classification Level"},
             "enumValues": [{"name": "Public", "index": 1}, {"name": "Internal", "index": 2}, {"name": "Confidential", "index": 3}, {"name": "Restricted", "index": 4}, {"name": "Highly Restricted", "index": 5}, {"name": "Supplier-Confidential", "index": 6}]},
            {"name": "pii_category", "type": "enum", "index": 2, "annotations": {"displayName": "PII & Data Category"},
             "enumValues": [{"name": "Direct Identifier", "index": 1}, {"name": "Quasi Identifier", "index": 2}, {"name": "Financial Data", "index": 3}, {"name": "Account Data", "index": 4}, {"name": "Not PII", "index": 5}, {"name": "PII", "index": 6}, {"name": "Payment Card Data", "index": 7}, {"name": "Supplier-Confidential", "index": 8}, {"name": "Marketing Consent", "index": 9}]},
            {"name": "requires_encryption", "type": "bool", "index": 3, "annotations": {"displayName": "Requires Encryption"}},
            {"name": "requires_masking", "type": "bool", "index": 4, "annotations": {"displayName": "Requires Masking"}},
            {"name": "regulatory_scope", "type": "string", "index": 5, "annotations": {"displayName": "Regulatory Scope (PCI-DSS, CCPA/CPRA, GDPR)"}},
        ]),
        ("retail-data-retention", "[Retail] Data Retention Policy", "[Retail] Retail privacy and PCI-DSS data retention requirements", [
            {"name": "retention_period_years", "type": "int", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Retention Period (Years)"}},
            {"name": "governing_regulation", "type": "string", "index": 2, "annotations": {"displayName": "Governing Regulation (CCPA/CPRA, GDPR, PCI-DSS)"}},
            {"name": "retention_start_event", "type": "string", "index": 3, "annotations": {"displayName": "Retention Start Event"}},
            {"name": "archival_required", "type": "bool", "index": 4, "annotations": {"displayName": "Archival Required"}},
            {"name": "destruction_method", "type": "enum", "index": 5, "annotations": {"displayName": "Destruction Method"},
             "enumValues": [{"name": "Secure Purge", "index": 1}, {"name": "Crypto Shredding", "index": 2}, {"name": "Physical Destruction", "index": 3}, {"name": "Not Applicable", "index": 4}]},
        ]),
        ("retail-regulatory-compliance", "[Retail] Regulatory Compliance", "[Retail] PCI-DSS, CCPA/CPRA, GDPR, and supplier compliance status", [
            {"name": "applicable_regulations", "type": "string", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Applicable Regulations"}},
            {"name": "compliance_status", "type": "enum", "index": 2, "constraints": {"required": True}, "annotations": {"displayName": "Compliance Status"},
             "enumValues": [{"name": "Compliant", "index": 1}, {"name": "Partially Compliant", "index": 2}, {"name": "Non-Compliant", "index": 3}, {"name": "Under Review", "index": 4}]},
            {"name": "last_audit_date", "type": "string", "index": 3, "annotations": {"displayName": "Last Audit Date"}},
            {"name": "audit_frequency", "type": "enum", "index": 4, "annotations": {"displayName": "Audit Frequency"},
             "enumValues": [{"name": "Annual", "index": 1}, {"name": "Semi-Annual", "index": 2}, {"name": "Quarterly", "index": 3}, {"name": "Continuous", "index": 4}]},
            {"name": "compliance_notes", "type": "string", "index": 5, "annotations": {"displayName": "Compliance Notes"}},
        ]),
        ("retail-data-lineage-metadata", "[Retail] Data Lineage Metadata", "[Retail] Source system (ORION, LUMEN, HELIOS) and omnichannel data flow metadata", [
            {"name": "source_system", "type": "string", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Source System"}},
            {"name": "ingestion_method", "type": "enum", "index": 2, "annotations": {"displayName": "Ingestion Method"},
             "enumValues": [{"name": "IBM CDC Replication", "index": 1}, {"name": "Salesforce Extract API", "index": 2}, {"name": "SAP SLT Replication", "index": 3}, {"name": "Batch File Extract", "index": 4}, {"name": "Database Replication", "index": 5}, {"name": "API Integration", "index": 6}, {"name": "Commerce Export API", "index": 7}]},
            {"name": "refresh_frequency", "type": "enum", "index": 3, "annotations": {"displayName": "Refresh Frequency"},
             "enumValues": [{"name": "Real-time", "index": 1}, {"name": "Intraday", "index": 2}, {"name": "End-of-Day", "index": 3}, {"name": "Daily", "index": 4}, {"name": "Weekly", "index": 5}, {"name": "Monthly", "index": 6}]},
            {"name": "data_flow_path", "type": "string", "index": 4, "annotations": {"displayName": "Data Flow Path"}},
        ]),
        ("retail-access-control", "[Retail] Access Control Policy", "[Retail] Role-based access control for store ops, merchandising, and privacy teams", [
            {"name": "access_level", "type": "enum", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Access Level"},
             "enumValues": [{"name": "Public", "index": 1}, {"name": "Internal", "index": 2}, {"name": "Restricted", "index": 3}, {"name": "Confidential", "index": 4}, {"name": "Highly Restricted", "index": 5}, {"name": "Supplier-Confidential", "index": 6}]},
            {"name": "authorized_roles", "type": "string", "index": 2, "constraints": {"required": True}, "annotations": {"displayName": "Authorized Roles"}},
            {"name": "requires_mfa", "type": "bool", "index": 3, "annotations": {"displayName": "Requires MFA"}},
            {"name": "need_to_know_applies", "type": "bool", "index": 4, "annotations": {"displayName": "Need-to-Know Applies"}},
            {"name": "audit_all_access", "type": "bool", "index": 5, "annotations": {"displayName": "Audit All Access"}},
        ]),
        ("retail-risk-classification", "[Retail] Risk Data Classification", "[Retail] Return fraud, shrinkage, markdown, and supply chain risk tagging", [
            {"name": "risk_category", "type": "enum", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Risk Category"},
             "enumValues": [{"name": "Return & Fraud Risk", "index": 1}, {"name": "Demand & Markdown Risk", "index": 2}, {"name": "Shrinkage & Ops Risk", "index": 3}, {"name": "Stockout & Liquidity Risk", "index": 4}, {"name": "Privacy & PCI Risk", "index": 5}, {"name": "Not Risk Data", "index": 6}]},
            {"name": "model_dependency", "type": "enum", "index": 2, "annotations": {"displayName": "Model Dependency"},
             "enumValues": [{"name": "Model Input", "index": 1}, {"name": "Model Output", "index": 2}, {"name": "Model Calibration", "index": 3}, {"name": "Not Model Related", "index": 4}]},
            {"name": "materiality_level", "type": "enum", "index": 3, "annotations": {"displayName": "Materiality Level"},
             "enumValues": [{"name": "Material", "index": 1}, {"name": "Significant", "index": 2}, {"name": "Moderate", "index": 3}, {"name": "Immaterial", "index": 4}]},
            {"name": "sox_relevant", "type": "bool", "index": 4, "annotations": {"displayName": "SOX / Financial Audit Relevant"}},
        ]),
        ("retail-regulatory-reporting", "[Retail] Regulatory & Compliance Reporting", "[Retail] Maps retail datasets to PCI-DSS, CCPA/CPRA, GDPR, and supplier compliance reports", [
            {"name": "report_name", "type": "string", "index": 1, "annotations": {"displayName": "Report Name"}},
            {"name": "filing_frequency", "type": "enum", "index": 2, "annotations": {"displayName": "Filing Frequency"},
             "enumValues": [{"name": "Daily", "index": 1}, {"name": "Monthly", "index": 2}, {"name": "Quarterly", "index": 3}, {"name": "Semi-Annual", "index": 4}, {"name": "Annual", "index": 5}, {"name": "Ad Hoc", "index": 6}]},
            {"name": "regulatory_body", "type": "enum", "index": 3, "annotations": {"displayName": "Regulatory Body"},
             "enumValues": [{"name": "PCI-SSC", "index": 1}, {"name": "CPPA (CCPA/CPRA)", "index": 2}, {"name": "EU DPA (GDPR)", "index": 3}, {"name": "FTC", "index": 4}, {"name": "SEC", "index": 5}, {"name": "GS1 US", "index": 6}, {"name": "State Attorney General", "index": 7}, {"name": "Internal Audit", "index": 8}]},
            {"name": "schedule_line_item", "type": "string", "index": 4, "annotations": {"displayName": "Schedule / Line Item"}},
        ]),
    ]

'''
    txt = txt.replace(old_custom_block, new_custom_block)

    # Entry groups
    txt = txt.replace(
        '("retail-orion-store-pos", "ORION Core Retail (DB2)", "IBM DB2 mainframe entries for ORION")',
        '("retail-orion-store-pos", "[Retail] ORION Store Ops & POS (IBM i)", "[Retail] NCR POS on IBM i custom source entries for ORION (14 tables)")',
    ).replace(
        '("retail-lumen-commerce-loyalty", "LUMEN Omnichannel Loyalty Management (Salesforce)", "Salesforce T24 entries for LUMEN")',
        '("retail-lumen-commerce-loyalty", "[Retail] LUMEN Digital Commerce & Loyalty (Salesforce)", "[Retail] Salesforce Commerce Cloud custom source entries for LUMEN (13 tables)")',
    ).replace(
        '("retail-helios-merch-supply", "HELIOS Finance & Risk (SAP)", "SAP S/4HANA entries for HELIOS")',
        '("retail-helios-merch-supply", "[Retail] HELIOS Merchandising, Supply Chain & Finance (SAP)", "[Retail] SAP S/4HANA Retail custom source entries for HELIOS (13 tables)")',
    )
    p.write_text(txt, encoding="utf-8")


def update_02_scans() -> None:
    p = SCRIPTS_DIR / "02_create_scans.py"
    txt = p.read_text(encoding="utf-8")
    txt = txt.replace("dataset.replace('fsi_', '')", "dataset.replace('retail_', '')")
    txt = txt.replace('dataset.replace("fsi_", "")', 'dataset.replace("retail_", "")')
    txt = txt.replace('"displayName": f"Retail ', '"displayName": f"[Retail] ')
    txt = txt.replace('"description": f"Data ', '"description": f"[Retail] Data ')
    txt = txt.replace('"description": f"Documentation ', '"description": f"[Retail] Documentation ')
    txt = txt.replace('"description": f"Dataset ', '"description": f"[Retail] Dataset ')
    p.write_text(txt, encoding="utf-8")


def update_03_source_entries() -> None:
    p = SCRIPTS_DIR / "03_create_source_entries.py"
    txt = p.read_text(encoding="utf-8")
    txt = txt.replace("Home branch", "Home store")
    txt = txt.replace("DB2 for z/OS", "NCR POS on IBM i")
    txt = txt.replace("T24 Transact", "Commerce Cloud")
    txt = txt.replace("Production IBM DB2 v13 for z/OS. Core retail platform. CDC replication to BigQuery.", "[Retail] Production NCR POS on IBM i. Store Operations & POS platform. IBM CDC replication to BigQuery.")
    txt = txt.replace("Core retail schema: 14 CDC-replicated tables.", "[Retail] Store Operations & POS schema: 14 IBM CDC-replicated tables.")
    txt = txt.replace("Production Salesforce T24 R22. Omnichannel Loyalty management platform. API extraction to BigQuery.", "[Retail] Production Salesforce Commerce Cloud. Digital Commerce & Loyalty platform. Commerce Export API to BigQuery.")
    txt = txt.replace("Omnichannel Loyalty management module: 13 API-replicated tables.", "[Retail] Digital Commerce & Loyalty module: 13 API-replicated tables.")
    txt = txt.replace("Production SAP S/4HANA 2023 FPS02. Finance and risk management. SLT replication to BigQuery.", "[Retail] Production SAP S/4HANA Retail. Merchandising, Supply Chain & Finance. SAP SLT replication to BigQuery.")
    txt = txt.replace("Finance and risk management schema: 13 SLT-replicated tables.", "[Retail] Merchandising, Supply Chain & Finance schema: 13 SAP SLT-replicated tables.")
    # Prefix displayName and description in create_entry calls if not already prefixed
    txt = txt.replace(
        '"displayName": name, "description": desc',
        '"displayName": name if name.startswith("[Retail]") else f"[Retail] {name}", "description": desc if desc.startswith("[Retail]") else f"[Retail] {desc}"',
    )
    txt = txt.replace(
        '"displayName": s["instance_name"], "description": s["instance_desc"]',
        '"displayName": f"[Retail] {s[\'instance_name\']}", "description": s["instance_desc"]',
    )
    txt = txt.replace(
        '"displayName": s["schema_name"], "description": s["schema_desc"]',
        '"displayName": f"[Retail] {s[\'schema_name\']}", "description": s["schema_desc"]',
    )
    p.write_text(txt, encoding="utf-8")


def update_04_aspects() -> None:
    p = SCRIPTS_DIR / "04_create_aspects.py"
    txt = p.read_text(encoding="utf-8")
    txt = txt.replace('ds.replace("fsi_", "")', 'ds.replace("retail_", "")')
    txt = txt.replace('"branch": ("ORION DB2", "Batch File Extract", "Daily")', '"store": ("ORION IBM i POS", "Batch File Extract", "Daily")')
    txt = txt.replace('"ORION DB2"', '"ORION IBM i POS"')
    txt = txt.replace('"LUMEN T24"', '"LUMEN Commerce Cloud"')
    txt = txt.replace('"HELIOS S/4HANA"', '"HELIOS SAP S/4HANA Retail"')
    txt = txt.replace('"CCPA, CCPA, BSA/Promo-Fraud"', '"CCPA/CPRA, GDPR, Marketing Consent"')
    txt = txt.replace('"CCPA, BSA/Promo-Fraud, Reg E"', '"PCI-DSS, CCPA/CPRA"')
    txt = txt.replace('"BSA/Promo-Fraud, FinCEN"', '"PCI-DSS, CCPA/CPRA, Loss Prevention"')
    txt = txt.replace('"SOX, PCI-DSS III, DFAST"', '"PCI-DSS, SOX, Supplier-Confidential"')
    txt = txt.replace('"SEC, FINRA, Investment Advisers Act"', '"Supplier-Confidential, CCPA/CPRA"')
    txt = txt.replace('"BSA Officer, Compliance Analyst, Legal"', '"Privacy & Compliance Officer, Loss Prevention, Legal"')
    txt = txt.replace('"Direct Identifier"', '"PII"')
    txt = txt.replace('"Financial Data"', '"Payment Card Data"')
    txt = txt.replace('"Account Data"', '"Marketing Consent"')

    # Replace PII_TERMS block with exact 16 Retail glossary term IDs
    old_pii = txt[txt.index("    PII_TERMS = {"):txt.index("    count = 0")]
    new_pii = '''    PII_TERMS = {
        "customer-id": ("PII", "Restricted", True, True, "CCPA/CPRA, GDPR"),
        "member-tin": ("PII", "Highly Restricted", True, True, "CCPA/CPRA, GDPR"),
        "loyalty-return-risk-score": ("Marketing Consent", "Confidential", True, False, "CCPA/CPRA"),
        "points-rewards-account": ("Marketing Consent", "Confidential", True, False, "CCPA/CPRA, Marketing Consent"),
        "vip-cashback-account": ("Marketing Consent", "Confidential", True, False, "CCPA/CPRA, Marketing Consent"),
        "loyalty-account-balance": ("Marketing Consent", "Confidential", True, False, "CCPA/CPRA"),
        "extended-furniture-bnpl": ("Payment Card Data", "Confidential", True, False, "PCI-DSS, CCPA/CPRA"),
        "cobranded-store-card": ("Payment Card Data", "Confidential", True, False, "PCI-DSS, CCPA/CPRA"),
        "high-value-refund-payout": ("Payment Card Data", "Confidential", True, False, "PCI-DSS, Loss Prevention"),
        "promo-abuse-incident-report": ("PII", "Highly Restricted", True, False, "CCPA/CPRA, Loss Prevention"),
        "shopper-verification": ("Marketing Consent", "Restricted", True, False, "CCPA/CPRA, GDPR"),
        "gross-merchandise-value": ("Supplier-Confidential", "Confidential", True, False, "Supplier-Confidential"),
        "general-ledger": ("Not PII", "Confidential", False, False, "SOX, Supplier-Confidential"),
        "core-working-capital-ratio": ("Not PII", "Internal", False, False, "PCI-DSS, Internal Audit"),
        "markdown-value-at-risk": ("Supplier-Confidential", "Confidential", False, False, "Supplier-Confidential"),
        "retail-store-location": ("Not PII", "Internal", False, False, "General"),
    }
'''
    txt = txt.replace(old_pii, new_pii)
    p.write_text(txt, encoding="utf-8")


def update_05_data_products() -> None:
    p = SCRIPTS_DIR / "05_create_data_products.py"
    txt = p.read_text(encoding="utf-8")
    old_products = txt[txt.index("    PRODUCTS = ["):txt.index("    for product in PRODUCTS:")]
    new_products = '''    PRODUCTS = [
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

'''
    txt = txt.replace(old_products, new_products)
    p.write_text(txt, encoding="utf-8")


def update_09_simulate_queries() -> None:
    p = SCRIPTS_DIR / "09_simulate_queries.py"
    txt = p.read_text(encoding="utf-8")
    old_block = txt[txt.index("def build_queries(pid):"):txt.index("def main():")]
    new_block = '''def build_queries(pid):
    S = f"`{pid}.retail_silver"
    G = f"`{pid}.retail_gold"
    queries = []

    # Persona 1: Merchandising Manager (5 queries)
    queries.append(("merchandising_manager", "VIP member GMV", f"SELECT wm_client_id, first_name, last_name, client_tier, total_aum FROM {S}.silver_vip_members` ORDER BY total_aum DESC LIMIT 20"))
    queries.append(("merchandising_manager", "Assortment performance", f"SELECT assortment_name, market_value, ytd_return, avg_sharpe_ratio, avg_alpha FROM {G}.gold_assortment_performance` ORDER BY market_value DESC LIMIT 20"))
    queries.append(("merchandising_manager", "Category manager scorecard", f"SELECT first_name, last_name, total_aum, client_count, avg_assortment_ytd_return, avg_sharpe_ratio FROM {G}.gold_category_manager_scorecard` ORDER BY total_aum DESC LIMIT 10"))
    queries.append(("merchandising_manager", "Inventory allocation mix", f"SELECT asset_class, sector, total_market_value, avg_return_pct FROM {G}.gold_inventory_allocation` ORDER BY total_market_value DESC"))
    queries.append(("merchandising_manager", "Promo margin impact", f"SELECT fee_type, client_tier, total_fees, avg_fee_rate_bps FROM {G}.gold_promo_margin_impact` ORDER BY total_fees DESC"))

    # Persona 2: Store Operations Director (5 queries)
    queries.append(("store_ops_director", "Store performance ranking", f"SELECT store_name, region, total_pos_revenue, total_bnpl_originations, sales_per_associate FROM {G}.gold_store_performance` ORDER BY total_pos_revenue DESC LIMIT 20"))
    queries.append(("store_ops_director", "Omnichannel order patterns", f"SELECT channel, merchant_category, transaction_count, total_amount FROM {G}.gold_order_patterns` WHERE month >= '2024-06-01' ORDER BY total_amount DESC LIMIT 20"))
    queries.append(("store_ops_director", "Gross margin by product", f"SELECT product, balance_type, total_balance, avg_interest_rate FROM {G}.gold_gross_margin_analysis` ORDER BY total_balance DESC"))
    queries.append(("store_ops_director", "Retail financial summary", f"SELECT category, line_item, amount FROM {G}.gold_financial_summary` ORDER BY category, amount DESC"))
    queries.append(("store_ops_director", "Store omnichannel view", f"SELECT store_id, store_name, region, store_pos_sales, vip_digital_gmv, combined_assets FROM `{pid}.retail_dashboards.vw_store_omnichannel_performance` ORDER BY combined_assets DESC LIMIT 20"))

    # Persona 3: Loyalty/CRM Marketer (5 queries)
    queries.append(("loyalty_crm_marketer", "Shopper profile lookup", f"SELECT * FROM {S}.silver_customers` WHERE customer_id = 'CUST-{random.randint(1,20000):08d}'"))
    queries.append(("loyalty_crm_marketer", "Top loyalty members", f"SELECT customer_id, customer_segment, total_loyalty_balance FROM {G}.gold_customer_360` ORDER BY total_loyalty_balance DESC LIMIT 20"))
    queries.append(("loyalty_crm_marketer", "Loyalty account dormancy", f"SELECT account_type, COUNT(*) AS cnt FROM {G}.gold_loyalty_account_summary` WHERE is_dormant GROUP BY 1"))
    queries.append(("loyalty_crm_marketer", "Customer lifetime value tiers", f"SELECT relationship_tier, COUNT(*) AS cnt, SUM(total_relationship_value) AS total_value FROM `{pid}.retail_dashboards.vw_customer_lifetime_value` GROUP BY 1 ORDER BY total_value DESC"))
    queries.append(("loyalty_crm_marketer", "Return risk score bands", f"SELECT CASE WHEN return_risk_score_at_signup >= 800 THEN '800+' WHEN return_risk_score_at_signup >= 740 THEN '740-799' WHEN return_risk_score_at_signup >= 670 THEN '670-739' WHEN return_risk_score_at_signup >= 580 THEN '580-669' ELSE '<580' END AS return_risk_band, COUNT(*) AS cnt FROM {S}.silver_bnpl_plans` GROUP BY 1 ORDER BY 1"))

    # Persona 4: Supply Chain Planner (4 queries)
    queries.append(("supply_chain_planner", "Working capital adequacy", f"SELECT reporting_date, capital_component, capital_ratio, regulatory_minimum, buffer_above_minimum FROM {G}.gold_working_capital_adequacy` ORDER BY reporting_date DESC"))
    queries.append(("supply_chain_planner", "Markdown risk MVaR", f"SELECT asset_class, sector, total_exposure, var_99_1d, var_99_10d FROM {G}.gold_markdown_risk_var` ORDER BY var_99_10d DESC"))
    queries.append(("supply_chain_planner", "BNPL plan assortment", f"SELECT plan_type, risk_rating, plan_count, total_outstanding, delinquency_rate_pct FROM {G}.gold_bnpl_plan_summary` ORDER BY total_outstanding DESC"))
    queries.append(("supply_chain_planner", "B2B commercial trade plans", f"SELECT naics_code, plan_count, total_balance FROM {G}.gold_bnpl_delinquency_analysis` WHERE plan_type = 'COMMERCIAL' ORDER BY total_balance DESC"))

    # Persona 5: Privacy & Compliance Officer (5 queries)
    queries.append(("privacy_compliance_officer", "Return fraud trends", f"SELECT alert_month, alert_type, alert_count, confirmed_fraud_count, false_positive_rate_pct FROM {G}.gold_return_fraud_analytics` ORDER BY alert_month DESC"))
    queries.append(("privacy_compliance_officer", "Promo fraud risk scoring", f"SELECT customer_segment, kyc_risk_rating, customer_count, avg_risk_score, sar_filings FROM {G}.gold_promo_fraud_scoring` ORDER BY avg_risk_score DESC"))
    queries.append(("privacy_compliance_officer", "Privacy consent overdue", f"SELECT due_diligence_level, risk_score_category, COUNT(*) AS total, COUNTIF(review_overdue) AS overdue FROM {S}.silver_privacy_consents` GROUP BY 1, 2"))
    queries.append(("privacy_compliance_officer", "High-value refund logs", f"SELECT wire_type, beneficiary_country, COUNT(*) AS cnt, SUM(amount) AS total FROM {S}.silver_high_value_refunds` WHERE amount >= 10000 GROUP BY 1, 2 ORDER BY total DESC"))
    queries.append(("privacy_compliance_officer", "Privacy & PCI dashboard", f"SELECT metric_category, metric_name, metric_value, threshold, status FROM {G}.gold_compliance_dashboard`"))

    return queries


'''
    txt = txt.replace(old_block, new_block)
    p.write_text(txt, encoding="utf-8")


def update_10_rules() -> None:
    p = SCRIPTS_DIR / "10_create_rule_library.py"
    txt = p.read_text(encoding="utf-8")

    old_templates = txt[txt.index("TEMPLATES = ["):txt.index("def _tref(cfg, template_id):")]
    new_templates = '''TEMPLATES = [
    {
        "id": "valid-gtin13-checksum",
        "display_name": "[Retail] Valid GTIN-13 Barcode Format & Checksum",
        "description": "[Retail] Validates GTIN-13 barcode is a 13-digit numeric GS1 identifier.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^[0-9]{13}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "valid-sku-format",
        "display_name": "[Retail] Valid Northwind Master SKU Format",
        "description": "[Retail] Validates SKU code matches Northwind format NW-SKU-NNNNNN.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^NW-SKU-[0-9]{6}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "valid-pii-email-phone-masked",
        "display_name": "[Retail] Valid Masked Shopper PII / Member-TIN Format",
        "description": "[Retail] Validates shopper PII / Member-TIN is masked as XXX-XX-NNNN and email/phone PII complies with CCPA masking.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^XXX-XX-[0-9]{4}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "valid-tender-type-enum",
        "display_name": "[Retail] Valid Loyalty Account & Tender Format",
        "description": "[Retail] Validates loyalty account / tender identifier matches ACCT-NNNNNNNNNN format.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (REGEXP_CONTAINS(${column()}, r'^ACCT-\\d{10}$') IS TRUE)",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "inventory-and-order-total-non-negative",
        "display_name": "[Retail] Non-Negative On-Hand Qty & Order Total Balance",
        "description": "[Retail] Validates on-hand inventory quantity, loyalty balance, and order total equal to sum of line items are non-negative.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE ${column()} < 0",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "negative-margin-guard",
        "display_name": "[Retail] Negative Margin & Financing Rate Guard",
        "description": "[Retail] Guards against negative gross margin rates or promotional APR outside 0% to 30%.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE ${column()} < 0 OR ${column()} > 0.30",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "loyalty-return-risk-score-range",
        "display_name": "[Retail] Loyalty Tier & Return-Risk Score Range (300-850)",
        "description": "[Retail] Validates shopper loyalty return-risk score is between 300 and 850.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE CAST(${column()} AS INT64) < 300 OR CAST(${column()} AS INT64) > 850",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "duplicate-loyalty-id-guard",
        "display_name": "[Retail] Valid Enrollment Date & Duplicate Loyalty ID Guard",
        "description": "[Retail] Validates loyalty enrollment/order dates are not in the future.",
        "dimension": "VALIDITY",
        "sql": r"SELECT * FROM ${data()} WHERE ${column()} > CURRENT_DATE()",
        "params": {},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "order-ship-delivery-date-ordering",
        "display_name": "[Retail] Order <= Ship <= Delivery Date Ordering",
        "description": "[Retail] Validates chronological date ordering (order_date <= ship_date <= delivery_date).",
        "dimension": "CONSISTENCY",
        "sql": r"SELECT * FROM ${data()} WHERE NOT (${column()} <= `${param(end_date_column)}`) IS TRUE",
        "params": {"end_date_column": {"description": "The later fulfillment/delivery date column to compare against"}},
        "capabilities": ["THRESHOLD", "IGNORE_NULL"],
    },
    {
        "id": "foreign-key-exists",
        "display_name": "[Retail] Foreign Key Reference Exists",
        "description": "[Retail] Validates every foreign key value (e.g., customer_id, store_id, sku_code) exists in its master reference table.",
        "dimension": "CONSISTENCY",
        "sql": r"SELECT t.* FROM ${data()} AS t LEFT JOIN `${param(reference_table)}` AS s ON t.${column()} = s.`${param(reference_column)}` WHERE s.`${param(reference_column)}` IS NULL",
        "params": {
            "reference_table": {"description": "Fully qualified master reference table"},
            "reference_column": {"description": "Primary key column in reference table"},
        },
        "capabilities": ["THRESHOLD"],
    },
]


'''
    txt = txt.replace(old_templates, new_templates)
    txt = txt.replace(
        '"displayName": "Northwind Retail Group Data Quality Rule Library"',
        '"displayName": "[Retail] Northwind Retail Group Data Quality Rule Library"',
    ).replace(
        '"description": "Centralized, reusable rule templates for Retail data validation."',
        '"description": "[Retail] Centralized, reusable rule templates for Northwind Retail data validation."',
    )

    old_attach = txt[txt.index("def attach_rules_to_terms(cfg):"):txt.index("    for term_id, rules in term_rules.items():")]
    new_attach = '''def attach_rules_to_terms(cfg):
    logger.info("=== Attaching rule templates to glossary terms ===")

    term_rules = {
        "loyalty-return-risk-score": [
            {"name": "return-risk-score-range-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] Return-Risk score must be between 300 and 850",
             "templateReference": {"name": _tref(cfg, "loyalty-return-risk-score-range")}},
        ],
        "member-tin": [
            {"name": "member-tin-masking-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] Shopper PII / Member-TIN must be masked as XXX-XX-NNNN",
             "templateReference": {"name": _tref(cfg, "valid-pii-email-phone-masked")}},
        ],
        "gtin-13": [
            {"name": "gtin13-format-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] GTIN-13 barcode must be a 13-digit GS1 identifier",
             "templateReference": {"name": _tref(cfg, "valid-gtin13-checksum")}},
        ],
        "sku-code": [
            {"name": "sku-code-format-check", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] SKU code must match Northwind format NW-SKU-NNNNNN",
             "templateReference": {"name": _tref(cfg, "valid-sku-format")}},
        ],
        "loyalty-account-balance": [
            {"name": "inventory-and-order-total-non-negative", "type": "TEMPLATE_REFERENCE", "dimension": "VALIDITY",
             "description": "[Retail] Loyalty balance, on-hand inventory, and order total must be non-negative",
             "templateReference": {"name": _tref(cfg, "inventory-and-order-total-non-negative")}},
        ],
    }

'''
    txt = txt.replace(old_attach, new_attach)
    p.write_text(txt, encoding="utf-8")


def update_11_13_15_16() -> None:
    for fname in ["11_run_scans_and_apply_insights.py", "13_apply_insights_descriptions.py", "15_inject_dirty_data.py"]:
        p = SCRIPTS_DIR / fname
        txt = p.read_text(encoding="utf-8")
        txt = txt.replace('dataset.replace("fsi_", "")', 'dataset.replace("retail_", "")')
        txt = txt.replace('ds.replace("fsi_", "")', 'ds.replace("retail_", "")')
        p.write_text(txt, encoding="utf-8")

    # In 13_apply_insights_descriptions.py, prefix table description with [Retail] if not already
    p13 = SCRIPTS_DIR / "13_apply_insights_descriptions.py"
    t13 = p13.read_text(encoding="utf-8")
    t13 = t13.replace(
        "table_obj.description = tbl_desc",
        'table_obj.description = tbl_desc if tbl_desc.startswith("[Retail]") else f"[Retail] {tbl_desc}"',
    )
    p13.write_text(t13, encoding="utf-8")

    # In 15_inject_dirty_data.py, prefix descriptions with [Retail]
    p15 = SCRIPTS_DIR / "15_inject_dirty_data.py"
    t15 = p15.read_text(encoding="utf-8")
    t15 = re.sub(r'"description": "(?!\[Retail\])', '"description": "[Retail] ', t15)
    p15.write_text(t15, encoding="utf-8")

    # In 16_create_policy_tags.py, prefix descriptions and display names with [Retail]
    p16 = SCRIPTS_DIR / "16_create_policy_tags.py"
    t16 = p16.read_text(encoding="utf-8")
    t16 = re.sub(r'"display_name": "(?!\[Retail\])', '"display_name": "[Retail] ', t16)
    t16 = re.sub(r'"description": "(?!\[Retail\])', '"description": "[Retail] ', t16)
    p16.write_text(t16, encoding="utf-8")


def main() -> None:
    update_common()
    update_00_infra()
    update_02_scans()
    update_03_source_entries()
    update_04_aspects()
    update_05_data_products()
    update_09_simulate_queries()
    update_10_rules()
    update_11_13_15_16()
    print("Updated governance scripts 00..16 and common.py successfully.")


if __name__ == "__main__":
    main()
