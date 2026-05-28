#!/usr/bin/env python3
"""Extracts Horizon metadata from Snowflake and imports into Dataplex Knowledge Catalog.

Queries SNOWFLAKE.ACCOUNT_USAGE views for table/column/tag metadata,
produces a JSONL import file, and calls the Dataplex MetadataJobs API.

Usage: python3 snowflake/02_ingest_metadata.py
"""

import json
import logging
import os
import tempfile
import time

from common_snowflake import (
    DATABASE, WAREHOUSE, SCHEMAS, TABLES,
    get_snowflake_connection, load_snowflake_config,
    api_call, DATAPLEX_URL,
)

logger = logging.getLogger(__name__)


def extract_tables(cur):
    """Extract table metadata from INFORMATION_SCHEMA (more reliable than ACCOUNT_USAGE for structure)."""
    cur.execute(f"""
        SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE, COMMENT
        FROM {DATABASE}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """)
    return cur.fetchall()


def extract_columns(cur):
    """Extract column metadata."""
    cur.execute(f"""
        SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE,
               IS_NULLABLE, COLUMN_DEFAULT, COMMENT, ORDINAL_POSITION
        FROM {DATABASE}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA')
        ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
    """)
    return cur.fetchall()


def extract_tags(cur):
    """Extract Horizon tag definitions from ACCOUNT_USAGE."""
    cur.execute("""
        SELECT TAG_NAME, TAG_DATABASE, TAG_SCHEMA, ALLOWED_VALUES
        FROM SNOWFLAKE.ACCOUNT_USAGE.TAGS
        WHERE TAG_DATABASE = %s AND DELETED IS NULL
    """, (DATABASE,))
    return cur.fetchall()


def extract_tag_references(cur):
    """Extract tag assignments from ACCOUNT_USAGE."""
    cur.execute("""
        SELECT TAG_NAME, TAG_VALUE, OBJECT_DATABASE, OBJECT_SCHEMA,
               OBJECT_NAME, COLUMN_NAME, DOMAIN
        FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
        WHERE OBJECT_DATABASE = %s AND TAG_DATABASE = %s
    """, (DATABASE, DATABASE))
    return cur.fetchall()


