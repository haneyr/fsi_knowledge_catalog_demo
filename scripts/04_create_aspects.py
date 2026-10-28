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
Applies custom Retail aspects (data classification, retention, compliance, lineage,
access control, risk classification, regulatory reporting) to BQ tables and
glossary terms.

Usage: python3 04_create_aspects.py
"""

import logging
import time

from common import (
    load_config, set_entry_aspect, glossary_term_entry, bq_table_entry,
    BRONZE_TABLES, SILVER_TABLES, GOLD_TABLES,
)

logger = logging.getLogger(__name__)

ALL_TABLES = BRONZE_TABLES + SILVER_TABLES + GOLD_TABLES


def get_table_aspects(ds, tbl):
    layer = ds.replace("retail_", "")
    aspects = {}

    if "customers" in tbl or "wm_clients" in tbl:
        aspects["retail-data-classification"] = {"classification_level": "Restricted", "pii_category": "PII", "requires_encryption": True, "requires_masking": True, "regulatory_scope": "CCPA/CPRA, GDPR, Marketing Consent"}
    elif any(x in tbl for x in ["transactions", "bnpl_plans", "credit_cards", "card_trans", "billing", "wire", "ach"]):
        aspects["retail-data-classification"] = {"classification_level": "Confidential", "pii_category": "Payment Card Data", "requires_encryption": True, "requires_masking": False, "regulatory_scope": "PCI-DSS, CCPA/CPRA"}
    elif any(x in tbl for x in ["fraud", "kyc", "compliance"]):
        aspects["retail-data-classification"] = {"classification_level": "Highly Restricted", "pii_category": "Payment Card Data", "requires_encryption": True, "requires_masking": False, "regulatory_scope": "PCI-DSS, CCPA/CPRA, Loss Prevention"}
    elif any(x in tbl for x in ["gl_", "capital", "risk", "stress"]):
        aspects["retail-data-classification"] = {"classification_level": "Confidential", "pii_category": "Not PII", "requires_encryption": False, "requires_masking": False, "regulatory_scope": "PCI-DSS, SOX, Supplier-Confidential"}
    elif any(x in tbl for x in ["holdings", "assortments", "trades", "performance"]):
        aspects["retail-data-classification"] = {"classification_level": "Confidential", "pii_category": "Marketing Consent", "requires_encryption": True, "requires_masking": False, "regulatory_scope": "Supplier-Confidential, CCPA/CPRA"}
    else:
        aspects["retail-data-classification"] = {"classification_level": "Internal", "pii_category": "Not PII", "requires_encryption": False, "requires_masking": False, "regulatory_scope": "General"}

    if any(x in tbl for x in ["fraud", "kyc", "compliance", "sar"]):
        aspects["retail-data-retention"] = {"retention_period_years": 7, "governing_regulation": "PCI-DSS, CCPA/CPRA, Loss Prevention", "retention_start_event": "Date of record creation", "archival_required": True, "destruction_method": "Secure Purge"}
    elif any(x in tbl for x in ["gl_", "capital", "stress", "regulatory"]):
        aspects["retail-data-retention"] = {"retention_period_years": 7, "governing_regulation": "SOX, OCC, Federal Reserve", "retention_start_event": "End of fiscal year", "archival_required": True, "destruction_method": "Secure Purge"}
    else:
        aspects["retail-data-retention"] = {"retention_period_years": 5, "governing_regulation": "CCPA, State law", "retention_start_event": "Account closure or last activity", "archival_required": True, "destruction_method": "Crypto Shredding"}

    if layer == "gold":
        aspects["retail-regulatory-compliance"] = {"applicable_regulations": "SOX, CCPA, PCI-DSS III, DFAST", "compliance_status": "Compliant", "last_audit_date": "2025-11-15", "audit_frequency": "Quarterly", "compliance_notes": f"Analytics table ({tbl})."}
    else:
        aspects["retail-regulatory-compliance"] = {"applicable_regulations": "PCI-DSS, CCPA/CPRA", "compliance_status": "Compliant", "last_audit_date": "2025-11-15", "audit_frequency": "Annual", "compliance_notes": f"{'Raw' if layer == 'bronze' else 'Cleansed'} operational data."}

    src_map = {
        "customers": ("ORION IBM i POS", "IBM CDC Replication", "Real-time"),
        "accounts": ("ORION IBM i POS", "IBM CDC Replication", "Real-time"),
        "transactions": ("ORION IBM i POS", "IBM CDC Replication", "Real-time"),
        "bnpl_plans": ("ORION IBM i POS", "IBM CDC Replication", "End-of-Day"),
        "credit_cards": ("ORION IBM i POS", "IBM CDC Replication", "End-of-Day"),
        "card_trans": ("ORION IBM i POS", "IBM CDC Replication", "Real-time"),
        "fraud": ("ORION IBM i POS", "IBM CDC Replication", "Real-time"),
        "kyc": ("ORION IBM i POS", "IBM CDC Replication", "Daily"),
        "wire": ("ORION IBM i POS", "IBM CDC Replication", "Real-time"),
        "ach": ("ORION IBM i POS", "IBM CDC Replication", "Daily"),
        "store": ("ORION IBM i POS", "Batch File Extract", "Daily"),
        "employee": ("ORION IBM i POS", "Batch File Extract", "Daily"),
        "atm": ("ORION IBM i POS", "IBM CDC Replication", "Real-time"),
        "wm_client": ("LUMEN Commerce Cloud", "Salesforce Extract API", "End-of-Day"),
        "assortment": ("LUMEN Commerce Cloud", "Salesforce Extract API", "End-of-Day"),
        "holding": ("LUMEN Commerce Cloud", "Salesforce Extract API", "End-of-Day"),
        "trade": ("LUMEN Commerce Cloud", "Salesforce Extract API", "Intraday"),
        "securit": ("LUMEN Commerce Cloud", "Salesforce Extract API", "End-of-Day"),
        "advisor": ("LUMEN Commerce Cloud", "Salesforce Extract API", "Daily"),
        "performance": ("LUMEN Commerce Cloud", "Salesforce Extract API", "End-of-Day"),
        "fee_schedule": ("LUMEN Commerce Cloud", "Salesforce Extract API", "Daily"),
        "benchmark": ("LUMEN Commerce Cloud", "Salesforce Extract API", "End-of-Day"),
        "client_goal": ("LUMEN Commerce Cloud", "Salesforce Extract API", "Daily"),
        "risk_profile": ("LUMEN Commerce Cloud", "Salesforce Extract API", "Daily"),
        "distribution": ("LUMEN Commerce Cloud", "Salesforce Extract API", "Daily"),
        "custodian": ("LUMEN Commerce Cloud", "Salesforce Extract API", "End-of-Day"),
        "gl_": ("HELIOS SAP S/4HANA Retail", "SAP SLT Replication", "Real-time"),
        "cost_center": ("HELIOS SAP S/4HANA Retail", "SAP SLT Replication", "Daily"),
        "capital": ("HELIOS SAP S/4HANA Retail", "SAP SLT Replication", "Monthly"),
        "risk_exposure": ("HELIOS SAP S/4HANA Retail", "SAP SLT Replication", "End-of-Day"),
        "counterpart": ("HELIOS SAP S/4HANA Retail", "SAP SLT Replication", "Daily"),
        "market_data": ("HELIOS SAP S/4HANA Retail", "API Integration", "End-of-Day"),
        "stress": ("HELIOS SAP S/4HANA Retail", "SAP SLT Replication", "Quarterly"),
        "audit": ("HELIOS SAP S/4HANA Retail", "SAP SLT Replication", "Real-time"),
        "regulatory_filing": ("HELIOS SAP S/4HANA Retail", "SAP SLT Replication", "Quarterly"),
        "interest_rate": ("HELIOS SAP S/4HANA Retail", "API Integration", "End-of-Day"),
        "fx_rate": ("HELIOS SAP S/4HANA Retail", "API Integration", "End-of-Day"),
        "compliance": ("HELIOS SAP S/4HANA Retail", "SAP SLT Replication", "Real-time"),
    }
    for key, (src, method, freq) in src_map.items():
        if key in tbl:
            path = f"{src} -> {ds}.{tbl}" if layer == "bronze" else (f"{src} -> retail_bronze -> {ds}.{tbl}" if layer == "silver" else f"retail_silver -> aggregation -> {ds}.{tbl}")
            aspects["retail-data-lineage-metadata"] = {"source_system": src, "ingestion_method": method, "refresh_frequency": freq, "data_flow_path": path}
            break

    if any(x in tbl for x in ["customers", "wm_clients", "kyc"]):
        aspects["retail-access-control"] = {"access_level": "Restricted", "authorized_roles": "Compliance, Relationship Manager, Store Manager", "requires_mfa": True, "need_to_know_applies": True, "audit_all_access": True}
    elif any(x in tbl for x in ["fraud", "compliance", "sar"]):
        aspects["retail-access-control"] = {"access_level": "Highly Restricted", "authorized_roles": "Privacy & Compliance Officer, Loss Prevention, Legal", "requires_mfa": True, "need_to_know_applies": True, "audit_all_access": True}
    elif any(x in tbl for x in ["gl_", "capital", "stress"]):
        aspects["retail-access-control"] = {"access_level": "Confidential", "authorized_roles": "CFO, Controller, Finance Analyst, Internal Audit", "requires_mfa": True, "need_to_know_applies": True, "audit_all_access": True}
    else:
        aspects["retail-access-control"] = {"access_level": "Restricted", "authorized_roles": "Department Head, Data Analyst, Operations", "requires_mfa": False, "need_to_know_applies": True, "audit_all_access": False}

    if any(x in tbl for x in ["fraud", "return", "card_trans"]):
        aspects["retail-risk-classification"] = {"risk_category": "Return and Fraud Risk", "model_dependency": "Model Input", "materiality_level": "Significant", "sox_relevant": False}
    elif any(x in tbl for x in ["stress", "risk", "performance", "assortment"]):
        aspects["retail-risk-classification"] = {"risk_category": "Demand and Markdown Risk", "model_dependency": "Model Output", "materiality_level": "Material", "sox_relevant": True}
    elif any(x in tbl for x in ["capital", "gl_", "holding"]):
        aspects["retail-risk-classification"] = {"risk_category": "Stockout and Liquidity Risk", "model_dependency": "Model Input", "materiality_level": "Material", "sox_relevant": True}
    elif any(x in tbl for x in ["customers", "wm_clients", "kyc", "compliance"]):
        aspects["retail-risk-classification"] = {"risk_category": "Privacy and PCI Risk", "model_dependency": "Not Model Related", "materiality_level": "Significant", "sox_relevant": False}

    if any(x in tbl for x in ["regulatory", "compliance", "kyc"]):
        aspects["retail-regulatory-reporting"] = {"report_name": "CCPA-CPRA Annual Privacy & Supplier Audit", "filing_frequency": "Annual", "regulatory_body": "CPPA CCPA-CPRA", "schedule_line_item": "Schedule A - Consumer Privacy & Supplier Compliance"}
    elif any(x in tbl for x in ["card_trans", "credit_cards", "transactions", "fraud"]):
        aspects["retail-regulatory-reporting"] = {"report_name": "PCI-DSS v4.0 Report on Compliance (ROC)", "filing_frequency": "Quarterly", "regulatory_body": "PCI-SSC", "schedule_line_item": "Req 3 & Req 10 - Cardholder Data Protection"}
    elif any(x in tbl for x in ["gl_", "capital", "stress"]):
        aspects["retail-regulatory-reporting"] = {"report_name": "Form 10-K / SOX 404 Retail Financial Controls", "filing_frequency": "Quarterly", "regulatory_body": "SEC", "schedule_line_item": "Item 7 - MD&A Inventory & Working Capital"}

    return aspects


def apply_table_aspects(cfg):
    logger.info("=== Applying aspects to %d BQ tables ===", len(ALL_TABLES))
    total = 0
    for ds, tbl in ALL_TABLES:
        entry = bq_table_entry(cfg, ds, tbl)
        aspects = get_table_aspects(ds, tbl)
        for aspect_id, data in aspects.items():
            try:
                set_entry_aspect(cfg, entry, aspect_id, data)
                total += 1
            except RuntimeError as e:
                logger.warning("  Failed %s on %s: %s", aspect_id, tbl, str(e)[:80])
            time.sleep(0.3)
    logger.info("  Applied %d aspect instances to tables", total)


def apply_glossary_aspects(cfg):
    logger.info("=== Applying aspects to glossary terms ===")
    PII_TERMS = {
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
    count = 0
    for term_id, (cat, level, enc, mask, reg) in PII_TERMS.items():
        try:
            entry = glossary_term_entry(cfg, term_id)
            set_entry_aspect(cfg, entry, "retail-data-classification", {
                "classification_level": level, "pii_category": cat,
                "requires_encryption": enc, "requires_masking": mask,
                "regulatory_scope": reg,
            })
            count += 1
        except RuntimeError:
            pass
        time.sleep(0.3)
    logger.info("  Classification: %d terms", count)


def main():
    cfg = load_config()
    logger.info("Project: %s", cfg["project_id"])
    apply_table_aspects(cfg)
    apply_glossary_aspects(cfg)
    logger.info("Aspect application complete")


if __name__ == "__main__":
    main()
