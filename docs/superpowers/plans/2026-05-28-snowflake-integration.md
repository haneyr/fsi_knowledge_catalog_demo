# Snowflake NEXUS Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional Snowflake module that creates a NEXUS market data source system in Snowflake, ingests its metadata into Knowledge Catalog via the Horizon connector pattern, and gives the KC agent a `query_snowflake` tool to query Snowflake data discovered through KC.

**Architecture:** A self-contained `snowflake/` directory with 4 numbered Python scripts (data setup, Dataplex infra, metadata ingestion, enrichment), a deploy script, and a shared helper module. The KC agent conditionally registers a `query_snowflake` tool when `SNOWFLAKE_ACCOUNT` is set. All existing functionality is unchanged when Snowflake is not configured.

**Tech Stack:** Python 3.12, `snowflake-connector-python`, Dataplex REST API, Dataplex Import API, Data Lineage API, BigQuery API (via `scripts/common.py`)

**Spec:** `docs/superpowers/specs/2026-05-28-snowflake-integration-design.md`

---

## File Map

### New files

| File | Responsibility |
|---|---|
| `snowflake/common_snowflake.py` | Snowflake connection helper, config loader, shared constants (table definitions, CUSIP generator) |
| `snowflake/00_setup_nexus_data.py` | Creates warehouse, database, schemas, tables, synthetic data, Horizon tags in Snowflake |
| `snowflake/01_create_dataplex_infra.py` | Creates entry group, entry types, aspect types in Dataplex for Snowflake metadata |
| `snowflake/02_ingest_metadata.py` | Extracts Horizon metadata from Snowflake, produces JSONL, calls Dataplex Import API |
| `snowflake/03_enrich_entries.py` | Links Snowflake KC entries to glossary terms, applies custom aspects, creates NEXUS lineage |
| `snowflake/deploy.sh` | Orchestrates all Snowflake setup steps |
| `snowflake/requirements.txt` | `snowflake-connector-python>=3.0` |
| `snowflake/README.md` | Snowflake-specific setup instructions, user creation SQL, env vars, Secret Manager note |

### Modified files

| File | What changes |
|---|---|
| `agents/agent_kc/agent.py` | Conditional `query_snowflake` tool, system prompt extension |
| `agents/deploy_agents.sh` | Add Snowflake env vars to `agent_kc/.env` when enabled |
| `deploy-full.sh` | Conditional `bash snowflake/deploy.sh` step |
| `README.md` | Snowflake section with setup instructions |
| `demo/demo_questions.md` | Category 7: Multi-Cloud Discovery (4 scenarios) |
| `eval/test_cases.yaml` | 4 multi-cloud test cases |
| `eval/run_eval.py` | Skip multi-cloud cases when Snowflake not configured |
| `pyproject.toml` | Optional `snowflake` dependency group |

---

## Task 1: Snowflake Connection Helper & Constants

**Files:**
- Create: `snowflake/common_snowflake.py`
- Create: `snowflake/requirements.txt`

This module provides the Snowflake connection, config loading, and the table/column definitions that all other scripts reference. It also contains the CUSIP generator that matches the BQ formula exactly.

- [ ] **Step 1: Create `snowflake/requirements.txt`**

```
snowflake-connector-python>=3.0
```

- [ ] **Step 2: Create `snowflake/common_snowflake.py`**

```python
#!/usr/bin/env python3
"""Shared utilities for Snowflake NEXUS integration scripts."""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

import snowflake.connector

# Allow importing from the sibling scripts/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from common import load_config as load_gcp_config, api_call, poll_operation, DATAPLEX_URL, LINEAGE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATABASE = "NEXUS_MARKET_DATA"
WAREHOUSE = "NEXUS_WH"

SCHEMAS = ["SECURITIES", "INDICES", "ECONOMICS", "RISK_ANALYTICS"]

TABLES: Dict[str, List[Tuple[str, str]]] = {
    "SECURITIES": [
        ("SECURITY_PRICES", "Daily closing prices by CUSIP/ISIN from NEXUS market data feed"),
        ("SECURITY_FUNDAMENTALS", "Fundamental metrics: P/E, EPS, market cap, dividend yield"),
        ("CORPORATE_ACTIONS", "Corporate actions: splits, dividends, mergers"),
    ],
    "INDICES": [
        ("BENCHMARK_RETURNS", "Daily and monthly index returns for major benchmarks"),
        ("INDEX_CONSTITUENTS", "Constituent securities for each benchmark index"),
    ],
    "ECONOMICS": [
        ("INTEREST_RATE_CURVES", "SOFR, Fed Funds Effective, Treasury yields (2Y/5Y/10Y/30Y)"),
        ("ECONOMIC_INDICATORS", "GDP, CPI, unemployment rate, housing starts"),
        ("FX_SPOT_RATES", "Spot FX rates for major currency pairs"),
    ],
    "RISK_ANALYTICS": [
        ("CREDIT_SPREADS", "Corporate bond spreads by credit rating and sector"),
        ("VOLATILITY_SURFACES", "Implied volatility surfaces for options pricing"),
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
    "SECURITY_PRICES": {"DATA_CLASSIFICATION": "INTERNAL", "DATA_DOMAIN": "MARKET_DATA", "DATA_FRESHNESS": "DAILY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
    "SECURITY_FUNDAMENTALS": {"DATA_CLASSIFICATION": "INTERNAL", "DATA_DOMAIN": "MARKET_DATA", "DATA_FRESHNESS": "DAILY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
    "CORPORATE_ACTIONS": {"DATA_CLASSIFICATION": "PUBLIC", "DATA_DOMAIN": "MARKET_DATA", "DATA_FRESHNESS": "DAILY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
    "BENCHMARK_RETURNS": {"DATA_CLASSIFICATION": "PUBLIC", "DATA_DOMAIN": "MARKET_DATA", "DATA_FRESHNESS": "DAILY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
    "INDEX_CONSTITUENTS": {"DATA_CLASSIFICATION": "PUBLIC", "DATA_DOMAIN": "MARKET_DATA", "DATA_FRESHNESS": "MONTHLY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
    "INTEREST_RATE_CURVES": {"DATA_CLASSIFICATION": "PUBLIC", "DATA_DOMAIN": "ECONOMICS", "DATA_FRESHNESS": "DAILY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
    "ECONOMIC_INDICATORS": {"DATA_CLASSIFICATION": "PUBLIC", "DATA_DOMAIN": "ECONOMICS", "DATA_FRESHNESS": "MONTHLY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
    "FX_SPOT_RATES": {"DATA_CLASSIFICATION": "INTERNAL", "DATA_DOMAIN": "ECONOMICS", "DATA_FRESHNESS": "DAILY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
    "CREDIT_SPREADS": {"DATA_CLASSIFICATION": "CONFIDENTIAL", "DATA_DOMAIN": "RISK", "DATA_FRESHNESS": "DAILY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
    "VOLATILITY_SURFACES": {"DATA_CLASSIFICATION": "CONFIDENTIAL", "DATA_DOMAIN": "RISK", "DATA_FRESHNESS": "DAILY", "PII_FLAG": "FALSE", "SOURCE_VENDOR": "NEXUS_DATA_SERVICES"},
}

# Matches BQ formula: LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0')
# We generate the same CUSIPs for n=1..500 (subset of the 5000 in BQ)
CUSIP_SEED_RANGE = range(1, 501)


def generate_cusip(n: int) -> str:
    return str((n * 7) % 1_000_000_000).zfill(9)


def generate_isin(n: int) -> str:
    return f"US{generate_cusip(n)}{n % 10}"


def us_business_days(start_date: str, count: int) -> list[str]:
    """Generate `count` US business days starting from `start_date` (YYYY-MM-DD).
    Excludes weekends. Does not exclude NYSE holidays for simplicity, but
    avoids generating data on Saturdays/Sundays.
    """
    from datetime import datetime, timedelta
    current = datetime.strptime(start_date, "%Y-%m-%d")
    days = []
    while len(days) < count:
        if current.weekday() < 5:  # Mon-Fri
            days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return days


def get_snowflake_connection() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", WAREHOUSE),
        database=os.environ.get("SNOWFLAKE_DATABASE", DATABASE),
    )


def get_agent_snowflake_connection() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_AGENT_USER"],
        password=os.environ["SNOWFLAKE_AGENT_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", WAREHOUSE),
        database=os.environ.get("SNOWFLAKE_DATABASE", DATABASE),
    )


def load_snowflake_config() -> Dict[str, str]:
    """Load GCP config and add Snowflake env vars."""
    cfg = load_gcp_config()
    cfg["snowflake_account"] = os.environ.get("SNOWFLAKE_ACCOUNT", "")
    cfg["snowflake_database"] = os.environ.get("SNOWFLAKE_DATABASE", DATABASE)
    cfg["snowflake_warehouse"] = os.environ.get("SNOWFLAKE_WAREHOUSE", WAREHOUSE)
    return cfg
```

