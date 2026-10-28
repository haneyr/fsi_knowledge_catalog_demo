#!/usr/bin/env python3
"""Creates NEXUS Syndicated Retail Market Intelligence database, tables, synthetic data,
and Horizon tags in Snowflake (Phase C2).

Requires SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD env vars.
The user must have RETAIL_KC_SETUP_ROLE (CREATE DATABASE, CREATE WAREHOUSE, APPLY TAG).
Keep schemas 100% identical to C1 catalog entries in scripts/17_create_nexus_c1.py.

Usage: python3 snowflake/00_setup_nexus_data.py
"""

import logging
import random

from common_snowflake import (
    DATABASE, WAREHOUSE, SCHEMAS, TABLES, HORIZON_TAGS, TAG_ASSIGNMENTS,
    generate_gtin13, generate_sku, get_snowflake_connection,
    GTIN_SEED_RANGE,
)

logger = logging.getLogger(__name__)

CATEGORIES = [
    ("CAT-APP", "Apparel", "Outerwear & Active"),
    ("CAT-HOM", "Home & Kitchen", "Small Appliances"),
    ("CAT-ELC", "Electronics", "Smart Home & Audio"),
    ("CAT-BTY", "Beauty", "Skincare & Cosmetics"),
    ("CAT-GRC", "Grocery", "Specialty & Organic"),
    ("CAT-FTW", "Footwear", "Athletic Footwear"),
    ("CAT-SPT", "Sporting Goods", "Outdoor Recreation"),
]

COMPETITORS = ["Target", "Walmart", "Amazon", "Costco", "Kroger"]
CHANNELS = ["In-Store", "Online", "Marketplace"]
REGIONS = ["Northeast", "Midwest", "South", "West"]
DMAS = [
    ("Northeast", "501", "New York, NY"),
    ("Northeast", "506", "Boston, MA"),
    ("Midwest", "602", "Chicago, IL"),
    ("Midwest", "613", "Minneapolis-St. Paul, MN"),
    ("South", "623", "Dallas-Ft. Worth, TX"),
    ("South", "524", "Atlanta, GA"),
    ("West", "803", "Los Angeles, CA"),
    ("West", "819", "Seattle-Tacoma, WA"),
]


def create_infrastructure(cur):
    logger.info("Creating warehouse, database, and schema...")
    cur.execute(f"CREATE WAREHOUSE IF NOT EXISTS {WAREHOUSE} WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE")
    cur.execute(f"USE WAREHOUSE {WAREHOUSE}")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    cur.execute(f"USE DATABASE {DATABASE}")
    for schema in SCHEMAS:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")


