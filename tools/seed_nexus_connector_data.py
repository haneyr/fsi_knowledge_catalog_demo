#!/usr/bin/env python3
"""Seed deterministic NEXUS reference data in BigQuery: retail_reference.nexus_connector_data.

Contains realistic, deterministic rows for all 6 nexus_* tables:
  1. nexus_competitor_prices
  2. nexus_category_market_share
  3. nexus_consumer_panel
  4. nexus_regional_demand_index
  5. nexus_promo_calendar_benchmark
  6. nexus_basket_affinity

Table description: "[Retail] NEXUS connector reference data (simulated external feed)"
"""

import os
from datetime import date
from google.cloud import bigquery

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE", "false")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "alitch-ca-demo")
DATASET_ID = "retail_reference"
TABLE_ID = "nexus_connector_data"
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
FEED_LABEL = "[Retail] NEXUS connector reference data (simulated external feed)"

SCHEMA = [
    bigquery.SchemaField("table_name", "STRING", mode="REQUIRED", description="Canonical NEXUS table name"),
    bigquery.SchemaField("snowflake_fqn", "STRING", mode="REQUIRED", description="Snowflake fully-qualified table name"),
    bigquery.SchemaField("feed_label", "STRING", mode="REQUIRED", description="Feed provenance label"),
    # 1. nexus_competitor_prices
    bigquery.SchemaField("observation_date", "DATE", mode="NULLABLE", description="Date of syndicated price observation"),
    bigquery.SchemaField("gtin_13", "STRING", mode="NULLABLE", description="GS1 13-digit barcode (join key to silver_product_skus.gtin_13)"),
    bigquery.SchemaField("sku_code", "STRING", mode="NULLABLE", description="Standardized SKU identifier (join key to silver_product_skus.sku_code)"),
    bigquery.SchemaField("competitor_chain", "STRING", mode="NULLABLE", description="Competitor retailer chain"),
    bigquery.SchemaField("channel", "STRING", mode="NULLABLE", description="Sales channel (In-Store, Online, Marketplace, BOPIS)"),
    bigquery.SchemaField("category_name", "STRING", mode="NULLABLE", description="Merchandise category name"),
    bigquery.SchemaField("competitor_regular_price", "FLOAT64", mode="NULLABLE", description="Competitor regular unit shelf price (USD)"),
    bigquery.SchemaField("competitor_promo_price", "FLOAT64", mode="NULLABLE", description="Competitor active promotional price (USD)"),
    bigquery.SchemaField("northwind_shelf_price", "FLOAT64", mode="NULLABLE", description="Northwind Retail matched shelf price (USD)"),
    bigquery.SchemaField("price_index_vs_competitor", "FLOAT64", mode="NULLABLE", description="Northwind price index vs competitor (100 = parity, >100 = priced above competitor)"),
    bigquery.SchemaField("in_stock_flag", "BOOL", mode="NULLABLE", description="Competitor in-stock availability indicator"),
    bigquery.SchemaField("region_code", "STRING", mode="NULLABLE", description="US region code"),
    # 2. nexus_category_market_share
    bigquery.SchemaField("period_month", "DATE", mode="NULLABLE", description="Reporting month start date"),
    bigquery.SchemaField("category_id", "STRING", mode="NULLABLE", description="Syndicated category identifier"),
    bigquery.SchemaField("subcategory_name", "STRING", mode="NULLABLE", description="Merchandise subcategory"),
    bigquery.SchemaField("total_market_sales_usd", "FLOAT64", mode="NULLABLE", description="Total addressable category market sales (USD)"),
    bigquery.SchemaField("northwind_market_share_pct", "FLOAT64", mode="NULLABLE", description="Northwind Retail estimated dollar market share (%)"),
    bigquery.SchemaField("benchmark_gross_margin_pct", "FLOAT64", mode="NULLABLE", description="Syndicated peer median gross margin benchmark (%)"),
    bigquery.SchemaField("top_quartile_margin_pct", "FLOAT64", mode="NULLABLE", description="Syndicated peer 75th-percentile gross margin (%)"),
    bigquery.SchemaField("yoy_category_growth_pct", "FLOAT64", mode="NULLABLE", description="Year-over-year category market growth rate (%)"),
    bigquery.SchemaField("markdown_rate_benchmark_pct", "FLOAT64", mode="NULLABLE", description="Industry category clearance markdown rate benchmark (%)"),
    # 3. nexus_consumer_panel
    bigquery.SchemaField("panel_quarter", "STRING", mode="NULLABLE", description="Fiscal quarter (e.g., 2026-Q3)"),
    bigquery.SchemaField("cohort_id", "STRING", mode="NULLABLE", description="Anonymized demographic cohort identifier (No PII)"),
    bigquery.SchemaField("income_band", "STRING", mode="NULLABLE", description="Household annual income bracket"),
    bigquery.SchemaField("age_group", "STRING", mode="NULLABLE", description="Primary household shopper age bracket"),
    bigquery.SchemaField("primary_category", "STRING", mode="NULLABLE", description="Primary merchandise category"),
    bigquery.SchemaField("share_of_wallet_pct", "FLOAT64", mode="NULLABLE", description="Northwind Retail share of cohort category wallet (%)"),
    bigquery.SchemaField("avg_basket_size_usd", "FLOAT64", mode="NULLABLE", description="Average trip basket spend across all tracked retailers (USD)"),
    bigquery.SchemaField("trips_per_quarter", "FLOAT64", mode="NULLABLE", description="Average retail trips per household per quarter"),
    bigquery.SchemaField("online_spend_share_pct", "FLOAT64", mode="NULLABLE", description="Digital commerce share of category spend (%)"),
    # 4. nexus_regional_demand_index
    bigquery.SchemaField("week_ending_date", "DATE", mode="NULLABLE", description="Week-ending Saturday date"),
    bigquery.SchemaField("dma_code", "STRING", mode="NULLABLE", description="Designated Market Area (DMA) code"),
    bigquery.SchemaField("dma_name", "STRING", mode="NULLABLE", description="Metropolitan market name"),
    bigquery.SchemaField("demand_velocity_index", "FLOAT64", mode="NULLABLE", description="Syndicated category demand velocity index (100 = 52-week baseline)"),
    bigquery.SchemaField("foot_traffic_index", "FLOAT64", mode="NULLABLE", description="Regional brick-and-mortar retail traffic index"),
    bigquery.SchemaField("digital_search_intent_index", "FLOAT64", mode="NULLABLE", description="Regional online category search demand index"),
    bigquery.SchemaField("weather_sensitivity_score", "FLOAT64", mode="NULLABLE", description="Weather-adjusted demand elasticity score"),
    bigquery.SchemaField("stockout_risk_benchmark_pct", "FLOAT64", mode="NULLABLE", description="Syndicated peer out-of-stock benchmark rate (%)"),
    # 5. nexus_promo_calendar_benchmark
    bigquery.SchemaField("promo_window_id", "STRING", mode="NULLABLE", description="Syndicated promotional window identifier"),
    bigquery.SchemaField("seasonal_event_name", "STRING", mode="NULLABLE", description="Retail seasonal event"),
    bigquery.SchemaField("competitor_tier", "STRING", mode="NULLABLE", description="Competitor peer tier"),
    bigquery.SchemaField("avg_discount_depth_pct", "FLOAT64", mode="NULLABLE", description="Peer average promotional discount depth (%)"),
    bigquery.SchemaField("promo_duration_days", "INT64", mode="NULLABLE", description="Peer median promotion duration in days"),
    bigquery.SchemaField("baseline_unit_lift_pct", "FLOAT64", mode="NULLABLE", description="Syndicated median incremental unit lift (%)"),
    bigquery.SchemaField("margin_erosion_bps", "INT64", mode="NULLABLE", description="Average category gross margin impact in basis points"),
    bigquery.SchemaField("pull_forward_rate_pct", "FLOAT64", mode="NULLABLE", description="Post-promotion demand pull-forward dip (%)"),
    # 6. nexus_basket_affinity
    bigquery.SchemaField("anchor_category", "STRING", mode="NULLABLE", description="Primary anchor merchandise category in basket"),
    bigquery.SchemaField("attached_category", "STRING", mode="NULLABLE", description="Co-purchased attached merchandise category"),
    bigquery.SchemaField("anchor_gtin_13", "STRING", mode="NULLABLE", description="Anchor item GTIN-13 barcode"),
    bigquery.SchemaField("attached_gtin_13", "STRING", mode="NULLABLE", description="Attached item GTIN-13 barcode"),
    bigquery.SchemaField("co_occurrence_rate_pct", "FLOAT64", mode="NULLABLE", description="Share of anchor baskets containing attached category (%)"),
    bigquery.SchemaField("affinity_lift_ratio", "FLOAT64", mode="NULLABLE", description="Syndicated market basket lift ratio"),
    bigquery.SchemaField("avg_combined_basket_usd", "FLOAT64", mode="NULLABLE", description="Average total basket value when both categories co-occur (USD)"),
]


