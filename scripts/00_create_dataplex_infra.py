#!/usr/bin/env python3
"""Creates Dataplex entry types, aspect types, and entry groups via API.
Replaces the Terraform dataplex-entry-types module when TF is not available.

Usage: python3 00_create_dataplex_infra.py
"""

import json
import logging
import time

from common import load_config, api_call, poll_operation, DATAPLEX_URL

logger = logging.getLogger(__name__)


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    loc = cfg["location"]
    DP = DATAPLEX_URL

    # --- Entry Types ---
    entry_types = [
        ("db2-instance", "DB2 Mainframe Instance", ["DATABASE"], "IBM", "DB2 for z/OS"),
        ("db2-schema", "DB2 Schema", ["DATABASE_SCHEMA"], "IBM", "DB2 for z/OS"),
        ("db2-table", "DB2 Table", ["TABLE"], "IBM", "DB2 for z/OS"),
        ("temenos-instance", "Temenos T24 Instance", ["DATABASE"], "Temenos", "T24 Transact"),
        ("temenos-schema", "Temenos Schema", ["DATABASE_SCHEMA"], "Temenos", "T24 Transact"),
        ("temenos-table", "Temenos Table", ["TABLE"], "Temenos", "T24 Transact"),
        ("sap-instance", "SAP S/4HANA Instance", ["DATABASE"], "SAP", "S/4HANA"),
        ("sap-schema", "SAP Schema", ["DATABASE_SCHEMA"], "SAP", "S/4HANA"),
        ("sap-table", "SAP Table", ["TABLE"], "SAP", "S/4HANA"),
    ]

    logger.info("Creating %d entry types...", len(entry_types))
    for et_id, name, aliases, platform, system in entry_types:
        result = api_call(f"{DP}/projects/{pid}/locations/{loc}/entryTypes?entryTypeId={et_id}", "POST", {
            "displayName": name, "description": f"Represents a {name.lower()}", "typeAliases": aliases, "platform": platform, "system": system,
        })
        if "name" in result and "operations" in result.get("name", ""):
            poll_operation(result["name"])
        status = "exists" if result.get("_exists") else "created"
        logger.info("  %s: %s", et_id, status)
        time.sleep(1)

    # --- Aspect Types (regional markers) ---
    marker_aspects = ["db2-instance", "db2-schema", "db2-table", "temenos-instance", "temenos-table", "sap-instance", "sap-table"]
    logger.info("Creating %d marker aspect types...", len(marker_aspects))
    for at_id in marker_aspects:
        for attempt in range(5):
            try:
                result = api_call(f"{DP}/projects/{pid}/locations/{loc}/aspectTypes?aspectTypeId={at_id}", "POST", {
                    "displayName": at_id.replace("-", " ").title(),
                    "description": f"Marker aspect for {at_id} entries",
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
        ("fsi-data-classification", "Data Classification", "Data sensitivity and PII classification", [
            {"name": "classification_level", "type": "enum", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Classification Level"},
             "enumValues": [{"name": "Public", "index": 1}, {"name": "Internal", "index": 2}, {"name": "Confidential", "index": 3}, {"name": "Restricted", "index": 4}, {"name": "Highly Restricted", "index": 5}]},
            {"name": "pii_category", "type": "enum", "index": 2, "annotations": {"displayName": "PII Category"},
             "enumValues": [{"name": "Direct Identifier", "index": 1}, {"name": "Quasi Identifier", "index": 2}, {"name": "Financial Data", "index": 3}, {"name": "Account Data", "index": 4}, {"name": "Not PII", "index": 5}]},
            {"name": "requires_encryption", "type": "bool", "index": 3, "annotations": {"displayName": "Requires Encryption"}},
            {"name": "requires_masking", "type": "bool", "index": 4, "annotations": {"displayName": "Requires Masking"}},
            {"name": "regulatory_scope", "type": "string", "index": 5, "annotations": {"displayName": "Regulatory Scope"}},
        ]),
        ("fsi-data-retention", "Data Retention Policy", "Regulatory data retention requirements", [
            {"name": "retention_period_years", "type": "int", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Retention Period (Years)"}},
            {"name": "governing_regulation", "type": "string", "index": 2, "annotations": {"displayName": "Governing Regulation"}},
            {"name": "retention_start_event", "type": "string", "index": 3, "annotations": {"displayName": "Retention Start Event"}},
            {"name": "archival_required", "type": "bool", "index": 4, "annotations": {"displayName": "Archival Required"}},
            {"name": "destruction_method", "type": "enum", "index": 5, "annotations": {"displayName": "Destruction Method"},
             "enumValues": [{"name": "Secure Purge", "index": 1}, {"name": "Crypto Shredding", "index": 2}, {"name": "Physical Destruction", "index": 3}, {"name": "Not Applicable", "index": 4}]},
        ]),
        ("fsi-regulatory-compliance", "Regulatory Compliance", "Compliance status", [
            {"name": "applicable_regulations", "type": "string", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Applicable Regulations"}},
            {"name": "compliance_status", "type": "enum", "index": 2, "constraints": {"required": True}, "annotations": {"displayName": "Compliance Status"},
             "enumValues": [{"name": "Compliant", "index": 1}, {"name": "Partially Compliant", "index": 2}, {"name": "Non-Compliant", "index": 3}, {"name": "Under Review", "index": 4}]},
            {"name": "last_audit_date", "type": "string", "index": 3, "annotations": {"displayName": "Last Audit Date"}},
            {"name": "audit_frequency", "type": "enum", "index": 4, "annotations": {"displayName": "Audit Frequency"},
             "enumValues": [{"name": "Annual", "index": 1}, {"name": "Semi-Annual", "index": 2}, {"name": "Quarterly", "index": 3}, {"name": "Continuous", "index": 4}]},
            {"name": "compliance_notes", "type": "string", "index": 5, "annotations": {"displayName": "Compliance Notes"}},
        ]),
        ("fsi-data-lineage-metadata", "Data Lineage Metadata", "Source system and data flow info", [
            {"name": "source_system", "type": "string", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Source System"}},
            {"name": "ingestion_method", "type": "enum", "index": 2, "annotations": {"displayName": "Ingestion Method"},
             "enumValues": [{"name": "IBM CDC Replication", "index": 1}, {"name": "Temenos Extract API", "index": 2}, {"name": "SAP SLT Replication", "index": 3}, {"name": "Batch File Extract", "index": 4}, {"name": "Database Replication", "index": 5}, {"name": "API Integration", "index": 6}, {"name": "SWIFT/FIX Message", "index": 7}]},
            {"name": "refresh_frequency", "type": "enum", "index": 3, "annotations": {"displayName": "Refresh Frequency"},
             "enumValues": [{"name": "Real-time", "index": 1}, {"name": "Intraday", "index": 2}, {"name": "End-of-Day", "index": 3}, {"name": "Daily", "index": 4}, {"name": "Weekly", "index": 5}, {"name": "Monthly", "index": 6}]},
            {"name": "data_flow_path", "type": "string", "index": 4, "annotations": {"displayName": "Data Flow Path"}},
        ]),
        ("fsi-access-control", "Access Control Policy", "RBAC requirements", [
            {"name": "access_level", "type": "enum", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Access Level"},
             "enumValues": [{"name": "Public", "index": 1}, {"name": "Internal", "index": 2}, {"name": "Restricted", "index": 3}, {"name": "Confidential", "index": 4}, {"name": "Highly Restricted", "index": 5}]},
            {"name": "authorized_roles", "type": "string", "index": 2, "constraints": {"required": True}, "annotations": {"displayName": "Authorized Roles"}},
            {"name": "requires_mfa", "type": "bool", "index": 3, "annotations": {"displayName": "Requires MFA"}},
            {"name": "need_to_know_applies", "type": "bool", "index": 4, "annotations": {"displayName": "Need-to-Know Applies"}},
            {"name": "audit_all_access", "type": "bool", "index": 5, "annotations": {"displayName": "Audit All Access"}},
        ]),
        ("fsi-risk-classification", "Risk Data Classification", "Risk management tagging", [
            {"name": "risk_category", "type": "enum", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Risk Category"},
             "enumValues": [{"name": "Credit Risk", "index": 1}, {"name": "Market Risk", "index": 2}, {"name": "Operational Risk", "index": 3}, {"name": "Liquidity Risk", "index": 4}, {"name": "Compliance Risk", "index": 5}, {"name": "Not Risk Data", "index": 6}]},
            {"name": "model_dependency", "type": "enum", "index": 2, "annotations": {"displayName": "Model Dependency"},
             "enumValues": [{"name": "Model Input", "index": 1}, {"name": "Model Output", "index": 2}, {"name": "Model Calibration", "index": 3}, {"name": "Not Model Related", "index": 4}]},
            {"name": "materiality_level", "type": "enum", "index": 3, "annotations": {"displayName": "Materiality Level"},
             "enumValues": [{"name": "Material", "index": 1}, {"name": "Significant", "index": 2}, {"name": "Moderate", "index": 3}, {"name": "Immaterial", "index": 4}]},
            {"name": "sox_relevant", "type": "bool", "index": 4, "annotations": {"displayName": "SOX Relevant"}},
        ]),
        ("fsi-regulatory-reporting", "Regulatory Reporting Mapping", "Maps data to regulatory reports", [
            {"name": "report_name", "type": "string", "index": 1, "annotations": {"displayName": "Report Name"}},
            {"name": "filing_frequency", "type": "enum", "index": 2, "annotations": {"displayName": "Filing Frequency"},
             "enumValues": [{"name": "Daily", "index": 1}, {"name": "Monthly", "index": 2}, {"name": "Quarterly", "index": 3}, {"name": "Semi-Annual", "index": 4}, {"name": "Annual", "index": 5}, {"name": "Ad Hoc", "index": 6}]},
            {"name": "regulatory_body", "type": "enum", "index": 3, "annotations": {"displayName": "Regulatory Body"},
             "enumValues": [{"name": "OCC", "index": 1}, {"name": "Federal Reserve", "index": 2}, {"name": "FDIC", "index": 3}, {"name": "SEC", "index": 4}, {"name": "FINRA", "index": 5}, {"name": "FinCEN", "index": 6}, {"name": "CFPB", "index": 7}, {"name": "State Regulator", "index": 8}]},
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
        ("atlas-core-banking", "ATLAS Core Banking (DB2)", "IBM DB2 mainframe entries for ATLAS"),
        ("fortuna-wealth-mgmt", "FORTUNA Wealth Management (Temenos)", "Temenos T24 entries for FORTUNA"),
        ("argus-finance-risk", "ARGUS Finance & Risk (SAP)", "SAP S/4HANA entries for ARGUS"),
    ]

    logger.info("Creating %d entry groups...", len(entry_groups))
    for eg_id, name, desc in entry_groups:
        for attempt in range(5):
            try:
                result = api_call(f"{DP}/projects/{pid}/locations/{loc}/entryGroups?entryGroupId={eg_id}", "POST", {
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

    logger.info("Dataplex infrastructure complete")


if __name__ == "__main__":
    main()