def create_tables(cur):
    logger.info("Creating 6 NEXUS Syndicated Retail Market Intelligence tables...")
    s = f"{DATABASE}.SYNDICATED_INTEL"

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {s}.nexus_competitor_prices (
        observation_date           DATE NOT NULL,
        gtin_13                    VARCHAR(14) NOT NULL,
        sku_code                   VARCHAR(20) NOT NULL,
        competitor_chain           VARCHAR(60) NOT NULL,
        channel                    VARCHAR(20) NOT NULL,
        category_name              VARCHAR(60) NOT NULL,
        competitor_regular_price   DECIMAL(12,2) NOT NULL,
        competitor_promo_price     DECIMAL(12,2),
        northwind_shelf_price      DECIMAL(12,2),
        price_index_vs_competitor  DECIMAL(8,2),
        in_stock_flag              BOOLEAN NOT NULL,
        region_code                VARCHAR(20) NOT NULL
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {s}.nexus_category_market_share (
        period_month               DATE NOT NULL,
        category_id                VARCHAR(20) NOT NULL,
        category_name              VARCHAR(60) NOT NULL,
        subcategory_name           VARCHAR(60),
        region_code                VARCHAR(20) NOT NULL,
        total_market_sales_usd     DECIMAL(18,2) NOT NULL,
        northwind_market_share_pct DECIMAL(6,2) NOT NULL,
        benchmark_gross_margin_pct DECIMAL(6,2) NOT NULL,
        top_quartile_margin_pct    DECIMAL(6,2),
        yoy_category_growth_pct    DECIMAL(6,2),
        markdown_rate_benchmark_pct DECIMAL(6,2)
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {s}.nexus_consumer_panel (
        panel_quarter              VARCHAR(10) NOT NULL,
        cohort_id                  VARCHAR(24) NOT NULL,
        income_band                VARCHAR(30) NOT NULL,
        age_group                  VARCHAR(20) NOT NULL,
        region_code                VARCHAR(20) NOT NULL,
        primary_category           VARCHAR(60) NOT NULL,
        share_of_wallet_pct        DECIMAL(6,2) NOT NULL,
        avg_basket_size_usd        DECIMAL(10,2) NOT NULL,
        trips_per_quarter          DECIMAL(6,2) NOT NULL,
        online_spend_share_pct     DECIMAL(6,2)
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {s}.nexus_regional_demand_index (
        week_ending_date            DATE NOT NULL,
        region_code                 VARCHAR(20) NOT NULL,
        dma_code                    VARCHAR(10) NOT NULL,
        dma_name                    VARCHAR(80) NOT NULL,
        category_name               VARCHAR(60) NOT NULL,
        demand_velocity_index       DECIMAL(8,2) NOT NULL,
        foot_traffic_index          DECIMAL(8,2),
        digital_search_intent_index DECIMAL(8,2),
        weather_sensitivity_score   DECIMAL(6,2),
        stockout_risk_benchmark_pct DECIMAL(6,2)
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {s}.nexus_promo_calendar_benchmark (
        promo_window_id             VARCHAR(24) NOT NULL,
        seasonal_event_name         VARCHAR(60) NOT NULL,
        category_name               VARCHAR(60) NOT NULL,
        competitor_tier             VARCHAR(30) NOT NULL,
        avg_discount_depth_pct      DECIMAL(6,2) NOT NULL,
        promo_duration_days         INT NOT NULL,
        baseline_unit_lift_pct      DECIMAL(8,2) NOT NULL,
        margin_erosion_bps          INT,
        pull_forward_rate_pct       DECIMAL(6,2)
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {s}.nexus_basket_affinity (
        anchor_category             VARCHAR(60) NOT NULL,
        attached_category           VARCHAR(60) NOT NULL,
        anchor_gtin_13              VARCHAR(14),
        attached_gtin_13            VARCHAR(14),
        co_occurrence_rate_pct      DECIMAL(6,2) NOT NULL,
        affinity_lift_ratio         DECIMAL(8,2) NOT NULL,
        avg_combined_basket_usd     DECIMAL(10,2) NOT NULL,
        channel                     VARCHAR(20) NOT NULL
    )
    """)


def populate_tables(cur):
    random.seed(42)
    s = f"{DATABASE}.SYNDICATED_INTEL"

    # 1. nexus_competitor_prices
    cur.execute(f"SELECT COUNT(*) FROM {s}.nexus_competitor_prices")
    if cur.fetchone()[0] == 0:
        rows = []
        for n in list(GTIN_SEED_RANGE)[:120]:
            gtin = generate_gtin13(n)
            sku = generate_sku(n)
            _, cat_name, _ = CATEGORIES[n % len(CATEGORIES)]
            nw_price = round(random.uniform(19.99, 149.99), 2)
            for comp in random.sample(COMPETITORS, 2):
                comp_reg = round(nw_price * random.uniform(0.92, 1.08), 2)
                comp_promo = round(comp_reg * random.uniform(0.80, 0.95), 2) if random.random() < 0.4 else None
                eff_comp = comp_promo or comp_reg
                idx = round((nw_price / eff_comp) * 100.0, 2)
                rows.append((
                    "2026-04-15", gtin, sku, comp, random.choice(CHANNELS),
                    cat_name, comp_reg, comp_promo, nw_price, idx,
                    random.random() > 0.08, random.choice(REGIONS),
                ))
        cur.executemany(
            f"INSERT INTO {s}.nexus_competitor_prices VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
        logger.info("  Inserted %d rows into nexus_competitor_prices", len(rows))

    # 2. nexus_category_market_share
    cur.execute(f"SELECT COUNT(*) FROM {s}.nexus_category_market_share")
    if cur.fetchone()[0] == 0:
        rows = []
        for cat_id, cat_name, subcat in CATEGORIES:
            for reg in REGIONS:
                rows.append((
                    "2026-04-01", cat_id, cat_name, subcat, reg,
                    round(random.uniform(250_000_000, 1_400_000_000), 2),
                    round(random.uniform(4.2, 14.8), 2),
                    round(random.uniform(34.0, 54.0), 2),
                    round(random.uniform(42.0, 62.0), 2),
                    round(random.uniform(-1.5, 9.8), 2),
                    round(random.uniform(8.5, 22.0), 2),
                ))
        cur.executemany(
            f"INSERT INTO {s}.nexus_category_market_share VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
        logger.info("  Inserted %d rows into nexus_category_market_share", len(rows))

    # 3. nexus_consumer_panel
    cur.execute(f"SELECT COUNT(*) FROM {s}.nexus_consumer_panel")
    if cur.fetchone()[0] == 0:
        rows = []
        incomes = ["Under $50K", "$50K-$100K", "$100K-$175K", "$175K+"]
        ages = ["18-29", "30-44", "45-60", "60+"]
        idx = 1
        for reg in REGIONS:
            for _, cat_name, _ in CATEGORIES:
                rows.append((
                    "2026-Q1", f"COHORT-{idx:04d}", random.choice(incomes), random.choice(ages),
                    reg, cat_name,
                    round(random.uniform(8.0, 26.5), 2),
                    round(random.uniform(42.0, 168.0), 2),
                    round(random.uniform(2.1, 7.8), 2),
                    round(random.uniform(24.0, 58.0), 2),
                ))
                idx += 1
        cur.executemany(
            f"INSERT INTO {s}.nexus_consumer_panel VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
        logger.info("  Inserted %d rows into nexus_consumer_panel", len(rows))

    # 4. nexus_regional_demand_index
    cur.execute(f"SELECT COUNT(*) FROM {s}.nexus_regional_demand_index")
    if cur.fetchone()[0] == 0:
        rows = []
        for reg, dma_code, dma_name in DMAS:
            for _, cat_name, _ in CATEGORIES:
                rows.append((
                    "2026-04-18", reg, dma_code, dma_name, cat_name,
                    round(random.uniform(88.0, 124.0), 2),
                    round(random.uniform(82.0, 115.0), 2),
                    round(random.uniform(90.0, 136.0), 2),
                    round(random.uniform(0.4, 2.8), 2),
                    round(random.uniform(2.5, 9.4), 2),
                ))
        cur.executemany(
            f"INSERT INTO {s}.nexus_regional_demand_index VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
        logger.info("  Inserted %d rows into nexus_regional_demand_index", len(rows))

    # 5. nexus_promo_calendar_benchmark
    cur.execute(f"SELECT COUNT(*) FROM {s}.nexus_promo_calendar_benchmark")
    if cur.fetchone()[0] == 0:
        rows = []
        events = ["Spring Clearance", "Memorial Day Preview", "Back to School", "Black Friday", "Holiday Peak"]
        tiers = ["Mass Merchant", "Specialty", "Department Store", "Pure-Play Digital"]
        w_id = 1
        for ev in events:
            for _, cat_name, _ in CATEGORIES:
                rows.append((
                    f"PROMO-WIN-{w_id:03d}", ev, cat_name, random.choice(tiers),
                    round(random.uniform(15.0, 38.0), 2),
                    random.choice([5, 7, 10, 14]),
                    round(random.uniform(18.0, 65.0), 2),
                    random.randint(120, 480),
                    round(random.uniform(6.0, 21.0), 2),
                ))
                w_id += 1
        cur.executemany(
            f"INSERT INTO {s}.nexus_promo_calendar_benchmark VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
        logger.info("  Inserted %d rows into nexus_promo_calendar_benchmark", len(rows))

    # 6. nexus_basket_affinity
    cur.execute(f"SELECT COUNT(*) FROM {s}.nexus_basket_affinity")
    if cur.fetchone()[0] == 0:
        rows = []
        for i, (_, cat_a, _) in enumerate(CATEGORIES):
            for j, (_, cat_b, _) in enumerate(CATEGORIES):
                if i == j:
                    continue
                rows.append((
                    cat_a, cat_b,
                    generate_gtin13(i + 1), generate_gtin13(j + 10),
                    round(random.uniform(6.5, 34.0), 2),
                    round(random.uniform(1.12, 2.85), 2),
                    round(random.uniform(68.0, 215.0), 2),
                    random.choice(["In-Store", "Online", "BOPIS"]),
                ))
        cur.executemany(
            f"INSERT INTO {s}.nexus_basket_affinity VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            rows,
        )
        logger.info("  Inserted %d rows into nexus_basket_affinity", len(rows))


def create_and_apply_tags(cur):
    logger.info("Creating and applying Snowflake Horizon governance tags...")
    s = f"{DATABASE}.SYNDICATED_INTEL"
    for tag_name, meta in HORIZON_TAGS.items():
        vals = ", ".join(f"'{v}'" for v in meta["allowed_values"])
        cur.execute(f"CREATE TAG IF NOT EXISTS {s}.{tag_name} ALLOWED_VALUES {vals}")

    for tbl_name, tags in TAG_ASSIGNMENTS.items():
        for tag_name, tag_val in tags.items():
            cur.execute(f"ALTER TABLE {s}.{tbl_name} SET TAG {s}.{tag_name} = '{tag_val}'")


def main():
    conn = get_snowflake_connection()
    try:
        cur = conn.cursor()
        create_infrastructure(cur)
        create_tables(cur)
        populate_tables(cur)
        create_and_apply_tags(cur)
        logger.info("Snowflake NEXUS Syndicated Retail Market Intelligence setup complete!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