- [ ] **Step 3: Verify the CUSIP generator matches BigQuery**

Run this in Python to confirm alignment:
```bash
python3 -c "
import sys; sys.path.insert(0, 'snowflake')
from common_snowflake import generate_cusip, generate_isin
# BQ formula: LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0')
assert generate_cusip(1) == '000000007'
assert generate_cusip(100) == '000000700'
assert generate_cusip(1000) == '000007000'
assert generate_isin(1) == 'US0000000071'
print('CUSIP/ISIN generators match BQ formula')
"
```

Expected: `CUSIP/ISIN generators match BQ formula`

- [ ] **Step 4: Commit**

```bash
git add snowflake/common_snowflake.py snowflake/requirements.txt
git commit -m "Add Snowflake connection helper and shared constants for NEXUS integration"
```

---

## Task 2: Snowflake Data Setup Script

**Files:**
- Create: `snowflake/00_setup_nexus_data.py`

Creates the NEXUS_MARKET_DATA database, 4 schemas, ~10 tables with synthetic data, warehouse, and Horizon governance tags. This is the longest script — it contains all the DDL and INSERT statements.

- [ ] **Step 1: Create `snowflake/00_setup_nexus_data.py`**

```python
#!/usr/bin/env python3
"""Creates NEXUS market data database, tables, synthetic data, and Horizon tags in Snowflake.

Requires SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD env vars.
The user must have FSI_KC_SETUP_ROLE (CREATE DATABASE, CREATE WAREHOUSE, APPLY TAG).

Usage: python3 snowflake/00_setup_nexus_data.py
"""

import logging
import random

from common_snowflake import (
    DATABASE, WAREHOUSE, SCHEMAS, TABLES, HORIZON_TAGS, TAG_ASSIGNMENTS,
    generate_cusip, generate_isin, us_business_days, get_snowflake_connection,
    CUSIP_SEED_RANGE,
)

logger = logging.getLogger(__name__)

BENCHMARKS = [
    "S&P 500", "Russell 2000", "MSCI EAFE", "Bloomberg US Agg",
    "MSCI Emerging Markets", "FTSE 100", "Nikkei 225",
]

RATE_INSTRUMENTS = [
    ("SOFR", "Secured Overnight Financing Rate"),
    ("FED_FUNDS", "Federal Funds Effective Rate"),
    ("UST_2Y", "US Treasury 2-Year Yield"),
    ("UST_5Y", "US Treasury 5-Year Yield"),
    ("UST_10Y", "US Treasury 10-Year Yield"),
    ("UST_30Y", "US Treasury 30-Year Yield"),
]

SECTORS = [
    "Technology", "Healthcare", "Financials", "Energy",
    "Consumer Discretionary", "Industrials", "Utilities", "Real Estate",
]

CURRENCIES = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD"]

ECONOMIC_SERIES = [
    ("GDP_GROWTH_QOQ", "GDP Growth Rate (QoQ)", "Quarterly"),
    ("CPI_YOY", "Consumer Price Index (YoY)", "Monthly"),
    ("UNEMPLOYMENT_RATE", "Unemployment Rate", "Monthly"),
    ("HOUSING_STARTS", "Housing Starts (thousands)", "Monthly"),
    ("RETAIL_SALES_MOM", "Retail Sales (MoM)", "Monthly"),
    ("PMI_MANUFACTURING", "PMI Manufacturing Index", "Monthly"),
]


def create_infrastructure(cur):
    logger.info("Creating warehouse and database...")
    cur.execute(f"CREATE WAREHOUSE IF NOT EXISTS {WAREHOUSE} WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE")
    cur.execute(f"USE WAREHOUSE {WAREHOUSE}")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    cur.execute(f"USE DATABASE {DATABASE}")
    for schema in SCHEMAS:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")


def create_tables(cur):
    logger.info("Creating tables...")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.SECURITIES.SECURITY_PRICES (
        price_date       DATE NOT NULL,
        cusip            VARCHAR(9) NOT NULL,
        isin             VARCHAR(12),
        ticker           VARCHAR(10),
        security_name    VARCHAR(100),
        close_price      DECIMAL(18,4),
        open_price       DECIMAL(18,4),
        high_price       DECIMAL(18,4),
        low_price        DECIMAL(18,4),
        volume           BIGINT,
        market_cap_mm    DECIMAL(18,2),
        currency         VARCHAR(3) DEFAULT 'USD',
        exchange         VARCHAR(20),
        as_of_timestamp  TIMESTAMP_TZ DEFAULT '2026-04-30 16:00:00 -0400'
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.SECURITIES.SECURITY_PRICES IS 'Daily closing prices by CUSIP/ISIN from NEXUS market data feed. Join to BigQuery silver_holdings on CUSIP for portfolio valuation.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.SECURITIES.SECURITY_FUNDAMENTALS (
        as_of_date       DATE NOT NULL,
        cusip            VARCHAR(9) NOT NULL,
        pe_ratio         DECIMAL(10,2),
        eps              DECIMAL(10,4),
        market_cap_mm    DECIMAL(18,2),
        dividend_yield   DECIMAL(8,4),
        beta             DECIMAL(8,4),
        sector           VARCHAR(50),
        industry         VARCHAR(100),
        sp_rating        VARCHAR(5)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.SECURITIES.SECURITY_FUNDAMENTALS IS 'Fundamental metrics per security: P/E, EPS, market cap, dividend yield, beta.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.SECURITIES.CORPORATE_ACTIONS (
        action_date      DATE NOT NULL,
        cusip            VARCHAR(9) NOT NULL,
        action_type      VARCHAR(20),
        description      VARCHAR(200),
        ratio            DECIMAL(10,4),
        amount           DECIMAL(18,4),
        currency         VARCHAR(3) DEFAULT 'USD'
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.SECURITIES.CORPORATE_ACTIONS IS 'Corporate actions: stock splits, dividend declarations, mergers and acquisitions.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.INDICES.BENCHMARK_RETURNS (
        return_date      DATE NOT NULL,
        benchmark_name   VARCHAR(50) NOT NULL,
        daily_return     DECIMAL(10,6),
        mtd_return       DECIMAL(10,6),
        qtd_return       DECIMAL(10,6),
        ytd_return       DECIMAL(10,6),
        trailing_1y      DECIMAL(10,6)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.INDICES.BENCHMARK_RETURNS IS 'Daily and period returns for major benchmark indices. Join to BigQuery gold_portfolio_performance on benchmark name.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.INDICES.INDEX_CONSTITUENTS (
        as_of_date       DATE NOT NULL,
        benchmark_name   VARCHAR(50) NOT NULL,
        cusip            VARCHAR(9) NOT NULL,
        weight_pct       DECIMAL(8,4),
        sector           VARCHAR(50)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.INDICES.INDEX_CONSTITUENTS IS 'Constituent securities and weights for each benchmark index.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.ECONOMICS.INTEREST_RATE_CURVES (
        rate_date        DATE NOT NULL,
        instrument       VARCHAR(20) NOT NULL,
        instrument_name  VARCHAR(100),
        rate_pct         DECIMAL(8,4),
        change_bps       DECIMAL(8,2),
        as_of_timestamp  TIMESTAMP_TZ DEFAULT '2026-04-30 16:00:00 -0400'
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.ECONOMICS.INTEREST_RATE_CURVES IS 'SOFR, Fed Funds Effective, and Treasury yields (2Y/5Y/10Y/30Y). Join to BigQuery gold_net_interest_margin on date for NIM sensitivity analysis.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.ECONOMICS.ECONOMIC_INDICATORS (
        report_date      DATE NOT NULL,
        series_id        VARCHAR(30) NOT NULL,
        series_name      VARCHAR(100),
        value            DECIMAL(12,4),
        period_type      VARCHAR(10),
        revision         VARCHAR(20) DEFAULT 'Final'
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.ECONOMICS.ECONOMIC_INDICATORS IS 'Key economic indicators: GDP, CPI, unemployment, housing starts, retail sales, PMI.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.ECONOMICS.FX_SPOT_RATES (
        rate_date        DATE NOT NULL,
        currency_pair    VARCHAR(10) NOT NULL,
        mid_rate         DECIMAL(12,6),
        bid              DECIMAL(12,6),
        ask              DECIMAL(12,6),
        daily_change_pct DECIMAL(8,4)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.ECONOMICS.FX_SPOT_RATES IS 'Spot FX rates for major currency pairs. Complements BigQuery bronze_fx_rates with intraday snapshots.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.RISK_ANALYTICS.CREDIT_SPREADS (
        spread_date      DATE NOT NULL,
        rating           VARCHAR(5) NOT NULL,
        sector           VARCHAR(50) NOT NULL,
        spread_bps       DECIMAL(10,2),
        change_1d_bps    DECIMAL(8,2),
        change_1w_bps    DECIMAL(8,2),
        change_1m_bps    DECIMAL(8,2)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.RISK_ANALYTICS.CREDIT_SPREADS IS 'Corporate bond spreads by credit rating and sector. Join to BigQuery gold_market_risk_var for credit spread exposure analysis.'")

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.RISK_ANALYTICS.VOLATILITY_SURFACES (
        as_of_date       DATE NOT NULL,
        underlying_cusip VARCHAR(9),
        expiry_days      INT,
        strike_pct       DECIMAL(8,2),
        implied_vol      DECIMAL(8,4),
        delta            DECIMAL(8,4)
    )
    """)
    cur.execute(f"COMMENT ON TABLE {DATABASE}.RISK_ANALYTICS.VOLATILITY_SURFACES IS 'Implied volatility surfaces for options pricing across maturities and strikes.'")

    # Add column comments for key join columns
    cur.execute(f"COMMENT ON COLUMN {DATABASE}.SECURITIES.SECURITY_PRICES.CUSIP IS 'CUSIP identifier — matches BigQuery ref_cusip_master.cusip and silver_holdings.cusip'")
    cur.execute(f"COMMENT ON COLUMN {DATABASE}.SECURITIES.SECURITY_PRICES.ISIN IS 'ISIN identifier — matches BigQuery ref_isin_mapping.isin'")
    cur.execute(f"COMMENT ON COLUMN {DATABASE}.INDICES.BENCHMARK_RETURNS.BENCHMARK_NAME IS 'Benchmark name — matches BigQuery gold_portfolio_performance.benchmark_name'")
    cur.execute(f"COMMENT ON COLUMN {DATABASE}.ECONOMICS.INTEREST_RATE_CURVES.INSTRUMENT IS 'Rate instrument code: SOFR, FED_FUNDS, UST_2Y, UST_5Y, UST_10Y, UST_30Y'")


def populate_data(cur):
    logger.info("Populating synthetic data...")
    rng = random.Random(42)
    biz_days = us_business_days("2025-11-03", 120)  # ~6 months of business days

    # SECURITY_PRICES: 500 CUSIPs x 120 days = 60,000 rows (batched)
    logger.info("  SECURITY_PRICES...")
    cusips = [(n, generate_cusip(n), generate_isin(n)) for n in CUSIP_SEED_RANGE]
    batch = []
    for day in biz_days:
        for n, cusip, isin in cusips:
            base = 20 + (n % 300)
            close = round(base + rng.gauss(0, base * 0.02), 4)
            open_p = round(close * (1 + rng.gauss(0, 0.005)), 4)
            high_p = round(max(close, open_p) * (1 + abs(rng.gauss(0, 0.003))), 4)
            low_p = round(min(close, open_p) * (1 - abs(rng.gauss(0, 0.003))), 4)
            vol = int(abs(rng.gauss(500000, 300000)))
            mcap = round(close * vol * rng.uniform(50, 200) / 1e6, 2)
            exch = ["NYSE", "NASDAQ", "OTC"][n % 3]
            ticker = f"TK{n:04d}"
            name = f"Security-{n}"
            batch.append(f"('{day}','{cusip}','{isin}','{ticker}','{name}',{close},{open_p},{high_p},{low_p},{vol},{mcap},'USD','{exch}','{day} 16:00:00 -0400')")
            if len(batch) >= 5000:
                cur.execute(f"INSERT INTO {DATABASE}.SECURITIES.SECURITY_PRICES VALUES {','.join(batch)}")
                batch = []
    if batch:
        cur.execute(f"INSERT INTO {DATABASE}.SECURITIES.SECURITY_PRICES VALUES {','.join(batch)}")
    logger.info("    %d CUSIPs x %d days", len(cusips), len(biz_days))

    # SECURITY_FUNDAMENTALS: 500 rows (latest)
    logger.info("  SECURITY_FUNDAMENTALS...")
    batch = []
    for n, cusip, _ in cusips:
        pe = round(rng.uniform(5, 50), 2)
        eps = round(rng.uniform(0.5, 20), 4)
        mcap = round(rng.uniform(100, 50000), 2)
        div_yield = round(rng.uniform(0, 0.06), 4)
        beta = round(rng.gauss(1.0, 0.3), 4)
        sector = SECTORS[n % len(SECTORS)]
        rating = ["AAA", "AA", "A", "BBB", "BB"][n % 5]
        batch.append(f"('{biz_days[-1]}','{cusip}',{pe},{eps},{mcap},{div_yield},{beta},'{sector}','Industry-{n % 20}','{rating}')")
    cur.execute(f"INSERT INTO {DATABASE}.SECURITIES.SECURITY_FUNDAMENTALS VALUES {','.join(batch)}")

    # CORPORATE_ACTIONS: ~200 events
    logger.info("  CORPORATE_ACTIONS...")
    batch = []
    for i in range(200):
        n = rng.choice(range(1, 501))
        cusip = generate_cusip(n)
        day = rng.choice(biz_days)
        atype = rng.choice(["DIVIDEND", "DIVIDEND", "SPLIT", "MERGER"])
        desc = {"DIVIDEND": f"Quarterly dividend ${rng.uniform(0.1, 2.0):.2f}/share", "SPLIT": f"{rng.choice([2,3,4])}:1 stock split", "MERGER": "Merger announcement"}[atype]
        ratio = {"DIVIDEND": 1.0, "SPLIT": float(rng.choice([2, 3, 4])), "MERGER": round(rng.uniform(1.1, 1.5), 4)}[atype]
        amt = round(rng.uniform(0.1, 5.0), 4) if atype == "DIVIDEND" else 0
        batch.append(f"('{day}','{cusip}','{atype}','{desc}',{ratio},{amt},'USD')")
    cur.execute(f"INSERT INTO {DATABASE}.SECURITIES.CORPORATE_ACTIONS VALUES {','.join(batch)}")

    # BENCHMARK_RETURNS: 7 benchmarks x 120 days
    logger.info("  BENCHMARK_RETURNS...")
    batch = []
    for day in biz_days:
        for bm in BENCHMARKS:
            daily = round(rng.gauss(0.0003, 0.012), 6)
            mtd = round(rng.gauss(0.005, 0.03), 6)
            qtd = round(rng.gauss(0.02, 0.05), 6)
            ytd = round(rng.gauss(0.08, 0.10), 6)
            t1y = round(rng.gauss(0.10, 0.12), 6)
            batch.append(f"('{day}','{bm}',{daily},{mtd},{qtd},{ytd},{t1y})")
    cur.execute(f"INSERT INTO {DATABASE}.INDICES.BENCHMARK_RETURNS VALUES {','.join(batch)}")

    # INDEX_CONSTITUENTS: latest date, 7 benchmarks x ~50 securities each
    logger.info("  INDEX_CONSTITUENTS...")
    batch = []
    latest = biz_days[-1]
    for bm in BENCHMARKS:
        members = rng.sample(range(1, 501), 50)
        total_w = 0
        for i, n in enumerate(members):
            w = round(rng.uniform(0.5, 5.0), 4)
            total_w += w
            batch.append(f"('{latest}','{bm}','{generate_cusip(n)}',{w},'{SECTORS[n % len(SECTORS)]}')")
    cur.execute(f"INSERT INTO {DATABASE}.INDICES.INDEX_CONSTITUENTS VALUES {','.join(batch)}")

    # INTEREST_RATE_CURVES: 6 instruments x 120 days
    logger.info("  INTEREST_RATE_CURVES...")
    batch = []
    base_rates = {"SOFR": 4.55, "FED_FUNDS": 4.58, "UST_2Y": 3.95, "UST_5Y": 3.80, "UST_10Y": 4.25, "UST_30Y": 4.50}
    for day in biz_days:
        for code, name in RATE_INSTRUMENTS:
            base = base_rates[code]
            rate = round(base + rng.gauss(0, 0.05), 4)
            change = round(rng.gauss(0, 3), 2)
            batch.append(f"('{day}','{code}','{name}',{rate},{change},'{day} 16:00:00 -0400')")
    cur.execute(f"INSERT INTO {DATABASE}.ECONOMICS.INTEREST_RATE_CURVES VALUES {','.join(batch)}")

    # ECONOMIC_INDICATORS: 6 series x ~6 months
    logger.info("  ECONOMIC_INDICATORS...")
    batch = []
    monthly_dates = [d for d in biz_days if d.endswith(("01", "02", "03")) and d[8:10] <= "03"]
    if len(monthly_dates) < 6:
        monthly_dates = biz_days[::20][:6]
    for series_id, series_name, period in ECONOMIC_SERIES:
        base_vals = {"GDP_GROWTH_QOQ": 2.5, "CPI_YOY": 3.2, "UNEMPLOYMENT_RATE": 4.1, "HOUSING_STARTS": 1400, "RETAIL_SALES_MOM": 0.3, "PMI_MANUFACTURING": 52.0}
        for date in monthly_dates:
            val = round(base_vals[series_id] + rng.gauss(0, base_vals[series_id] * 0.05), 4)
            batch.append(f"('{date}','{series_id}','{series_name}',{val},'{period}','Final')")
    cur.execute(f"INSERT INTO {DATABASE}.ECONOMICS.ECONOMIC_INDICATORS VALUES {','.join(batch)}")

    # FX_SPOT_RATES: 6 pairs x 120 days
    logger.info("  FX_SPOT_RATES...")
    batch = []
    base_fx = {"EUR/USD": 1.08, "GBP/USD": 1.27, "USD/JPY": 155.0, "USD/CHF": 0.88, "AUD/USD": 0.65, "USD/CAD": 1.37}
    for day in biz_days:
        for pair in CURRENCIES:
            mid = round(base_fx[pair] * (1 + rng.gauss(0, 0.003)), 6)
            spread = mid * 0.0002
            batch.append(f"('{day}','{pair}',{mid},{round(mid - spread, 6)},{round(mid + spread, 6)},{round(rng.gauss(0, 0.3), 4)})")
    cur.execute(f"INSERT INTO {DATABASE}.ECONOMICS.FX_SPOT_RATES VALUES {','.join(batch)}")

    # CREDIT_SPREADS: 5 ratings x 8 sectors x 120 days
    logger.info("  CREDIT_SPREADS...")
    batch = []
    ratings = ["AAA", "AA", "A", "BBB", "BB"]
    base_spreads = {"AAA": 30, "AA": 50, "A": 80, "BBB": 150, "BB": 300}
    for day in biz_days:
        for rating in ratings:
            for sector in SECTORS:
                base = base_spreads[rating]
                spread = round(base + rng.gauss(0, base * 0.1), 2)
                d1 = round(rng.gauss(0, 2), 2)
                d1w = round(rng.gauss(0, 5), 2)
                d1m = round(rng.gauss(0, 10), 2)
                batch.append(f"('{day}','{rating}','{sector}',{spread},{d1},{d1w},{d1m})")
                if len(batch) >= 5000:
                    cur.execute(f"INSERT INTO {DATABASE}.RISK_ANALYTICS.CREDIT_SPREADS VALUES {','.join(batch)}")
                    batch = []
    if batch:
        cur.execute(f"INSERT INTO {DATABASE}.RISK_ANALYTICS.CREDIT_SPREADS VALUES {','.join(batch)}")

    # VOLATILITY_SURFACES: 50 underlyings x 5 expiries x 5 strikes
    logger.info("  VOLATILITY_SURFACES...")
    batch = []
    latest = biz_days[-1]
    expiries = [30, 60, 90, 180, 365]
    strikes = [0.90, 0.95, 1.00, 1.05, 1.10]
    for n in rng.sample(range(1, 501), 50):
        cusip = generate_cusip(n)
        for exp in expiries:
            for strike in strikes:
                iv = round(0.20 + rng.gauss(0, 0.05) + (abs(strike - 1.0) * 0.5), 4)
                delta = round(rng.uniform(-1, 1) * (1 - abs(strike - 1.0)), 4)
                batch.append(f"('{latest}','{cusip}',{exp},{strike},{iv},{delta})")
    cur.execute(f"INSERT INTO {DATABASE}.RISK_ANALYTICS.VOLATILITY_SURFACES VALUES {','.join(batch)}")


def create_horizon_tags(cur):
    logger.info("Creating Horizon governance tags...")
    cur.execute(f"USE DATABASE {DATABASE}")

    for tag_name, tag_def in HORIZON_TAGS.items():
        values = ", ".join(f"'{v}'" for v in tag_def["allowed_values"])
        cur.execute(f"CREATE TAG IF NOT EXISTS {DATABASE}.SECURITIES.{tag_name} ALLOWED_VALUES {values}")
        logger.info("  Tag: %s", tag_name)

    logger.info("Applying tags to tables...")
    for schema in SCHEMAS:
        for table_name, _ in TABLES[schema]:
            tags = TAG_ASSIGNMENTS.get(table_name, {})
            for tag_name, tag_value in tags.items():
                cur.execute(f"ALTER TABLE {DATABASE}.{schema}.{table_name} SET TAG {DATABASE}.SECURITIES.{tag_name} = '{tag_value}'")
            logger.info("  %s.%s: %d tags", schema, table_name, len(tags))


def main():
    logger.info("=== Setting up NEXUS Market Data in Snowflake ===")
    conn = get_snowflake_connection()
    cur = conn.cursor()
    try:
        create_infrastructure(cur)
        create_tables(cur)
        populate_data(cur)
        create_horizon_tags(cur)
        logger.info("=== NEXUS setup complete ===")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script against Snowflake (requires live credentials)**

```bash
export SNOWFLAKE_ACCOUNT=your-account
export SNOWFLAKE_USER=FSI_KC_SETUP
export SNOWFLAKE_PASSWORD=your-password
python3 snowflake/00_setup_nexus_data.py
```

Expected: Script completes with log messages showing each table and tag created. Verify in Snowflake console that `NEXUS_MARKET_DATA` database exists with all 4 schemas and 10 tables.

- [ ] **Step 3: Commit**

```bash
git add snowflake/00_setup_nexus_data.py
git commit -m "Add Snowflake NEXUS data setup script with synthetic market data and Horizon tags"
```

---

## Task 3: Dataplex Infrastructure for Snowflake Entries

**Files:**
- Create: `snowflake/01_create_dataplex_infra.py`

Creates the Dataplex entry group, entry types, and aspect types needed before metadata import. Follows the exact pattern from `scripts/00_create_dataplex_infra.py`.

- [ ] **Step 1: Create `snowflake/01_create_dataplex_infra.py`**

```python
#!/usr/bin/env python3
"""Creates Dataplex entry group, entry types, and aspect types for Snowflake metadata.

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
    DP = DATAPLEX_URL

    # --- Entry Group ---
    logger.info("Creating entry group: snowflake-nexus")
    for attempt in range(5):
        try:
            result = api_call(
                f"{DP}/projects/{pid}/locations/{loc}/entryGroups?entryGroupId=snowflake-nexus",
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

    # --- Entry Types ---
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
                    f"{DP}/projects/{pid}/locations/{loc}/entryTypes?entryTypeId={et_id}",
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
                    f"{DP}/projects/{pid}/locations/{loc}/aspectTypes?aspectTypeId={at_id}",
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

    logger.info("Dataplex infrastructure for Snowflake complete")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script (requires GCP credentials)**

```bash
python3 snowflake/01_create_dataplex_infra.py
```

Expected: Log output showing 1 entry group, 7 entry types, and 7 aspect types created (or already existing).

- [ ] **Step 3: Commit**

```bash
git add snowflake/01_create_dataplex_infra.py
git commit -m "Add Dataplex infrastructure script for Snowflake entry types and aspect types"
```

---

## Task 4: Horizon Metadata Ingestion

**Files:**
- Create: `snowflake/02_ingest_metadata.py`

Extracts metadata from Snowflake's `ACCOUNT_USAGE` views, builds a JSONL metadata import file following the Dataplex import specification, and calls the Dataplex Import API.

- [ ] **Step 1: Create `snowflake/02_ingest_metadata.py`**

```python
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
        table_columns = col_map.get((schema, table_name), [])
        schema_fields = []
        for col in table_columns:
            field = {
                "name": col[2],
                "mode": "NULLABLE" if col[4] == "YES" else "REQUIRED",
                "type": col[5] or "STRING",
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
```

- [ ] **Step 2: Run the script (requires both Snowflake and GCP credentials)**

```bash
python3 snowflake/02_ingest_metadata.py
```

Expected: Extracts metadata from Snowflake, writes JSONL to `snowflake/output/nexus_metadata.jsonl`, imports entries into Dataplex. Verify entries are visible in the Dataplex Catalog console under the `snowflake-nexus` entry group.

- [ ] **Step 3: Commit**

```bash
git add snowflake/02_ingest_metadata.py
git commit -m "Add Horizon metadata ingestion script for Snowflake to Dataplex import"
```

---

## Task 5: Metadata Enrichment — Glossary Links, Aspects, Lineage

**Files:**
- Create: `snowflake/03_enrich_entries.py`

Links Snowflake KC entries to business glossary terms, applies the same 7 custom FSI aspects used on BQ tables, and creates NEXUS source system lineage. Follows the patterns from `scripts/04_create_aspects.py` and `scripts/07_create_lineage.py`.

- [ ] **Step 1: Create `snowflake/03_enrich_entries.py`**

```python
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
    """Create definition links from glossary terms to Snowflake table columns."""
    logger.info("=== Linking Snowflake columns to glossary terms ===")
    pid = cfg["project_id"]
    loc = cfg["multi_region"]
    count = 0

    for (schema, table), links in GLOSSARY_LINKS.items():
        entry = snowflake_table_entry(cfg, schema, table)
        for col_name, term_id in links:
            term_entry = glossary_term_entry(cfg, term_id)
            link_url = (
                f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/entryGroups/@dataplex/entries/"
                f"projects/{pid}/locations/{loc}/glossaries/meridian-national-bank-glossary-us/terms/{term_id}"
                f":definitionLinks"
            )
            body = {
                "references": [{"resource": entry, "field": col_name}],
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
```

- [ ] **Step 2: Run the script (requires GCP credentials, entries must exist from Task 4)**

```bash
python3 snowflake/03_enrich_entries.py
```

Expected: Glossary links created, custom aspects applied to all 10 tables, NEXUS lineage created. Verify in Dataplex console that Snowflake table entries show glossary terms, classification, and lineage.

- [ ] **Step 3: Commit**

```bash
git add snowflake/03_enrich_entries.py
git commit -m "Add metadata enrichment script for Snowflake entries — glossary, aspects, lineage"
```

---

## Task 6: KC Agent — Conditional query_snowflake Tool

**Files:**
- Modify: `agents/agent_kc/agent.py`

Adds a `query_snowflake` FunctionTool conditionally when `SNOWFLAKE_ACCOUNT` is set, extends the system prompt, and manages the Snowflake connection.

- [ ] **Step 1: Add Snowflake tool and system prompt extension to `agents/agent_kc/agent.py`**

Add the following block after the existing `_creds_cache` and `_get_token` definitions (after line 123 in the current file), before the `root_agent = Agent(...)` definition:

After the existing `run_sql` tool (after line 251), add:

```python
# --- Conditional Snowflake integration ---
_sf_conn = None
SNOWFLAKE_ENABLED = bool(os.environ.get("SNOWFLAKE_ACCOUNT"))

if SNOWFLAKE_ENABLED:
    import snowflake.connector

    def _get_sf_connection():
        global _sf_conn
        if _sf_conn is None:
            _sf_conn = snowflake.connector.connect(
                account=os.environ["SNOWFLAKE_ACCOUNT"],
                user=os.environ["SNOWFLAKE_AGENT_USER"],
                password=os.environ["SNOWFLAKE_AGENT_PASSWORD"],
                warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "NEXUS_WH"),
                database=os.environ.get("SNOWFLAKE_DATABASE", "NEXUS_MARKET_DATA"),
            )
        return _sf_conn

    @FunctionTool
    def query_snowflake(sql: str) -> str:
        """Execute a SQL query against Snowflake and return results.

        Use this when Knowledge Catalog search reveals data in Snowflake
        (NEXUS market data). Use fully qualified names: DATABASE.SCHEMA.TABLE.
        For example: NEXUS_MARKET_DATA.SECURITIES.SECURITY_PRICES
        """
        try:
            conn = _get_sf_connection()
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchmany(50)
            if not rows:
                return "Query returned 0 rows."

            col_names = [desc[0] for desc in cur.description]
            header = " | ".join(col_names)
            lines = [header, "-" * len(header)]
            for row in rows:
                lines.append(" | ".join(str(v) for v in row))

            total = cur.rowcount if cur.rowcount >= 0 else len(rows)
            return f"Query returned {total} rows (showing first {len(rows)}):\n\n" + "\n".join(lines)
        except Exception as e:
            return f"Snowflake SQL Error: {str(e)}"

    SNOWFLAKE_PROMPT_EXTENSION = """

