#!/usr/bin/env python3
"""Creates Knowledge Catalog entry group, entry types, and aspect types for Snowflake metadata.

Must run before 02_ingest_metadata.py so the import has types to reference.

Usage: python3 snowflake/01_create_dataplex_infra.py
"""

import logging
import time

from common_snowflake import load_snowflake_config, api_call, poll_operation, DATAPLEX_URL

logger = logging.getLogger(__name__)


def main():
    cfg = load_snowflake_config()
    pid = cfg["project_id"]
    loc = cfg["location"]
    multi = cfg["multi_region"]
    DP = DATAPLEX_URL

    # --- Entry Group (in multi-region to match glossary for entry links) ---
    logger.info("Creating entry group: snowflake-nexus (location=%s)", multi)
    for attempt in range(5):
        try:
            result = api_call(
                f"{DP}/projects/{pid}/locations/{multi}/entryGroups?entryGroupId=snowflake-nexus",
                "POST",
                {"displayName": "NEXUS Market Data (Snowflake)", "description": "Snowflake Horizon metadata for NEXUS external market data provider"},
            )
            if "name" in result and "operations" in result.get("name", ""):
                poll_operation(result["name"])
            status = "exists" if result.get("_exists") else "created"
            logger.info("  snowflake-nexus: %s", status)
            break
        except RuntimeError as e:
            if "429" in str(e) and attempt < 4:
                time.sleep(15 * (attempt + 1))
            else:
                raise
    time.sleep(5)

    # --- Entry Types (global so they work with any entry group region) ---
    entry_types = [
        ("snowflake-account", "Snowflake Account", ["DATABASE"], "Snowflake", "Snowflake"),
        ("snowflake-database", "Snowflake Database", ["DATABASE"], "Snowflake", "Snowflake"),
        ("snowflake-schema", "Snowflake Schema", ["DATABASE_SCHEMA"], "Snowflake", "Snowflake"),
        ("snowflake-table", "Snowflake Table", ["TABLE"], "Snowflake", "Snowflake"),
        ("snowflake-view", "Snowflake View", ["TABLE"], "Snowflake", "Snowflake"),
        ("snowflake-tag", "Snowflake Horizon Tag", [], "Snowflake", "Snowflake"),
        ("snowflake-tag-ref", "Snowflake Tag Reference", [], "Snowflake", "Snowflake"),
    ]

    logger.info("Creating %d entry types...", len(entry_types))
    for et_id, name, aliases, platform, system in entry_types:
        for attempt in range(5):
            try:
                result = api_call(
                    f"{DP}/projects/{pid}/locations/global/entryTypes?entryTypeId={et_id}",
                    "POST",
                    {"displayName": name, "description": f"Represents a {name.lower()}", "typeAliases": aliases, "platform": platform, "system": system},
                )
                if "name" in result and "operations" in result.get("name", ""):
                    poll_operation(result["name"])
                status = "exists" if result.get("_exists") else "created"
                logger.info("  %s: %s", et_id, status)
                break
            except RuntimeError as e:
                if "429" in str(e) and attempt < 4:
                    time.sleep(15 * (attempt + 1))
                else:
                    raise
        time.sleep(3)

    # --- Aspect Types ---
    aspect_types = [
        ("snowflake-account", "Snowflake Account", "Marker aspect for Snowflake account entries", []),
        ("snowflake-database", "Snowflake Database", "Marker aspect for Snowflake database entries", []),
        ("snowflake-schema", "Snowflake Schema", "Marker aspect for Snowflake schema entries", []),
        ("snowflake-table", "Snowflake Table", "Structural metadata for Snowflake table entries", []),
        ("snowflake-view", "Snowflake View", "Structural metadata for Snowflake view entries", []),
        ("snowflake-tag", "Snowflake Horizon Tag", "Governance tag definition from Snowflake Horizon", [
            {"name": "tag_name", "type": "string", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Tag Name"}},
            {"name": "allowed_values", "type": "string", "index": 2, "annotations": {"displayName": "Allowed Values"}},
            {"name": "tag_database", "type": "string", "index": 3, "annotations": {"displayName": "Tag Database"}},
            {"name": "tag_schema", "type": "string", "index": 4, "annotations": {"displayName": "Tag Schema"}},
        ]),
        ("snowflake-tag-ref", "Snowflake Tag Reference", "Tag assignment linking a governance tag to an object", [
            {"name": "tag_name", "type": "string", "index": 1, "constraints": {"required": True}, "annotations": {"displayName": "Tag Name"}},
            {"name": "tag_value", "type": "string", "index": 2, "annotations": {"displayName": "Tag Value"}},
            {"name": "object_name", "type": "string", "index": 3, "annotations": {"displayName": "Tagged Object"}},
            {"name": "object_type", "type": "string", "index": 4, "annotations": {"displayName": "Object Type"}},
        ]),
    ]

    logger.info("Creating %d aspect types...", len(aspect_types))
    for at_id, name, desc, fields in aspect_types:
        template = {"name": at_id.replace("-", "_"), "type": "record", "recordFields": fields}
        for attempt in range(5):
            try:
                result = api_call(
                    f"{DP}/projects/{pid}/locations/global/aspectTypes?aspectTypeId={at_id}",
                    "POST",
                    {"displayName": name, "description": desc, "metadataTemplate": template},
                )
                if "name" in result and "operations" in result.get("name", ""):
                    poll_operation(result["name"])
                status = "exists" if result.get("_exists") else "created"
                logger.info("  %s: %s", at_id, status)
                break
            except RuntimeError as e:
                if "429" in str(e) and attempt < 4:
                    time.sleep(15 * (attempt + 1))
                else:
                    raise
        time.sleep(5)

    logger.info("Knowledge Catalog infrastructure for Snowflake complete")


if __name__ == "__main__":
    main()
