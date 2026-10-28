#!/usr/bin/env python3
"""Creates Knowledge Catalog entry types, aspect types, and entry groups via API.
Replaces the Terraform dataplex-entry-types module when TF is not available.

Usage: python3 00_create_dataplex_infra.py
"""

import json
import logging
import time

from common import (
    load_config, api_call, poll_operation, DATAPLEX_URL,
    entry_group_location, entry_type_location,
)

logger = logging.getLogger(__name__)


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    loc = entry_type_location(cfg)          # entry/aspect types: global (#20)
    eg_loc = entry_group_location(cfg)      # entry groups: multi-region (#20)
    DP = DATAPLEX_URL

    # --- Entry Types ---
    entry_types = [
        ("retail-ibmi-instance", "[Retail] IBM i NCR POS Instance", ["DATABASE"], "IBM", "NCR POS on IBM i"),
        ("retail-ibmi-schema", "[Retail] IBM i POS Schema", ["DATABASE_SCHEMA"], "IBM", "NCR POS on IBM i"),
        ("retail-ibmi-table", "[Retail] IBM i POS Table", ["TABLE"], "IBM", "NCR POS on IBM i"),
        ("retail-sfcc-instance", "[Retail] Salesforce Commerce Cloud Instance", ["DATABASE"], "Salesforce", "Commerce Cloud"),
        ("retail-sfcc-schema", "[Retail] Salesforce Commerce Schema", ["DATABASE_SCHEMA"], "Salesforce", "Commerce Cloud"),
        ("retail-sfcc-table", "[Retail] Salesforce Commerce Table", ["TABLE"], "Salesforce", "Commerce Cloud"),
        ("retail-sap-instance", "[Retail] SAP S/4HANA Retail Instance", ["DATABASE"], "SAP", "S/4HANA Retail"),
        ("retail-sap-schema", "[Retail] SAP S/4HANA Retail Schema", ["DATABASE_SCHEMA"], "SAP", "S/4HANA Retail"),
        ("retail-sap-table", "[Retail] SAP S/4HANA Retail Table", ["TABLE"], "SAP", "S/4HANA Retail"),
    ]

    logger.info("Creating %d entry types...", len(entry_types))
    for et_id, name, aliases, platform, system in entry_types:
        result = api_call(f"{DP}/projects/{pid}/locations/{loc}/entryTypes?entryTypeId={et_id}", "POST", {
            "displayName": name, "description": f"[Retail] Represents a {name.replace('[Retail] ', '').lower()}", "typeAliases": aliases, "platform": platform, "system": system,
        })
        if "name" in result and "operations" in result.get("name", ""):
            poll_operation(result["name"])
        status = "exists" if result.get("_exists") else "created"
        logger.info("  %s: %s", et_id, status)
        time.sleep(1)

    # --- Aspect Types (regional markers) ---
    marker_aspects = ["retail-ibmi-instance", "retail-ibmi-schema", "retail-ibmi-table", "retail-sfcc-instance", "retail-sfcc-table", "retail-sap-instance", "retail-sap-table"]
    logger.info("Creating %d marker aspect types...", len(marker_aspects))
    for at_id in marker_aspects:
        for attempt in range(5):
            try:
                result = api_call(f"{DP}/projects/{pid}/locations/{loc}/aspectTypes?aspectTypeId={at_id}", "POST", {
                    "displayName": f"[Retail] {at_id.replace('-', ' ').title()}",
                    "description": f"[Retail] Marker aspect for {at_id} entries",
                    "metadataTemplate": {"name": at_id.replace("-", "_"), "type": "record", "recordFields": []},
                })
                if "name" in result and "operations" in result.get("name", ""):
                    poll_operation(result["name"])
                status = "exists" if result.get("_exists") else "created"
                logger.info("  %s: %s", at_id, status)
                break
            except RuntimeError as e:
                if "429" in str(e) and attempt < 4:
                    wait = 15 * (attempt + 1)
                    logger.warning("  %s: rate limited, waiting %ds...", at_id, wait)
                    time.sleep(wait)
                else:
                    raise
        time.sleep(5)

    # --- Custom Aspect Types (global) ---
    custom_aspects = [
        ("retail-data-classification", "[Retail] Data Classification", "[Retail] Retail data sensitivity, PII, PCI-DSS, and marketing consent classification", [
            {"name": "classification_level", "type": "enum", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Classification Level"},
             "enumValues": [{"name": "Public", "index": 1}, {"name": "Internal", "index": 2}, {"name": "Confidential", "index": 3}, {"name": "Restricted", "index": 4}, {"name": "Highly Restricted", "index": 5}, {"name": "Supplier-Confidential", "index": 6}, {"name": "Third-Party Licensed", "index": 7}]},
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
        ("retail-data-lineage-metadata", "[Retail] Data Lineage Metadata", "[Retail] Source system (ORION, LUMEN, HELIOS, NEXUS) and omnichannel data flow metadata", [
            {"name": "source_system", "type": "string", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Source System"}},
            {"name": "ingestion_method", "type": "enum", "index": 2, "annotations": {"displayName": "Ingestion Method"},
             "enumValues": [{"name": "IBM CDC Replication", "index": 1}, {"name": "Salesforce Extract API", "index": 2}, {"name": "SAP SLT Replication", "index": 3}, {"name": "Batch File Extract", "index": 4}, {"name": "Database Replication", "index": 5}, {"name": "API Integration", "index": 6}, {"name": "Commerce Export API", "index": 7}]},
            {"name": "refresh_frequency", "type": "enum", "index": 3, "annotations": {"displayName": "Refresh Frequency"},
             "enumValues": [{"name": "Real-time", "index": 1}, {"name": "Intraday", "index": 2}, {"name": "End-of-Day", "index": 3}, {"name": "Daily", "index": 4}, {"name": "Weekly", "index": 5}, {"name": "Monthly", "index": 6}]},
            {"name": "data_flow_path", "type": "string", "index": 4, "annotations": {"displayName": "Data Flow Path"}},
            {"name": "cloud_platform", "type": "string", "index": 5, "annotations": {"displayName": "Cloud Platform"}},
            {"name": "data_residency", "type": "string", "index": 6, "annotations": {"displayName": "Data Residency"}},
        ]),
        ("retail-access-control", "[Retail] Access Control Policy", "[Retail] Role-based access control for store ops, merchandising, and privacy teams", [
            {"name": "access_level", "type": "enum", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Access Level"},
             "enumValues": [{"name": "Public", "index": 1}, {"name": "Internal", "index": 2}, {"name": "Restricted", "index": 3}, {"name": "Confidential", "index": 4}, {"name": "Highly Restricted", "index": 5}, {"name": "Supplier-Confidential", "index": 6}, {"name": "External Vendor Agreement", "index": 7}]},
            {"name": "authorized_roles", "type": "string", "index": 2, "constraints": {"required": True}, "annotations": {"displayName": "Authorized Roles"}},
            {"name": "requires_mfa", "type": "bool", "index": 3, "annotations": {"displayName": "Requires MFA"}},
            {"name": "need_to_know_applies", "type": "bool", "index": 4, "annotations": {"displayName": "Need-to-Know Applies"}},
            {"name": "audit_all_access", "type": "bool", "index": 5, "annotations": {"displayName": "Audit All Access"}},
        ]),
        ("retail-risk-classification", "[Retail] Risk Data Classification", "[Retail] Return fraud, shrinkage, markdown, and supply chain risk tagging", [
            {"name": "risk_category", "type": "enum", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Risk Category"},
             "enumValues": [{"name": "Return and Fraud Risk", "index": 1}, {"name": "Demand and Markdown Risk", "index": 2}, {"name": "Shrinkage and Ops Risk", "index": 3}, {"name": "Stockout and Liquidity Risk", "index": 4}, {"name": "Privacy and PCI Risk", "index": 5}, {"name": "Not Risk Data", "index": 6}]},
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
             "enumValues": [{"name": "PCI-SSC", "index": 1}, {"name": "CPPA CCPA-CPRA", "index": 2}, {"name": "EU DPA GDPR", "index": 3}, {"name": "FTC", "index": 4}, {"name": "SEC", "index": 5}, {"name": "GS1 US", "index": 6}, {"name": "State Attorney General", "index": 7}, {"name": "Internal Audit", "index": 8}]},
            {"name": "schedule_line_item", "type": "string", "index": 4, "annotations": {"displayName": "Schedule / Line Item"}},
        ]),
    ]

    logger.info("Creating %d custom aspect types (global)...", len(custom_aspects))
    for at_id, name, desc, fields in custom_aspects:
        template = {"name": at_id.replace("-", "_"), "type": "record", "recordFields": fields}
        for attempt in range(5):
            try:
                result = api_call(f"{DP}/projects/{pid}/locations/global/aspectTypes?aspectTypeId={at_id}", "POST", {
                    "displayName": name, "description": desc, "metadataTemplate": template,
                })
                if "name" in result and "operations" in result.get("name", ""):
                    poll_operation(result["name"])
                status = "exists" if result.get("_exists") else "created"
                logger.info("  %s: %s", at_id, status)
                break
            except RuntimeError as e:
                if "429" in str(e) and attempt < 4:
                    wait = 15 * (attempt + 1)
                    logger.warning("  %s: rate limited, waiting %ds...", at_id, wait)
                    time.sleep(wait)
                else:
                    raise
        time.sleep(5)

    # --- Entry Groups ---
    entry_groups = [
        ("retail-orion-store-pos", "[Retail] ORION Store Ops & POS (IBM i)", "[Retail] NCR POS on IBM i custom source entries for ORION (14 tables)"),
        ("retail-lumen-commerce-loyalty", "[Retail] LUMEN Digital Commerce & Loyalty (Salesforce)", "[Retail] Salesforce Commerce Cloud custom source entries for LUMEN (13 tables)"),
        ("retail-helios-merch-supply", "[Retail] HELIOS Merchandising, Supply Chain & Finance (SAP)", "[Retail] SAP S/4HANA Retail custom source entries for HELIOS (13 tables)"),
    ]

    logger.info("Creating %d entry groups...", len(entry_groups))
    for eg_id, name, desc in entry_groups:
        for attempt in range(5):
            try:
                result = api_call(f"{DP}/projects/{pid}/locations/{eg_loc}/entryGroups?entryGroupId={eg_id}", "POST", {
                    "displayName": name, "description": desc,
                })
                if "name" in result and "operations" in result.get("name", ""):
                    poll_operation(result["name"])
                status = "exists" if result.get("_exists") else "created"
                logger.info("  %s: %s", eg_id, status)
                break
            except RuntimeError as e:
                if "429" in str(e) and attempt < 4:
                    wait = 15 * (attempt + 1)
                    logger.warning("  %s: rate limited, waiting %ds...", eg_id, wait)
                    time.sleep(wait)
                else:
                    raise
        time.sleep(5)

    logger.info("Knowledge Catalog infrastructure complete")


if __name__ == "__main__":
    main()