## Snowflake (NEXUS Market Data)

You also have access to Snowflake for querying external market data from the NEXUS data provider.
When Knowledge Catalog search results include Snowflake entries (entry type `snowflake-table`),
use `query_snowflake` instead of `run_sql`. Use fully qualified Snowflake table names:
`NEXUS_MARKET_DATA.SCHEMA.TABLE` (e.g., `NEXUS_MARKET_DATA.SECURITIES.SECURITY_PRICES`).

For cross-platform questions, you may need to query both BigQuery and Snowflake, then combine
the results in your response. For example, portfolio holdings live in BigQuery while current
security prices live in Snowflake.

When querying Snowflake for pricing data, prefer broad filters (date range, asset class) over
large IN-lists of identifiers. If a BigQuery result returns more than ~20 securities, query
Snowflake for the full pricing universe for that date and match in your analysis rather than
passing all CUSIPs into a single WHERE clause.

NEXUS provides: security prices, fundamentals, corporate actions, benchmark returns,
index constituents, interest rate curves (SOFR, Fed Funds, Treasuries), economic indicators,
FX spot rates, credit spreads, and volatility surfaces.
"""
```

Then modify the `root_agent` definition and `tools` list:

Replace the existing `root_agent = Agent(...)` block (around line 253-258) with:

```python
_kc_tools = [search_entries, get_context, run_sql]
if SNOWFLAKE_ENABLED:
    _kc_tools.append(query_snowflake)

_kc_instruction = SYSTEM_INSTRUCTION
if SNOWFLAKE_ENABLED:
    _kc_instruction += SNOWFLAKE_PROMPT_EXTENSION

root_agent = Agent(
    name="fsi_kc_agent",
    model="gemini-2.5-flash",
    instruction=_kc_instruction,
    tools=_kc_tools,
)
```

- [ ] **Step 2: Verify the agent still works without Snowflake configured**

```bash
cd agents/agent_kc
unset SNOWFLAKE_ACCOUNT
python3 -c "from agent import root_agent; print(f'Tools: {[t.name for t in root_agent.tools]}'); assert len(root_agent.tools) == 3; print('OK: 3 tools, no Snowflake')"
```

Expected: `OK: 3 tools, no Snowflake`

- [ ] **Step 3: Commit**

```bash
git add agents/agent_kc/agent.py
git commit -m "Add conditional query_snowflake tool to KC agent with system prompt extension"
```

---

## Task 7: Deploy Script Updates

**Files:**
- Create: `snowflake/deploy.sh`
- Modify: `agents/deploy_agents.sh`
- Modify: `deploy-full.sh`

- [ ] **Step 1: Create `snowflake/deploy.sh`**

```bash
#!/bin/bash
# Orchestrates Snowflake NEXUS integration setup.
# Requires: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [ -z "${SNOWFLAKE_ACCOUNT}" ]; then
    echo "ERROR: SNOWFLAKE_ACCOUNT not set. Skipping Snowflake setup."
    exit 1
fi

TOTAL=4
FAILED=0
SUCCEEDED=0

run_step() {
    local step="$1"
    local desc="$2"
    local cmd="$3"
    echo "[${step}/${TOTAL}] ${desc}..."
    if eval "${cmd}"; then
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "  WARNING: Step ${step} failed (${desc}) — continuing"
        FAILED=$((FAILED + 1))
    fi
}

echo "=== Snowflake NEXUS Integration Setup ==="

run_step 1 "Creating NEXUS database and data in Snowflake"  "python3 00_setup_nexus_data.py"
run_step 2 "Creating Dataplex infrastructure"                "python3 01_create_dataplex_infra.py"
run_step 3 "Ingesting Horizon metadata into Dataplex"        "python3 02_ingest_metadata.py"
run_step 4 "Enriching entries with glossary and aspects"     "python3 03_enrich_entries.py"

echo ""
echo "=== Snowflake Setup Complete ==="
echo "  Succeeded: ${SUCCEEDED}/${TOTAL}"
if [ ${FAILED} -gt 0 ]; then
    echo "  Failed:    ${FAILED}/${TOTAL} (check logs above)"
    exit 1
fi
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x snowflake/deploy.sh
```

- [ ] **Step 3: Modify `agents/deploy_agents.sh` to add Snowflake env vars for KC agent**

Add the following block after the existing `cat >> "${SCRIPT_DIR}/agent_kc/.env"` line that adds `DATAPLEX_PROJECT` (after line 65):

```bash
    # Snowflake integration (optional)
    if [ -n "${SNOWFLAKE_ACCOUNT:-}" ]; then
        cat >> "${SCRIPT_DIR}/agent_kc/.env" << SFEOF
SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT}
SNOWFLAKE_AGENT_USER=${SNOWFLAKE_AGENT_USER:-}
SNOWFLAKE_AGENT_PASSWORD=${SNOWFLAKE_AGENT_PASSWORD:-}
SNOWFLAKE_WAREHOUSE=${SNOWFLAKE_WAREHOUSE:-NEXUS_WH}
SNOWFLAKE_DATABASE=${SNOWFLAKE_DATABASE:-NEXUS_MARKET_DATA}
SFEOF
        # Add snowflake-connector-python to KC agent requirements
        if ! grep -q snowflake-connector-python "${SCRIPT_DIR}/agent_kc/requirements.txt"; then
            echo "snowflake-connector-python>=3.0" >> "${SCRIPT_DIR}/agent_kc/requirements.txt"
        fi
        echo "  Added Snowflake config to KC agent"
    fi
```

- [ ] **Step 4: Modify `deploy-full.sh` to conditionally run Snowflake setup**

Add the following block after the "Step 4: Create all Knowledge Catalog resources" section (after line 138), before the agent_analytics dataset step:

```bash
# ---------------------------------------------------------------------------
# Step 4b: Snowflake NEXUS integration (optional)
# ---------------------------------------------------------------------------
if [ -n "${SNOWFLAKE_ACCOUNT:-}" ]; then
    echo "=== Deploying Snowflake (NEXUS) integration ==="
    bash "${SCRIPT_DIR}/snowflake/deploy.sh"
else
    echo "=== Skipping Snowflake (SNOWFLAKE_ACCOUNT not set) ==="
fi
```

- [ ] **Step 5: Commit**

```bash
git add snowflake/deploy.sh agents/deploy_agents.sh deploy-full.sh
git commit -m "Add Snowflake deploy orchestration and conditional agent configuration"
```

---

## Task 8: Documentation — README and Snowflake README

**Files:**
- Create: `snowflake/README.md`
- Modify: `README.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create `snowflake/README.md`**

```markdown
# Snowflake NEXUS Integration

Optional module that adds a 4th source system — **NEXUS**, an external market data provider — in Snowflake. Demonstrates Knowledge Catalog discovering and governing data across BigQuery and Snowflake.

## Prerequisites

- Snowflake account ([free trial](https://signup.snowflake.com/) works)
- Python 3.12+ with `snowflake-connector-python`
- GCP project with the main demo already deployed

## Snowflake User Setup

Log into Snowflake as `ACCOUNTADMIN` to create the required roles and users. ACCOUNTADMIN is only used for user/role management — the scripts and agent never run as ACCOUNTADMIN.

### Step 1: Create the setup user

```sql
CREATE ROLE IF NOT EXISTS FSI_KC_SETUP_ROLE;
GRANT CREATE DATABASE ON ACCOUNT TO ROLE FSI_KC_SETUP_ROLE;
GRANT CREATE WAREHOUSE ON ACCOUNT TO ROLE FSI_KC_SETUP_ROLE;
GRANT APPLY TAG ON ACCOUNT TO ROLE FSI_KC_SETUP_ROLE;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE FSI_KC_SETUP_ROLE;

CREATE USER IF NOT EXISTS FSI_KC_SETUP
  PASSWORD = '<choose-a-password>'
  DEFAULT_ROLE = FSI_KC_SETUP_ROLE
  MUST_CHANGE_PASSWORD = FALSE;
GRANT ROLE FSI_KC_SETUP_ROLE TO USER FSI_KC_SETUP;
```

### Step 2: Run the setup scripts

```bash
export SNOWFLAKE_ACCOUNT=your-account-id
export SNOWFLAKE_USER=FSI_KC_SETUP
export SNOWFLAKE_PASSWORD=your-setup-password
bash snowflake/deploy.sh
```

### Step 3: Create the agent user

After the setup scripts complete (the database and warehouse now exist):

```sql
CREATE ROLE IF NOT EXISTS FSI_KC_AGENT_ROLE;
GRANT USAGE ON WAREHOUSE NEXUS_WH TO ROLE FSI_KC_AGENT_ROLE;
GRANT USAGE ON DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;
GRANT SELECT ON FUTURE TABLES IN DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;

CREATE USER IF NOT EXISTS FSI_KC_AGENT
  PASSWORD = '<choose-a-password>'
  DEFAULT_ROLE = FSI_KC_AGENT_ROLE
  DEFAULT_WAREHOUSE = NEXUS_WH
  MUST_CHANGE_PASSWORD = FALSE;
GRANT ROLE FSI_KC_AGENT_ROLE TO USER FSI_KC_AGENT;
```

### Step 4: Set agent environment variables

```bash
export SNOWFLAKE_AGENT_USER=FSI_KC_AGENT
export SNOWFLAKE_AGENT_PASSWORD=your-agent-password
```

Then deploy the agents as normal — the deploy script will detect Snowflake configuration and add the `query_snowflake` tool to the KC agent.

## Environment Variables

| Variable | Required For | Description |
|---|---|---|
| `SNOWFLAKE_ACCOUNT` | Setup + Agent | Account identifier (e.g., `xy12345.us-east-1`) |
| `SNOWFLAKE_USER` | Setup | Setup user (FSI_KC_SETUP) |
| `SNOWFLAKE_PASSWORD` | Setup | Setup user password |
| `SNOWFLAKE_AGENT_USER` | Agent | Read-only agent user (FSI_KC_AGENT) |
| `SNOWFLAKE_AGENT_PASSWORD` | Agent | Agent user password |
| `SNOWFLAKE_WAREHOUSE` | Both | Warehouse name (default: `NEXUS_WH`) |
| `SNOWFLAKE_DATABASE` | Both | Database name (default: `NEXUS_MARKET_DATA`) |

## Production Credential Management

Environment variables are appropriate for this demo. For production deployments:

- **Google Cloud Secret Manager:** The upstream [Snowflake Horizon connector](https://github.com/GoogleCloudPlatform/cloud-dataplex/tree/main/managed-connectivity/community-contributed-connectors/snowflake-horizon-connector) natively supports Secret Manager for credential storage. Adapt the connection helper in `common_snowflake.py` to read from `secretmanager.googleapis.com` instead of env vars.
- **Snowflake key-pair authentication:** Replace password auth with RSA key-pair auth for service accounts. Store the private key in Secret Manager and reference it in the connection config.

## What It Creates

| Component | Details |
|---|---|
| Snowflake warehouse | `NEXUS_WH` (X-Small, auto-suspend 60s) |
| Snowflake database | `NEXUS_MARKET_DATA` with 4 schemas, 10 tables |
| Synthetic data | ~50K rows of market data aligned to BQ CUSIPs |
| Horizon tags | 5 governance tags applied to all tables |
| Dataplex entries | Account, database, schema, table, tag, tag-ref entries |
| Glossary links | CUSIP, ISIN, NIM, Risk Rating linked to Snowflake columns |
| Custom aspects | Classification, retention, compliance, lineage, access control |
| Data lineage | NEXUS → Snowflake feed (10 links) |
```

- [ ] **Step 2: Add Snowflake section to main `README.md`**

Add the following section after the "Website Authentication (Optional)" section (after line 265) and before "Demo Questions":

```markdown
## Snowflake Integration (Optional)

The demo optionally integrates with Snowflake to demonstrate Knowledge Catalog's
multi-cloud data discovery. A 4th source system — NEXUS, an external market data
provider — lives in Snowflake. The KC agent discovers NEXUS data through KC and
queries both BigQuery and Snowflake in a single response.

See `snowflake/README.md` for full setup instructions.

### Quick Start

```bash
# Set Snowflake credentials (setup user)
export SNOWFLAKE_ACCOUNT=your-account-id
export SNOWFLAKE_USER=FSI_KC_SETUP
export SNOWFLAKE_PASSWORD=your-setup-password

# Set agent credentials (read-only user, created after setup)
export SNOWFLAKE_AGENT_USER=FSI_KC_AGENT
export SNOWFLAKE_AGENT_PASSWORD=your-agent-password

# Deploy everything including Snowflake
bash deploy-full.sh
```

Without `SNOWFLAKE_ACCOUNT` set, the Snowflake integration is skipped entirely
and the demo works exactly as before with BigQuery only.
```

- [ ] **Step 3: Add optional snowflake dependency to `pyproject.toml`**

Add after the existing `[project.optional-dependencies]` section (after line 13):

```toml
snowflake = [
    "snowflake-connector-python>=3.0",
]
```

- [ ] **Step 4: Commit**

```bash
git add snowflake/README.md README.md pyproject.toml
git commit -m "Add Snowflake README, update main README, add optional snowflake dependency"
```

---

## Task 9: Demo Scenarios and Eval Test Cases

**Files:**
- Modify: `demo/demo_questions.md`
- Modify: `eval/test_cases.yaml`
- Modify: `eval/run_eval.py`

- [ ] **Step 1: Add Category 7 to `demo/demo_questions.md`**

Append after the existing Category 6 section (at the end of the file):

```markdown

---

## Category 7: Multi-Cloud Discovery (KC agent with Snowflake enabled)

Demonstrates that the KC agent discovers and queries data across BigQuery and Snowflake.
Requires Snowflake integration to be configured (`SNOWFLAKE_ACCOUNT` set).

### Scenario 7.1 — Portfolio Market Value
> "What's the current market value of our top wealth portfolios?"

- **KC advantage:** Searches "portfolio holdings market value" → discovers `gold_portfolio_performance` (BQ) and `security_prices` (Snowflake) → queries both → combines on CUSIP → presents unified portfolio valuation
- **Key talking point:** *"The agent didn't know pricing data lives in Snowflake. It searched Knowledge Catalog, discovered entries from two platforms, and combined the results."*

### Scenario 7.2 — Benchmark Comparison
> "How do our portfolios compare to their benchmark indices this year?"

- **KC advantage:** Finds `gold_portfolio_performance` (BQ) + `benchmark_returns` (Snowflake) → calculates over/under-performance against live benchmark data
- **Key talking point:** *"Portfolio returns from our internal system, benchmark returns from an external vendor in Snowflake — the KC agent bridges both seamlessly."*

### Scenario 7.3 — Yield Curve Sensitivity
> "What's our NIM exposure given the current yield curve?"

- **KC advantage:** Finds `gold_net_interest_margin` (BQ) + `interest_rate_curves` (Snowflake, with SOFR/Treasury yields) → presents NIM with current rate environment context
- **Key talking point:** *"The yield curve comes from NEXUS in Snowflake, NIM from our internal analytics in BigQuery. Knowledge Catalog connects them."*

### Scenario 7.4 — Credit Spread Risk
> "What's our credit spread exposure by sector?"

- **KC advantage:** Finds `gold_market_risk_var` (BQ) + `credit_spreads` (Snowflake) → combines risk metrics with current market spreads
- **Key talking point:** *"Risk models in BigQuery, market spreads in Snowflake — the KC agent discovers the right data regardless of where it lives."*
```

- [ ] **Step 2: Add multi-cloud test cases to `eval/test_cases.yaml`**

Append to the end of the file:

```yaml

  # ============================================================
  # MULTI-CLOUD — Requires Snowflake NEXUS integration
  # ============================================================

  - id: portfolio_market_value
    question: "What's the current market value of our top wealth portfolios?"
    tags:
      complexity: multi_cloud
      audience: wealth_management
      kc_feature: cross_platform_discovery
    expected:
      basic:  { outcome: fail_gracefully }
      scaled: { outcome: fail_gracefully }
      kc:     { outcome: success, tables: [gold_portfolio_performance], snowflake_tables: [security_prices], tool_calls: [search_entries, get_context, run_sql, query_snowflake] }

  - id: benchmark_comparison
    question: "How do our portfolios compare to their benchmark indices this year?"
    tags:
      complexity: multi_cloud
      audience: wealth_management
      kc_feature: cross_platform_discovery
    expected:
      basic:  { outcome: fail_gracefully }
      scaled: { outcome: fail_gracefully }
      kc:     { outcome: success, tables: [gold_portfolio_performance], snowflake_tables: [benchmark_returns], tool_calls: [search_entries, get_context, run_sql, query_snowflake] }

  - id: yield_curve_sensitivity
    question: "What's our NIM exposure given the current yield curve?"
    tags:
      complexity: multi_cloud
      audience: risk_compliance
      kc_feature: cross_platform_discovery
    expected:
      basic:  { outcome: fail_gracefully }
      scaled: { outcome: fail_gracefully }
      kc:     { outcome: success, tables: [gold_net_interest_margin], snowflake_tables: [interest_rate_curves], glossary: [NIM], tool_calls: [search_entries, get_context, run_sql, query_snowflake] }

  - id: credit_spread_risk
    question: "What's our credit spread exposure by sector?"
    tags:
      complexity: multi_cloud
      audience: risk_compliance
      kc_feature: cross_platform_discovery
    expected:
      basic:  { outcome: fail_gracefully }
      scaled: { outcome: fail_gracefully }
      kc:     { outcome: success, tables: [gold_market_risk_var], snowflake_tables: [credit_spreads], tool_calls: [search_entries, get_context, run_sql, query_snowflake] }
```

- [ ] **Step 3: Modify `eval/run_eval.py` to skip multi-cloud cases**

Add this filter after the existing `args.filter` handling block (after line 224):

```python
    # Skip multi-cloud cases when Snowflake is not configured
    if not os.environ.get("SNOWFLAKE_ACCOUNT"):
        original_count = len(cases)
        cases = [c for c in cases if c.get("tags", {}).get("complexity") != "multi_cloud"]
        skipped = original_count - len(cases)
        if skipped:
            print(f"  Skipping {skipped} multi-cloud cases (SNOWFLAKE_ACCOUNT not set)")
```

- [ ] **Step 4: Commit**

```bash
git add demo/demo_questions.md eval/test_cases.yaml eval/run_eval.py
git commit -m "Add multi-cloud demo scenarios and eval test cases for Snowflake integration"
```

---

## Task 10: GitHub Issue for Deferred Visualization Work

**Files:** None (GitHub issue only)

- [ ] **Step 1: Create GitHub issue for Snowflake visualization differentiation**

```bash
gh issue create \
  --title "Differentiate Snowflake tables in frontend visualization" \
  --body "$(cat <<'EOF'
## Context

The Snowflake NEXUS integration adds market data tables that the KC agent can discover and query. Currently, these tables appear in the point cloud visualization the same way as BigQuery tables.

## Desired Behavior

Snowflake tables should be visually distinct in the `website-live` visualization:
- Different color cluster (e.g., cyan/teal vs the existing gold/silver/bronze colors)
- Labeled as "Snowflake" in the table popup tier badge
- Linked to the Dataplex catalog entry (not BigQuery) when clicked

## Files to Modify

- `website-live/static/visualization.js` — Add Snowflake node color/position logic
- `website-live/static/chat.js` — Add Snowflake table detection in `_DATASET_MAP` and popup handling
- `website-live/static/styles.css` — Add Snowflake tier color
- `website-live/app.py` — Add Snowflake table names to `ALL_TABLE_NAMES` conditionally

## Depends On

KC agent Snowflake query tool (must be able to surface Snowflake tables in responses).
EOF
)" \
  --label "enhancement"
```

- [ ] **Step 2: Note the issue number for reference**

Record the issue number returned by `gh issue create`.

- [ ] **Step 3: Commit (no code changes — issue only)**

No commit needed for this task.
