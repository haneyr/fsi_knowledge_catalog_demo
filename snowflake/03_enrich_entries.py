#!/usr/bin/env python3
"""Enriches Snowflake KC entries with glossary links, custom aspects, and NEXUS lineage.

Must run after 02_ingest_metadata.py so entries exist in Knowledge Catalog.

Usage: python3 snowflake/03_enrich_entries.py
"""

import logging
import time

from common_snowflake import (
    DATABASE, SCHEMAS, TABLES,
    load_snowflake_config, api_call, DATAPLEX_URL, LINEAGE_URL,
)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from common import set_entry_aspect, glossary_term_entry

logger = logging.getLogger(__name__)


def snowflake_table_entry(cfg, schema, table):
    """Build the Dataplex entry path for a Snowflake table."""
    pid = cfg["project_id"]
    loc = cfg["location"]
    return f"projects/{pid}/locations/{loc}/entryGroups/snowflake-nexus/entries/snowflake-table-{DATABASE.lower()}-{schema.lower()}-{table.lower()}"


GLOSSARY_LINKS = {
    ("SECURITIES", "SECURITY_PRICES"): [
        ("cusip", "cusip"),
        ("isin", "isin"),
    ],
    ("SECURITIES", "SECURITY_FUNDAMENTALS"): [
        ("cusip", "cusip"),
    ],
    ("SECURITIES", "CORPORATE_ACTIONS"): [
        ("cusip", "cusip"),
    ],
    ("INDICES", "BENCHMARK_RETURNS"): [
        ("benchmark_name", "sharpe-ratio"),
    ],
    ("ECONOMICS", "INTEREST_RATE_CURVES"): [
        ("rate_pct", "nim-abbr"),
    ],
    ("RISK_ANALYTICS", "CREDIT_SPREADS"): [
        ("rating", "risk-rating"),
    ],
}


def apply_glossary_links(cfg):
    """Create definition links from glossary terms to Snowflake table columns.

    Uses the entryLinks API (same pattern as scripts/01_create_glossary.py).

    NOTE: This currently fails because the snowflake-nexus entry group is in
    us-central1 but the glossary is in the us multi-region. Dataplex requires
    entry links and their referenced entries to be in the same region. The
    entries are still discoverable via KC search based on descriptions and
    column comments. Glossary links will work once the entry group is moved
    to the us multi-region.
    """
    logger.info("=== Linking Snowflake columns to glossary terms ===")
    pid = cfg["project_id"]
    loc = cfg["location"]
    multi = cfg["multi_region"]
    count = 0

    for (schema, table), links in GLOSSARY_LINKS.items():
        entry = snowflake_table_entry(cfg, schema, table)
        for col_name, term_id in links:
            link_id = f"def-{term_id}-sf-{table.lower().replace('_', '-')}-{col_name.replace('_', '-')}"[:63]
            link_url = (
                f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}"
                f"/entryGroups/snowflake-nexus/entryLinks?entryLinkId={link_id}"
            )
            body = {
                "entryLinkType": "projects/dataplex-types/locations/global/entryLinkTypes/definition",
                "entryReferences": [
                    {"name": entry, "type": "SOURCE", "path": f"Schema.{col_name}"},
                    {"name": glossary_term_entry(cfg, term_id), "type": "TARGET"},
                ],
            }
            try:
                api_call(link_url, "POST", body)
                count += 1
            except RuntimeError as e:
                if "409" not in str(e):
                    logger.warning("  Failed to link %s.%s -> %s: %s", table, col_name, term_id, str(e)[:80])
            time.sleep(0.5)

    logger.info("  Created %d glossary links", count)


