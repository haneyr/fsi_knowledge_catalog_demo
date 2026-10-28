#!/usr/bin/env python3
"""Shared utilities for Snowflake NEXUS integration scripts."""

import logging
import os
import sys
from typing import Any, Dict, List, Tuple

import snowflake.connector

# Allow importing from the sibling scripts/ directory
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
)
from common import (  # noqa: E402
    DATAPLEX_URL,
    LINEAGE_URL,
    api_call,
    load_config as load_gcp_config,
    poll_operation,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DATABASE = "NEXUS_MARKET_DATA"
WAREHOUSE = "NEXUS_WH"
ENTRY_GROUP_ID = "retail-nexus-market-intel"

SCHEMAS = ["SYNDICATED_INTEL"]

TABLES: Dict[str, List[Tuple[str, str]]] = {
    "SYNDICATED_INTEL": [
        (
            "nexus_competitor_prices",
            "Daily syndicated competitor retail & promotional prices by GTIN-13, SKU, and competitor chain",
        ),
        (
            "nexus_category_market_share",
            "Monthly syndicated US retail category dollar share, peer gross margin benchmarks, and YoY growth",
        ),
        (
            "nexus_consumer_panel",
            "Anonymized household consumer panel tracking cross-retailer wallet share and trip frequency",
        ),
        (
            "nexus_regional_demand_index",
            "Weekly syndicated regional retail demand velocity, foot-traffic, and weather elasticity by DMA",
        ),
        (
            "nexus_promo_calendar_benchmark",
            "Syndicated seasonal promotional depth, campaign duration, unit lift, and margin erosion benchmarks",
        ),
        (
            "nexus_basket_affinity",
            "Syndicated cross-category basket co-occurrence, attach rate, and affinity lift metrics",
        ),
    ],
}

HORIZON_TAGS: Dict[str, Dict[str, List[str]]] = {
    "DATA_CLASSIFICATION": {
        "allowed_values": ["THIRD_PARTY_LICENSED", "INTERNAL", "PUBLIC"],
    },
    "ACCESS_GOVERNANCE": {
        "allowed_values": ["EXTERNAL_VENDOR_AGREEMENT"],
    },
    "REGULATORY_COMPLIANCE": {
        "allowed_values": ["VENDOR_DATA_LICENSE_NO_PII"],
    },
    "CLOUD_PLATFORM": {
        "allowed_values": ["SNOWFLAKE"],
    },
    "DATA_RESIDENCY": {
        "allowed_values": ["EXTERNAL_NON_GCP"],
    },
}

TAG_ASSIGNMENTS: Dict[str, Dict[str, str]] = {
    tbl: {
        "DATA_CLASSIFICATION": "THIRD_PARTY_LICENSED",
        "ACCESS_GOVERNANCE": "EXTERNAL_VENDOR_AGREEMENT",
        "REGULATORY_COMPLIANCE": "VENDOR_DATA_LICENSE_NO_PII",
        "CLOUD_PLATFORM": "SNOWFLAKE",
        "DATA_RESIDENCY": "EXTERNAL_NON_GCP",
    }
    for tbl, _ in TABLES["SYNDICATED_INTEL"]
}

# Matches BQ formula: CONCAT('0085', LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0'))
# We generate the same GTINs for n=1..500 (subset of the 5000 in BQ)
GTIN_SEED_RANGE = range(1, 501)


def generate_gtin13(n: int) -> str:
    """Generate a 9-digit GTIN matching the BQ formula: CONCAT('0085', LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0'))."""
    return str((n * 7) % 1_000_000_000).zfill(9)


def generate_sku(n: int) -> str:
    """Generate a 12-character SKU: 'US' + gtin_13 + (n % 10)."""
    return f"US{generate_gtin13(n)}{n % 10}"


def us_business_days(start_date: str, count: int) -> list[str]:
    """Generate ``count`` US business days starting from ``start_date`` (YYYY-MM-DD).

    Excludes weekends (Sat/Sun). Does not exclude NYSE holidays for simplicity.
    """
    from datetime import datetime, timedelta

    current = datetime.strptime(start_date, "%Y-%m-%d")
    days: list[str] = []
    while len(days) < count:
        if current.weekday() < 5:  # Mon-Fri
            days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return days


def get_snowflake_connection() -> snowflake.connector.SnowflakeConnection:
    """Connect to Snowflake using the setup-user env vars."""
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", WAREHOUSE),
        database=os.environ.get("SNOWFLAKE_DATABASE", DATABASE),
        role="RETAIL_KC_SETUP_ROLE",
    )


def get_agent_snowflake_connection() -> snowflake.connector.SnowflakeConnection:
    """Connect to Snowflake using the agent-user env vars."""
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_AGENT_USER"],
        password=os.environ["SNOWFLAKE_AGENT_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", WAREHOUSE),
        database=os.environ.get("SNOWFLAKE_DATABASE", DATABASE),
        role="RETAIL_KC_AGENT_ROLE",
    )


def load_snowflake_config() -> Dict[str, str]:
    """Load GCP config from scripts/config.json and add Snowflake env vars."""
    cfg = load_gcp_config()
    cfg["snowflake_account"] = os.environ.get("SNOWFLAKE_ACCOUNT", "")
    cfg["snowflake_database"] = os.environ.get("SNOWFLAKE_DATABASE", DATABASE)
    cfg["snowflake_warehouse"] = os.environ.get("SNOWFLAKE_WAREHOUSE", WAREHOUSE)
    return cfg