def build_rows():
    rows = []

    # 1. nexus_competitor_prices (10 rows: competitors 4-8% below us on Apparel & Outerwear, Outdoor & Activewear, Accessories & Jewelry; flat on others)
    fqn_cp = "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES"
    cp_data = [
        # Priced above competitors (competitors 4.2% to 6.8% below Northwind):
        ("2026-10-15", "0085000000056", "NW-SKU-000008", "Nordstrom", "Online", "Apparel & Outerwear", 241.30, 229.00, 258.91, 107.30, True, "Northeast"),
        ("2026-10-15", "0085000000112", "NW-SKU-000016", "Macy's", "In-Store", "Apparel & Outerwear", 56.07, 52.50, 59.78, 106.62, True, "Midwest"),
        ("2026-10-15", "0085000000028", "NW-SKU-000004", "REI", "Online", "Outdoor & Activewear", 145.79, 138.50, 154.77, 106.16, True, "West"),
        ("2026-10-15", "0085000000084", "NW-SKU-000012", "Backcountry", "Online", "Outdoor & Activewear", 172.58, 165.00, 182.45, 105.72, True, "Southeast"),
        ("2026-10-15", "0085000000007", "NW-SKU-000001", "Bloomingdale's", "In-Store", "Accessories & Jewelry", 326.74, 310.00, 342.13, 104.71, True, "Northeast"),
        ("2026-10-15", "0085000000063", "NW-SKU-000009", "Nordstrom", "Online", "Accessories & Jewelry", 85.51, 81.00, 89.26, 104.39, True, "South"),
        # Flat / at parity vs competitors (~0.0% to 0.25% delta):
        ("2026-10-15", "0085000000014", "NW-SKU-000002", "Target", "In-Store", "Home & Kitchen", 59.40, 56.00, 59.53, 100.22, True, "Midwest"),
        ("2026-10-15", "0085000000049", "NW-SKU-000007", "Sephora", "Online", "Beauty & Personal Care", 37.80, 35.90, 37.72, 99.79, True, "West"),
        ("2026-10-15", "0085000000035", "NW-SKU-000005", "Amazon", "Marketplace", "Footwear", 257.50, 249.00, 258.02, 100.20, True, "South"),
        ("2026-10-15", "0085000000021", "NW-SKU-000003", "Target", "In-Store", "Everyday Essentials", 144.50, 139.00, 144.25, 99.83, True, "Southeast"),
    ]
    for d in cp_data:
        rows.append({
            "table_name": "nexus_competitor_prices",
            "snowflake_fqn": fqn_cp,
            "feed_label": FEED_LABEL,
            "observation_date": d[0],
            "gtin_13": d[1],
            "sku_code": d[2],
            "competitor_chain": d[3],
            "channel": d[4],
            "category_name": d[5],
            "competitor_regular_price": d[6],
            "competitor_promo_price": d[7],
            "northwind_shelf_price": d[8],
            "price_index_vs_competitor": d[9],
            "in_stock_flag": d[10],
            "region_code": d[11],
        })

    # 2. nexus_category_market_share (8 rows across core categories)
    fqn_ms = "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_CATEGORY_MARKET_SHARE"
    ms_data = [
        ("2026-10-01", "CAT-001", "Apparel & Outerwear", "Womens & Mens Apparel", "US_NATIONAL", 2450000000.0, 8.57, 34.80, 39.50, 5.80, 16.40),
        ("2026-10-01", "CAT-002", "Outdoor & Activewear", "Outdoor Recreation", "US_NATIONAL", 2180000000.0, 9.76, 34.20, 38.90, 6.40, 15.20),
        ("2026-10-01", "CAT-003", "Accessories & Jewelry", "Fashion Accessories", "US_NATIONAL", 1920000000.0, 10.98, 33.10, 37.80, 4.50, 14.10),
        ("2026-10-01", "CAT-004", "Beauty & Personal Care", "Clean Beauty & Skincare", "US_NATIONAL", 1760000000.0, 12.07, 29.80, 34.60, 3.20, 10.50),
        ("2026-10-01", "CAT-005", "Home & Kitchen", "Culinary & Tabletop", "US_NATIONAL", 1680000000.0, 12.51, 29.10, 33.40, 2.10, 11.20),
        ("2026-10-01", "CAT-006", "Footwear", "Athletic Footwear", "US_NATIONAL", 1720000000.0, 12.24, 29.30, 33.80, 2.80, 11.80),
        ("2026-10-01", "CAT-007", "Consumer Electronics", "Smart Home & Audio", "US_NATIONAL", 1810000000.0, 11.63, 28.90, 32.50, 2.40, 12.10),
        ("2026-10-01", "CAT-008", "Everyday Essentials", "Private Label Basics", "US_NATIONAL", 1640000000.0, 12.85, 28.80, 32.90, 1.90, 9.80),
    ]
    for d in ms_data:
        rows.append({
            "table_name": "nexus_category_market_share",
            "snowflake_fqn": fqn_ms,
            "feed_label": FEED_LABEL,
            "period_month": d[0],
            "category_id": d[1],
            "category_name": d[2],
            "subcategory_name": d[3],
            "region_code": d[4],
            "total_market_sales_usd": d[5],
            "northwind_market_share_pct": d[6],
            "benchmark_gross_margin_pct": d[7],
            "top_quartile_margin_pct": d[8],
            "yoy_category_growth_pct": d[9],
            "markdown_rate_benchmark_pct": d[10],
        })

    # 3. nexus_consumer_panel (8 rows)
    fqn_cpnl = "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_CONSUMER_PANEL"
    cpnl_data = [
        ("2026-Q3", "COH-NW-001", "$100K-$150K", "35-44", "Northeast", "Apparel & Outerwear", 18.40, 242.50, 4.10, 58.20),
        ("2026-Q3", "COH-NW-002", "$150K+", "35-44", "West", "Outdoor & Activewear", 19.20, 268.00, 4.40, 62.50),
        ("2026-Q3", "COH-NW-003", "$100K-$150K", "25-34", "Southeast", "Accessories & Jewelry", 20.80, 215.40, 3.80, 54.60),
        ("2026-Q3", "COH-NW-004", "$75K-$100K", "25-34", "Midwest", "Beauty & Personal Care", 28.60, 134.20, 6.20, 49.10),
        ("2026-Q3", "COH-NW-005", "$100K-$150K", "45-54", "Midwest", "Home & Kitchen", 29.40, 178.90, 5.10, 44.80),
        ("2026-Q3", "COH-NW-006", "$75K-$100K", "35-44", "South", "Footwear", 27.90, 164.00, 4.70, 51.30),
        ("2026-Q3", "COH-NW-007", "$50K-$75K", "25-34", "Southeast", "Everyday Essentials", 31.20, 118.60, 6.80, 42.50),
        ("2026-Q3", "COH-NW-008", "$150K+", "45-54", "Northeast", "Seasonal & Promotional", 25.40, 289.00, 3.50, 60.40),
    ]
    for d in cpnl_data:
        rows.append({
            "table_name": "nexus_consumer_panel",
            "snowflake_fqn": fqn_cpnl,
            "feed_label": FEED_LABEL,
            "panel_quarter": d[0],
            "cohort_id": d[1],
            "income_band": d[2],
            "age_group": d[3],
            "region_code": d[4],
            "primary_category": d[5],
            "share_of_wallet_pct": d[6],
            "avg_basket_size_usd": d[7],
            "trips_per_quarter": d[8],
            "online_spend_share_pct": d[9],
        })

    # 4. nexus_regional_demand_index (8 rows: rising sharply in Southeast & West while Northwind store sales are flat across regions)
    fqn_rdi = "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_REGIONAL_DEMAND_INDEX"
    rdi_data = [
        ("2026-10-17", "Southeast", "DMA-524", "Atlanta, GA", "Outdoor & Activewear", 118.40, 112.60, 124.50, 84.20, 8.40),
        ("2026-10-17", "Southeast", "DMA-528", "Miami-Ft. Lauderdale, FL", "Apparel & Outerwear", 116.80, 110.40, 122.10, 81.60, 7.90),
        ("2026-10-17", "West", "DMA-803", "Los Angeles, CA", "Outdoor & Activewear", 115.20, 109.80, 121.00, 79.50, 7.60),
        ("2026-10-17", "West", "DMA-819", "Seattle-Tacoma, WA", "Apparel & Outerwear", 114.50, 108.90, 119.80, 86.40, 7.20),
        ("2026-10-17", "Midwest", "DMA-602", "Chicago, IL", "Home & Kitchen", 100.80, 100.20, 101.50, 68.00, 4.20),
        ("2026-10-17", "Northeast", "DMA-501", "New York, NY", "Beauty & Personal Care", 101.20, 101.00, 102.30, 72.40, 4.50),
        ("2026-10-17", "South", "DMA-623", "Dallas-Ft. Worth, TX", "Footwear", 100.40, 99.80, 100.90, 65.10, 4.10),
        ("2026-10-17", "Midwest", "DMA-613", "Minneapolis-St. Paul, MN", "Everyday Essentials", 99.90, 99.50, 100.20, 70.30, 3.90),
    ]
    for d in rdi_data:
        rows.append({
            "table_name": "nexus_regional_demand_index",
            "snowflake_fqn": fqn_rdi,
            "feed_label": FEED_LABEL,
            "week_ending_date": d[0],
            "region_code": d[1],
            "dma_code": d[2],
            "dma_name": d[3],
            "category_name": d[4],
            "demand_velocity_index": d[5],
            "foot_traffic_index": d[6],
            "digital_search_intent_index": d[7],
            "weather_sensitivity_score": d[8],
            "stockout_risk_benchmark_pct": d[9],
        })

    # 5. nexus_promo_calendar_benchmark (6 rows)
    fqn_pcb = "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_PROMO_CALENDAR_BENCHMARK"
    pcb_data = [
        ("PROMO-2026-Q3-01", "Fall Outerwear Preview", "Apparel & Outerwear", "Department Store", 18.50, 10, 34.20, 240, 14.20),
        ("PROMO-2026-Q3-02", "Trail & Fall Gear Event", "Outdoor & Activewear", "Specialty", 16.00, 12, 31.80, 210, 12.60),
        ("PROMO-2026-Q3-03", "Designer Accessories Spotlight", "Accessories & Jewelry", "Specialty", 15.00, 7, 26.80, 185, 11.50),
        ("PROMO-2026-Q4-01", "Holiday Culinary Prep", "Home & Kitchen", "Mass Merchant", 20.00, 14, 38.40, 275, 15.80),
        ("PROMO-2026-Q4-02", "Clean Beauty Gift Event", "Beauty & Personal Care", "Specialty", 12.00, 10, 24.50, 140, 8.40),
        ("PROMO-2026-Q4-03", "Black Friday Early Access", "Seasonal & Promotional", "Pure-Play Digital", 25.00, 5, 48.00, 360, 19.20),
    ]
    for d in pcb_data:
        rows.append({
            "table_name": "nexus_promo_calendar_benchmark",
            "snowflake_fqn": fqn_pcb,
            "feed_label": FEED_LABEL,
            "promo_window_id": d[0],
            "seasonal_event_name": d[1],
            "category_name": d[2],
            "competitor_tier": d[3],
            "avg_discount_depth_pct": d[4],
            "promo_duration_days": d[5],
            "baseline_unit_lift_pct": d[6],
            "margin_erosion_bps": d[7],
            "pull_forward_rate_pct": d[8],
        })

    # 6. nexus_basket_affinity (6 rows)
    fqn_ba = "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_BASKET_AFFINITY"
    ba_data = [
        ("Outdoor & Activewear", "Footwear", "0085000000028", "0085000000035", 28.40, 3.42, 384.50, "Online"),
        ("Apparel & Outerwear", "Accessories & Jewelry", "0085000000056", "0085000000007", 24.10, 2.95, 542.00, "In-Store"),
        ("Beauty & Personal Care", "Seasonal & Promotional", "0085000000049", "0085000000042", 19.80, 2.48, 312.80, "Online"),
        ("Home & Kitchen", "Everyday Essentials", "0085000000014", "0085000000021", 17.50, 2.15, 192.40, "BOPIS"),
        ("Footwear", "Outdoor & Activewear", "0085000000035", "0085000000084", 22.60, 2.78, 410.20, "In-Store"),
        ("Accessories & Jewelry", "Beauty & Personal Care", "0085000000063", "0085000000049", 16.20, 1.94, 148.60, "Online"),
    ]
    for d in ba_data:
        rows.append({
            "table_name": "nexus_basket_affinity",
            "snowflake_fqn": fqn_ba,
            "feed_label": FEED_LABEL,
            "anchor_category": d[0],
            "attached_category": d[1],
            "anchor_gtin_13": d[2],
            "attached_gtin_13": d[3],
            "co_occurrence_rate_pct": d[4],
            "affinity_lift_ratio": d[5],
            "avg_combined_basket_usd": d[6],
            "channel": d[7],
        })

    return rows


def main():
    client = bigquery.Client(project=PROJECT_ID)
    table = bigquery.Table(FULL_TABLE_ID, schema=SCHEMA)
    table.description = FEED_LABEL
    table.labels = {
        "use-case": "retail",
        "demo": "retail-knowledge-catalog",
        "owner": "alitch",
        "env": "demo",
    }

    # Create or replace table idempotently
    client.delete_table(FULL_TABLE_ID, not_found_ok=True)
    table = client.create_table(table)
    print(f"Created table {FULL_TABLE_ID} with description: {table.description}")

    rows = build_rows()
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    job = client.load_table_from_json(rows, FULL_TABLE_ID, job_config=job_config)
    job.result()

    # Verify row counts by table_name
    q = f"""
    SELECT table_name, snowflake_fqn, COUNT(*) AS row_count
    FROM `{FULL_TABLE_ID}`
    GROUP BY 1, 2
    ORDER BY 1
    """
    for r in client.query(q).result():
        print(f"  {r.table_name} ({r.snowflake_fqn}): {r.row_count} rows")


if __name__ == "__main__":
    main()