def build_import_entries(cfg, tables, columns, tags, tag_refs):
    """Build JSONL entries for Dataplex metadata import."""
    pid = cfg["project_id"]
    loc = cfg["location"]
    sf_account = cfg["snowflake_account"]
    entry_group = f"projects/{pid}/locations/{loc}/entryGroups/snowflake-nexus"
    entries = []

    # Account entry
    entries.append({
        "name": f"{entry_group}/entries/snowflake-account-{sf_account.replace('.', '-')}",
        "entryType": f"projects/{pid}/locations/{loc}/entryTypes/snowflake-account",
        "fullyQualifiedName": f"snowflake:{sf_account}",
        "aspects": {
            f"{pid}.{loc}.snowflake-account": {
                "aspectType": f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-account",
                "data": {},
            }
        },
        "entrySource": {"displayName": f"Snowflake Account: {sf_account}", "description": "NEXUS market data provider Snowflake account"},
    })

    # Database entry
    db_entry_name = f"{entry_group}/entries/snowflake-db-{DATABASE.lower()}"
    entries.append({
        "name": db_entry_name,
        "entryType": f"projects/{pid}/locations/{loc}/entryTypes/snowflake-database",
        "fullyQualifiedName": f"snowflake:{sf_account}.{DATABASE}",
        "parentEntry": entries[0]["name"],
        "aspects": {
            f"{pid}.{loc}.snowflake-database": {
                "aspectType": f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-database",
                "data": {},
            }
        },
        "entrySource": {"displayName": DATABASE, "description": "NEXUS external market data provider database"},
    })

    # Schema entries
    schema_entries = {}
    for schema in SCHEMAS:
        schema_entry_name = f"{entry_group}/entries/snowflake-schema-{DATABASE.lower()}-{schema.lower()}"
        schema_entries[schema] = schema_entry_name
        entries.append({
            "name": schema_entry_name,
            "entryType": f"projects/{pid}/locations/{loc}/entryTypes/snowflake-schema",
            "fullyQualifiedName": f"snowflake:{sf_account}.{DATABASE}.{schema}",
            "parentEntry": db_entry_name,
            "aspects": {
                f"{pid}.{loc}.snowflake-schema": {
                    "aspectType": f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-schema",
                    "data": {},
                }
            },
            "entrySource": {"displayName": schema, "description": f"Schema for {schema.lower().replace('_', ' ')} data"},
        })

    # Group columns by (schema, table)
    col_map = {}
    for row in columns:
        key = (row[0], row[1])
        col_map.setdefault(key, []).append(row)

    # Table entries with schema
    for row in tables:
        schema, table_name, table_type, comment = row[0], row[1], row[2], row[3] or ""
        entry_type_id = "snowflake-view" if "VIEW" in (table_type or "") else "snowflake-table"
        table_entry_name = f"{entry_group}/entries/snowflake-table-{DATABASE.lower()}-{schema.lower()}-{table_name.lower()}"

        # Build schema aspect with column info
        # Dataplex metadataType is an enum: STRING, NUMBER, BOOLEAN, TIMESTAMP, DATE, etc.
        _SF_TO_DATAPLEX_TYPE = {
            "TEXT": "STRING", "VARCHAR": "STRING", "CHAR": "STRING", "STRING": "STRING",
            "NUMBER": "NUMBER", "DECIMAL": "NUMBER", "NUMERIC": "NUMBER", "INT": "NUMBER",
            "INTEGER": "NUMBER", "BIGINT": "NUMBER", "FLOAT": "NUMBER", "DOUBLE": "NUMBER",
            "BOOLEAN": "BOOLEAN",
            "DATE": "DATE",
            "TIMESTAMP_TZ": "TIMESTAMP", "TIMESTAMP_LTZ": "TIMESTAMP",
            "TIMESTAMP_NTZ": "TIMESTAMP", "TIMESTAMP": "TIMESTAMP",
        }
        table_columns = col_map.get((schema, table_name), [])
        schema_fields = []
        for col in table_columns:
            sf_type = col[5] or "STRING"
            metadata_type = _SF_TO_DATAPLEX_TYPE.get(sf_type.split("(")[0].upper(), "STRING")
            field = {
                "name": col[2],
                "mode": "NULLABLE" if col[4] == "YES" else "REQUIRED",
                "dataType": sf_type,
                "metadataType": metadata_type,
            }
            if col[6]:
                field["description"] = col[6]
            schema_fields.append(field)

        entry = {
            "name": table_entry_name,
            "entryType": f"projects/{pid}/locations/{loc}/entryTypes/{entry_type_id}",
            "fullyQualifiedName": f"snowflake:{sf_account}.{DATABASE}.{schema}.{table_name}",
            "parentEntry": schema_entries.get(schema, db_entry_name),
            "aspects": {
                f"{pid}.{loc}.{entry_type_id}": {
                    "aspectType": f"projects/{pid}/locations/{loc}/aspectTypes/{entry_type_id}",
                    "data": {},
                }
            },
            "entrySource": {
                "displayName": table_name,
                "description": comment or f"Snowflake table {DATABASE}.{schema}.{table_name}",
            },
        }

        if schema_fields:
            entry["aspects"][f"dataplex-types.global.schema"] = {
                "aspectType": "projects/dataplex-types/locations/global/aspectTypes/schema",
                "data": {"fields": schema_fields},
            }

        entries.append(entry)

    # Tag entries
    for row in tags:
        tag_name, tag_db, tag_schema, allowed = row[0], row[1], row[2], row[3]
        tag_entry_name = f"{entry_group}/entries/snowflake-tag-{tag_name.lower()}"
        entries.append({
            "name": tag_entry_name,
            "entryType": f"projects/{pid}/locations/{loc}/entryTypes/snowflake-tag",
            "fullyQualifiedName": f"snowflake:{sf_account}.{DATABASE}.tag.{tag_name}",
            "aspects": {
                f"{pid}.{loc}.snowflake-tag": {
                    "aspectType": f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-tag",
                    "data": {
                        "tag_name": tag_name,
                        "allowed_values": str(allowed) if allowed else "",
                        "tag_database": tag_db or "",
                        "tag_schema": tag_schema or "",
                    },
                }
            },
            "entrySource": {"displayName": f"Tag: {tag_name}", "description": f"Snowflake Horizon governance tag: {tag_name}"},
        })

    # Tag reference entries
    for i, row in enumerate(tag_refs):
        tag_name, tag_value = row[0], row[1]
        obj_db, obj_schema, obj_name = row[2], row[3], row[4]
        domain = row[6] if len(row) > 6 else "TABLE"
        ref_entry_name = f"{entry_group}/entries/snowflake-tagref-{tag_name.lower()}-{obj_name.lower()}-{i}"
        entries.append({
            "name": ref_entry_name,
            "entryType": f"projects/{pid}/locations/{loc}/entryTypes/snowflake-tag-ref",
            "fullyQualifiedName": f"snowflake:{sf_account}.{DATABASE}.tagref.{tag_name}.{obj_name}.{i}",
            "aspects": {
                f"{pid}.{loc}.snowflake-tag-ref": {
                    "aspectType": f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-tag-ref",
                    "data": {
                        "tag_name": tag_name,
                        "tag_value": tag_value or "",
                        "object_name": f"{obj_db}.{obj_schema}.{obj_name}",
                        "object_type": domain or "TABLE",
                    },
                }
            },
            "entrySource": {"displayName": f"{tag_name}={tag_value} on {obj_name}", "description": f"Tag assignment: {tag_name}={tag_value} on {obj_schema}.{obj_name}"},
        })

    return entries