def apply_custom_aspects(cfg):
    """Apply FSI custom aspects to Snowflake table entries."""
    logger.info("=== Applying custom aspects to Snowflake tables ===")
    count = 0

    for schema in SCHEMAS:
        for table_name, _ in TABLES[schema]:
            entry = snowflake_table_entry(cfg, schema, table_name)

            # Data Classification — market data is generally Internal/Public, no PII
            classification = "Internal"
            if schema == "RISK_ANALYTICS":
                classification = "Confidential"
            elif table_name in ("CORPORATE_ACTIONS", "BENCHMARK_RETURNS", "INDEX_CONSTITUENTS", "INTEREST_RATE_CURVES", "ECONOMIC_INDICATORS"):
                classification = "Public"

            try:
                set_entry_aspect(cfg, entry, "fsi-data-classification", {
                    "classification_level": classification,
                    "pii_category": "Not PII",
                    "requires_encryption": False,
                    "requires_masking": False,
                    "regulatory_scope": "SEC, FINRA" if schema in ("SECURITIES", "INDICES") else "General",
                })
                count += 1
            except RuntimeError as e:
                logger.warning("  Classification failed for %s.%s: %s", schema, table_name, str(e)[:80])

            # Data Retention
            try:
                set_entry_aspect(cfg, entry, "fsi-data-retention", {
                    "retention_period_years": 7 if schema == "RISK_ANALYTICS" else 5,
                    "governing_regulation": "SEC Rule 17a-4" if schema in ("SECURITIES", "INDICES") else "General",
                    "retention_start_event": "Date of market data capture",
                    "archival_required": True,
                    "destruction_method": "Crypto Shredding",
                })
                count += 1
            except RuntimeError as e:
                logger.warning("  Retention failed for %s.%s: %s", schema, table_name, str(e)[:80])

            # Regulatory Compliance
            try:
                set_entry_aspect(cfg, entry, "fsi-regulatory-compliance", {
                    "applicable_regulations": "SEC, FINRA, MiFID II",
                    "compliance_status": "Compliant",
                    "last_audit_date": "2025-11-15",
                    "audit_frequency": "Annual",
                    "compliance_notes": f"External market data from NEXUS vendor ({schema}.{table_name}).",
                })
                count += 1
            except RuntimeError as e:
                logger.warning("  Compliance failed for %s.%s: %s", schema, table_name, str(e)[:80])

            # Data Lineage Metadata
            try:
                set_entry_aspect(cfg, entry, "fsi-data-lineage-metadata", {
                    "source_system": "NEXUS Data Services",
                    "ingestion_method": "API Integration",
                    "refresh_frequency": "End-of-Day" if "DAILY" in str(table_name) or schema != "RISK_ANALYTICS" else "End-of-Day",
                    "data_flow_path": f"NEXUS API -> Snowflake {DATABASE}.{schema}.{table_name}",
                })
                count += 1
            except RuntimeError as e:
                logger.warning("  Lineage metadata failed for %s.%s: %s", schema, table_name, str(e)[:80])

            # Access Control
            try:
                set_entry_aspect(cfg, entry, "fsi-access-control", {
                    "access_level": "Confidential" if schema == "RISK_ANALYTICS" else "Internal",
                    "authorized_roles": "Risk Analyst, Portfolio Manager, Trader, Quant" if schema == "RISK_ANALYTICS" else "Analyst, Portfolio Manager, Operations",
                    "requires_mfa": schema == "RISK_ANALYTICS",
                    "need_to_know_applies": schema == "RISK_ANALYTICS",
                    "audit_all_access": False,
                })
                count += 1
            except RuntimeError as e:
                logger.warning("  Access control failed for %s.%s: %s", schema, table_name, str(e)[:80])

            # Risk Classification
            if schema == "RISK_ANALYTICS":
                try:
                    set_entry_aspect(cfg, entry, "fsi-risk-classification", {
                        "risk_category": "Market Risk",
                        "model_dependency": "Model Input",
                        "materiality_level": "Material",
                        "sox_relevant": True,
                    })
                    count += 1
                except RuntimeError as e:
                    logger.warning("  Risk classification failed for %s.%s: %s", schema, table_name, str(e)[:80])

            time.sleep(0.3)

    logger.info("  Applied %d aspect instances", count)


def create_nexus_lineage(cfg):
    """Create lineage showing NEXUS as a source system feeding market data."""
    logger.info("=== Creating NEXUS source system lineage ===")
    pid = cfg["project_id"]
    base = f"{LINEAGE_URL}/projects/{pid}/locations/{cfg['multi_region']}"
    sf_account = cfg["snowflake_account"]

    process = api_call(f"{base}/processes", "POST", {
        "displayName": "NEXUS Market Data Feed - Snowflake Ingestion",
        "origin": {"sourceType": "CUSTOM", "name": "nexus-market-data-feed"},
    })
    run = api_call(f"{LINEAGE_URL}/{process['name']}/runs", "POST", {
        "displayName": "NEXUS Daily Feed",
        "startTime": "2026-04-30T16:00:00Z",
        "endTime": "2026-04-30T16:30:00Z",
        "state": "COMPLETED",
    })

    links = []
    for schema in SCHEMAS:
        for table_name, _ in TABLES[schema]:
            links.append({
                "source": {"fullyQualifiedName": f"nexus-api:feeds.market_data.{table_name.lower()}"},
                "target": {"fullyQualifiedName": f"snowflake:{sf_account}.{DATABASE}.{schema}.{table_name}"},
            })

    api_call(f"{LINEAGE_URL}/{run['name']}/lineageEvents", "POST", {
        "startTime": "2026-04-30T16:00:00Z",
        "endTime": "2026-04-30T16:30:00Z",
        "links": links,
    })
    logger.info("  Created %d lineage links for NEXUS -> Snowflake", len(links))


def main():
    cfg = load_snowflake_config()
    logger.info("Project: %s", cfg["project_id"])
    apply_glossary_links(cfg)
    apply_custom_aspects(cfg)
    create_nexus_lineage(cfg)
    logger.info("Enrichment complete")


if __name__ == "__main__":
    main()
