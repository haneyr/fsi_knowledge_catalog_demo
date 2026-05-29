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

SCHEMAS = ["SECURITIES", "INDICES", "ECONOMICS", "RISK_ANALYTICS"]

TABLES: Dict[str, List[Tuple[str, str]]] = {
    "SECURITIES": [
        (
            "SECURITY_PRICES",
            "Daily closing prices by CUSIP/ISIN from NEXUS market data feed",
        ),
        (
            "SECURITY_FUNDAMENTALS",
            "Fundamental metrics: P/E, EPS, market cap, dividend yield",
        ),
        ("CORPORATE_ACTIONS", "Corporate actions: splits, dividends, mergers"),
    ],
    "INDICES": [
        (
            "BENCHMARK_RETURNS",
            "Daily and monthly index returns for major benchmarks",
        ),
        (
            "INDEX_CONSTITUENTS",
            "Constituent securities for each benchmark index",
        ),
    ],
    "ECONOMICS": [
        (
            "INTEREST_RATE_CURVES",
            "SOFR, Fed Funds Effective, Treasury yields (2Y/5Y/10Y/30Y)",
        ),
        (
            "ECONOMIC_INDICATORS",
            "GDP, CPI, unemployment rate, housing starts",
        ),
        ("FX_SPOT_RATES", "Spot FX rates for major currency pairs"),
    ],
    "RISK_ANALYTICS": [
        (
            "CREDIT_SPREADS",
            "Corporate bond spreads by credit rating and sector",
        ),
        (
            "VOLATILITY_SURFACES",
            "Implied volatility surfaces for options pricing",
        ),
    ],
}

HORIZON_TAGS: Dict[str, Dict[str, List[str]]] = {
    "DATA_CLASSIFICATION": {
        "allowed_values": ["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
    },
    "DATA_DOMAIN": {
        "allowed_values": ["MARKET_DATA", "RISK", "ECONOMICS"],
    },
    "DATA_FRESHNESS": {
        "allowed_values": ["REAL_TIME", "DAILY", "MONTHLY"],
    },
    "PII_FLAG": {
        "allowed_values": ["TRUE", "FALSE"],
    },
    "SOURCE_VENDOR": {
        "allowed_values": ["NEXUS_DATA_SERVICES"],
    },
}

TAG_ASSIGNMENTS: Dict[str, Dict[str, str]] = {
    "SECURITY_PRICES": {
        "DATA_CLASSIFICATION": "INTERNAL",
        "DATA_DOMAIN": "MARKET_DATA",
        "DATA_FRESHNESS": "DAILY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
    "SECURITY_FUNDAMENTALS": {
        "DATA_CLASSIFICATION": "INTERNAL",
        "DATA_DOMAIN": "MARKET_DATA",
        "DATA_FRESHNESS": "DAILY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
    "CORPORATE_ACTIONS": {
        "DATA_CLASSIFICATION": "PUBLIC",
        "DATA_DOMAIN": "MARKET_DATA",
        "DATA_FRESHNESS": "DAILY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
    "BENCHMARK_RETURNS": {
        "DATA_CLASSIFICATION": "PUBLIC",
        "DATA_DOMAIN": "MARKET_DATA",
        "DATA_FRESHNESS": "DAILY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
    "INDEX_CONSTITUENTS": {
        "DATA_CLASSIFICATION": "PUBLIC",
        "DATA_DOMAIN": "MARKET_DATA",
        "DATA_FRESHNESS": "MONTHLY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
    "INTEREST_RATE_CURVES": {
        "DATA_CLASSIFICATION": "PUBLIC",
        "DATA_DOMAIN": "ECONOMICS",
        "DATA_FRESHNESS": "DAILY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
    "ECONOMIC_INDICATORS": {
        "DATA_CLASSIFICATION": "PUBLIC",
        "DATA_DOMAIN": "ECONOMICS",
        "DATA_FRESHNESS": "MONTHLY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
    "FX_SPOT_RATES": {
        "DATA_CLASSIFICATION": "INTERNAL",
        "DATA_DOMAIN": "ECONOMICS",
        "DATA_FRESHNESS": "DAILY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
    "CREDIT_SPREADS": {
        "DATA_CLASSIFICATION": "CONFIDENTIAL",
        "DATA_DOMAIN": "RISK",
        "DATA_FRESHNESS": "DAILY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
    "VOLATILITY_SURFACES": {
        "DATA_CLASSIFICATION": "CONFIDENTIAL",
        "DATA_DOMAIN": "RISK",
        "DATA_FRESHNESS": "DAILY",
        "PII_FLAG": "FALSE",
        "SOURCE_VENDOR": "NEXUS_DATA_SERVICES",
    },
}

# Matches BQ formula: LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0')
# We generate the same CUSIPs for n=1..500 (subset of the 5000 in BQ)
CUSIP_SEED_RANGE = range(1, 501)


def generate_cusip(n: int) -> str:
    """Generate a 9-digit CUSIP matching the BQ formula: LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0')."""
    return str((n * 7) % 1_000_000_000).zfill(9)


def generate_isin(n: int) -> str:
    """Generate a 12-character ISIN: 'US' + cusip + (n % 10)."""
    return f"US{generate_cusip(n)}{n % 10}"


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
        role="FSI_KC_SETUP_ROLE",
    )


def get_agent_snowflake_connection() -> snowflake.connector.SnowflakeConnection:
    """Connect to Snowflake using the agent-user env vars."""
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_AGENT_USER"],
        password=os.environ["SNOWFLAKE_AGENT_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", WAREHOUSE),
        database=os.environ.get("SNOWFLAKE_DATABASE", DATABASE),
        role="FSI_KC_AGENT_ROLE",
    )


def load_snowflake_config() -> Dict[str, str]:
    """Load GCP config from scripts/config.json and add Snowflake env vars."""
    cfg = load_gcp_config()
    cfg["snowflake_account"] = os.environ.get("SNOWFLAKE_ACCOUNT", "")
    cfg["snowflake_database"] = os.environ.get("SNOWFLAKE_DATABASE", DATABASE)
    cfg["snowflake_warehouse"] = os.environ.get("SNOWFLAKE_WAREHOUSE", WAREHOUSE)
    return cfg
