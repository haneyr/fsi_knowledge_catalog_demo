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
Applies custom FSI aspects (data classification, retention, compliance, lineage,
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
    layer = ds.replace("fsi_", "")
    aspects = {}

    if "customers" in tbl or "wm_clients" in tbl:
        aspects["fsi-data-classification"] = {"classification_level": "Restricted", "pii_category": "Direct Identifier", "requires_encryption": True, "requires_masking": True, "regulatory_scope": "GLBA, CCPA, BSA/AML"}
    elif any(x in tbl for x in ["transactions", "loans", "credit_cards", "card_trans", "billing", "wire", "ach"]):
        aspects["fsi-data-classification"] = {"classification_level": "Confidential", "pii_category": "Financial Data", "requires_encryption": True, "requires_masking": False, "regulatory_scope": "GLBA, BSA/AML, Reg E"}
    elif any(x in tbl for x in ["fraud", "kyc", "compliance"]):
        aspects["fsi-data-classification"] = {"classification_level": "Highly Restricted", "pii_category": "Financial Data", "requires_encryption": True, "requires_masking": False, "regulatory_scope": "BSA/AML, FinCEN"}
    elif any(x in tbl for x in ["gl_", "capital", "risk", "stress"]):
        aspects["fsi-data-classification"] = {"classification_level": "Confidential", "pii_category": "Not PII", "requires_encryption": False, "requires_masking": False, "regulatory_scope": "SOX, Basel III, DFAST"}
    elif any(x in tbl for x in ["holdings", "portfolios", "trades", "performance"]):
        aspects["fsi-data-classification"] = {"classification_level": "Confidential", "pii_category": "Account Data", "requires_encryption": True, "requires_masking": False, "regulatory_scope": "SEC, FINRA, Investment Advisers Act"}
    else:
        aspects["fsi-data-classification"] = {"classification_level": "Internal", "pii_category": "Not PII", "requires_encryption": False, "requires_masking": False, "regulatory_scope": "General"}

    if any(x in tbl for x in ["fraud", "kyc", "compliance", "sar"]):
        aspects["fsi-data-retention"] = {"retention_period_years": 7, "governing_regulation": "BSA/AML, FinCEN", "retention_start_event": "Date of record creation", "archival_required": True, "destruction_method": "Secure Purge"}
    elif any(x in tbl for x in ["gl_", "capital", "stress", "regulatory"]):
        aspects["fsi-data-retention"] = {"retention_period_years": 7, "governing_regulation": "SOX, OCC, Federal Reserve", "retention_start_event": "End of fiscal year", "archival_required": True, "destruction_method": "Secure Purge"}
    else:
        aspects["fsi-data-retention"] = {"retention_period_years": 5, "governing_regulation": "GLBA, State law", "retention_start_event": "Account closure or last activity", "archival_required": True, "destruction_method": "Crypto Shredding"}

    if layer == "gold":
        aspects["fsi-regulatory-compliance"] = {"applicable_regulations": "SOX, GLBA, Basel III, DFAST", "compliance_status": "Compliant", "last_audit_date": "2025-11-15", "audit_frequency": "Quarterly", "compliance_notes": f"Analytics table ({tbl})."}
    else:
        aspects["fsi-regulatory-compliance"] = {"applicable_regulations": "GLBA, BSA/AML, Reg E", "compliance_status": "Compliant", "last_audit_date": "2025-11-15", "audit_frequency": "Annual", "compliance_notes": f"{'Raw' if layer == 'bronze' else 'Cleansed'} operational data."}

    src_map = {
        "customers": ("ATLAS DB2", "IBM CDC Replication", "Real-time"),
        "accounts": ("ATLAS DB2", "IBM CDC Replication", "Real-time"),
        "transactions": ("ATLAS DB2", "IBM CDC Replication", "Real-time"),
        "loans": ("ATLAS DB2", "IBM CDC Replication", "End-of-Day"),
        "credit_cards": ("ATLAS DB2", "IBM CDC Replication", "End-of-Day"),
        "card_trans": ("ATLAS DB2", "IBM CDC Replication", "Real-time"),
        "fraud": ("ATLAS DB2", "IBM CDC Replication", "Real-time"),
        "kyc": ("ATLAS DB2", "IBM CDC Replication", "Daily"),
        "wire": ("ATLAS DB2", "IBM CDC Replication", "Real-time"),
        "ach": ("ATLAS DB2", "IBM CDC Replication", "Daily"),
        "branch": ("ATLAS DB2", "Batch File Extract", "Daily"),
        "employee": ("ATLAS DB2", "Batch File Extract", "Daily"),
        "atm": ("ATLAS DB2", "IBM CDC Replication", "Real-time"),
        "wm_client": ("FORTUNA T24", "Temenos Extract API", "End-of-Day"),
        "portfolio": ("FORTUNA T24", "Temenos Extract API", "End-of-Day"),
        "holding": ("FORTUNA T24", "Temenos Extract API", "End-of-Day"),
        "trade": ("FORTUNA T24", "Temenos Extract API", "Intraday"),
        "securit": ("FORTUNA T24", "Temenos Extract API", "End-of-Day"),
        "advisor": ("FORTUNA T24", "Temenos Extract API", "Daily"),
        "performance": ("FORTUNA T24", "Temenos Extract API", "End-of-Day"),
        "fee_schedule": ("FORTUNA T24", "Temenos Extract API", "Daily"),
        "benchmark": ("FORTUNA T24", "Temenos Extract API", "End-of-Day"),
        "client_goal": ("FORTUNA T24", "Temenos Extract API", "Daily"),
        "risk_profile": ("FORTUNA T24", "Temenos Extract API", "Daily"),
        "distribution": ("FORTUNA T24", "Temenos Extract API", "Daily"),
        "custodian": ("FORTUNA T24", "Temenos Extract API", "End-of-Day"),
        "gl_": ("ARGUS S/4HANA", "SAP SLT Replication", "Real-time"),
        "cost_center": ("ARGUS S/4HANA", "SAP SLT Replication", "Daily"),
        "capital": ("ARGUS S/4HANA", "SAP SLT Replication", "Monthly"),
        "risk_exposure": ("ARGUS S/4HANA", "SAP SLT Replication", "End-of-Day"),
        "counterpart": ("ARGUS S/4HANA", "SAP SLT Replication", "Daily"),
        "market_data": ("ARGUS S/4HANA", "API Integration", "End-of-Day"),
        "stress": ("ARGUS S/4HANA", "SAP SLT Replication", "Quarterly"),
        "audit": ("ARGUS S/4HANA", "SAP SLT Replication", "Real-time"),
        "regulatory_filing": ("ARGUS S/4HANA", "SAP SLT Replication", "Quarterly"),
        "interest_rate": ("ARGUS S/4HANA", "API Integration", "End-of-Day"),
        "fx_rate": ("ARGUS S/4HANA", "API Integration", "End-of-Day"),
        "compliance": ("ARGUS S/4HANA", "SAP SLT Replication", "Real-time"),
    }
    for key, (src, method, freq) in src_map.items():
        if key in tbl:
            path = f"{src} -> {ds}.{tbl}" if layer == "bronze" else (f"{src} -> fsi_bronze -> {ds}.{tbl}" if layer == "silver" else f"fsi_silver -> aggregation -> {ds}.{tbl}")
            aspects["fsi-data-lineage-metadata"] = {"source_system": src, "ingestion_method": method, "refresh_frequency": freq, "data_flow_path": path}
            break

    if any(x in tbl for x in ["customers", "wm_clients", "kyc"]):
        aspects["fsi-access-control"] = {"access_level": "Restricted", "authorized_roles": "Compliance, Relationship Manager, Branch Manager", "requires_mfa": True, "need_to_know_applies": True, "audit_all_access": True}
    elif any(x in tbl for x in ["fraud", "compliance", "sar"]):
        aspects["fsi-access-control"] = {"access_level": "Highly Restricted", "authorized_roles": "BSA Officer, Compliance Analyst, Legal", "requires_mfa": True, "need_to_know_applies": True, "audit_all_access": True}
    elif any(x in tbl for x in ["gl_", "capital", "stress"]):
        aspects["fsi-access-control"] = {"access_level": "Confidential", "authorized_roles": "CFO, Controller, Finance Analyst, Internal Audit", "requires_mfa": True, "need_to_know_applies": True, "audit_all_access": True}
    else:
        aspects["fsi-access-control"] = {"access_level": "Restricted", "authorized_roles": "Department Head, Data Analyst, Operations", "requires_mfa": False, "need_to_know_applies": True, "audit_all_access": False}

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
        "customer-id": ("Direct Identifier", "Restricted", True, True, "GLBA, CCPA"),
        "tin": ("Direct Identifier", "Highly Restricted", True, True, "IRS, GLBA"),
        "fico-score": ("Financial Data", "Confidential", True, False, "FCRA, GLBA"),
        "checking-account": ("Account Data", "Confidential", True, False, "GLBA, Reg E"),
        "savings-account": ("Account Data", "Confidential", True, False, "GLBA"),
        "account-balance": ("Financial Data", "Confidential", True, False, "GLBA"),
        "mortgage": ("Financial Data", "Confidential", True, False, "TILA, RESPA, GLBA"),
        "credit-card": ("Account Data", "Confidential", True, False, "GLBA, PCI-DSS"),
        "wire-transfer": ("Financial Data", "Confidential", True, False, "BSA/AML, OFAC"),
        "sar": ("Financial Data", "Highly Restricted", True, False, "BSA/AML, FinCEN"),
        "kyc": ("Financial Data", "Restricted", True, False, "BSA/AML, CDD Rule"),
        "aum": ("Financial Data", "Confidential", True, False, "SEC, Investment Advisers Act"),
        "general-ledger": ("Not PII", "Confidential", False, False, "SOX"),
        "cet1-ratio": ("Not PII", "Internal", False, False, "Basel III, DFAST"),
        "var": ("Not PII", "Confidential", False, False, "Basel III"),
        "branch": ("Not PII", "Internal", False, False, "General"),
    }
    count = 0
    for term_id, (cat, level, enc, mask, reg) in PII_TERMS.items():
        try:
            entry = glossary_term_entry(cfg, term_id)
            set_entry_aspect(cfg, entry, "fsi-data-classification", {
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