def write_jsonl(entries, path):
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    logger.info("Wrote %d entries to %s", len(entries), path)


def import_metadata(cfg, jsonl_path):
    """Call Dataplex MetadataJobs API to import the JSONL file."""
    pid = cfg["project_id"]
    loc = cfg["location"]

    with open(jsonl_path) as f:
        entries = [json.loads(line) for line in f]

    entry_group = f"projects/{pid}/locations/{loc}/entryGroups/snowflake-nexus"

    import_body = {
        "type": "IMPORT",
        "importSpec": {
            "sourceStorageUri": "",
            "scope": {
                "entryGroups": [entry_group],
                "entryTypes": [
                    f"projects/{pid}/locations/{loc}/entryTypes/snowflake-account",
                    f"projects/{pid}/locations/{loc}/entryTypes/snowflake-database",
                    f"projects/{pid}/locations/{loc}/entryTypes/snowflake-schema",
                    f"projects/{pid}/locations/{loc}/entryTypes/snowflake-table",
                    f"projects/{pid}/locations/{loc}/entryTypes/snowflake-view",
                    f"projects/{pid}/locations/{loc}/entryTypes/snowflake-tag",
                    f"projects/{pid}/locations/{loc}/entryTypes/snowflake-tag-ref",
                ],
                "aspectTypes": [
                    f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-account",
                    f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-database",
                    f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-schema",
                    f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-table",
                    f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-view",
                    f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-tag",
                    f"projects/{pid}/locations/{loc}/aspectTypes/snowflake-tag-ref",
                    "projects/dataplex-types/locations/global/aspectTypes/schema",
                ],
            },
            "entrySyncMode": "FULL",
            "aspectSyncMode": "INCREMENTAL",
        },
        "importEntries": entries,
    }

    # Use the entries API to create/update entries directly since we have them in memory
    logger.info("Importing %d entries into Dataplex...", len(entries))
    success = 0
    for entry in entries:
        entry_id = entry["name"].split("/entries/")[-1]
        eg = entry["name"].split("/entries/")[0]
        url = f"{DATAPLEX_URL}/{eg}/entries?entryId={entry_id}"

        body = {k: v for k, v in entry.items() if k != "name"}
        try:
            result = api_call(url, "POST", body)
            if result.get("_exists"):
                # Update existing entry
                update_url = f"{DATAPLEX_URL}/{entry['name']}?updateMask=aspects,entrySource&deleteMissingAspects=false"
                api_call(update_url, "PATCH", body)
            success += 1
        except RuntimeError as e:
            logger.warning("  Failed to import %s: %s", entry_id, str(e)[:100])
        time.sleep(0.3)

    logger.info("Imported %d/%d entries", success, len(entries))


def main():
    cfg = load_snowflake_config()
    logger.info("=== Ingesting Snowflake Horizon metadata into Dataplex ===")

    conn = get_snowflake_connection()
    cur = conn.cursor()
    try:
        tables = extract_tables(cur)
        columns = extract_columns(cur)
        tags = extract_tags(cur)
        tag_refs = extract_tag_references(cur)
        logger.info("Extracted: %d tables, %d columns, %d tags, %d tag refs",
                     len(tables), len(columns), len(tags), len(tag_refs))
    finally:
        cur.close()
        conn.close()

    entries = build_import_entries(cfg, tables, columns, tags, tag_refs)

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    jsonl_path = os.path.join(output_dir, "nexus_metadata.jsonl")
    write_jsonl(entries, jsonl_path)

    import_metadata(cfg, jsonl_path)
    logger.info("=== Metadata ingestion complete ===")


if __name__ == "__main__":
    main()
