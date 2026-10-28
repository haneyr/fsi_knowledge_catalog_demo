#!/usr/bin/env python3
"""Phase C1 — Creates NEXUS (Syndicated Retail Market Intelligence) Snowflake catalog layer
and cross-cloud lineage in Google Cloud Knowledge Catalog without requiring live Snowflake credentials.

Creates:
  - Global Entry Types: retail-snowflake-instance, retail-snowflake-schema, retail-snowflake-table
  - Global Aspect Types: retail-snowflake-instance, retail-snowflake-schema, retail-snowflake-table
    (plus ensures retail-data-classification, retail-access-control, retail-data-lineage-metadata
     include Third-Party Licensed, External Vendor Agreement, cloud_platform="Snowflake",
     data_residency="External / Non-GCP")
  - Multi-region (us) Entry Group: retail-nexus-market-intel
  - Instance + Schema + 6 NEXUS Table Entries (system="Snowflake", platform="Snowflake"):
      1. nexus_competitor_prices
      2. nexus_category_market_share
      3. nexus_consumer_panel
      4. nexus_regional_demand_index
      5. nexus_promo_calendar_benchmark
      6. nexus_basket_affinity
  - All 7 retail-* governance aspects + retail-snowflake-table marker aspect on all 6 tables
  - Cross-cloud Data Lineage: NEXUS (Snowflake) -> retail_gold benchmark tables

Usage:
  python3 scripts/17_create_nexus_c1.py
"""

import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    load_config, api_call, poll_operation, set_entry_aspect,
    DATAPLEX_URL, LINEAGE_URL, entry_group_location, entry_type_location,
)

logger = logging.getLogger(__name__)

ENTRY_GROUP_ID = "retail-nexus-market-intel"
SF_ACCOUNT = "nexus-retail-intel"
SF_DATABASE = "NEXUS_MARKET_DATA"
SF_SCHEMA = "SYNDICATED_INTEL"
SF_WAREHOUSE = "NEXUS_WH"

NEXUS_TABLES = [
    (
        "nexus_competitor_prices",
        "nexus_competitor_prices",
        "[Retail] NEXUS Syndicated Competitor Prices (Snowflake External / Non-GCP) — Daily competitor shelf & promotional prices by GTIN-13, SKU, and retail chain across US in-store and digital channels. Join to BigQuery retail_gold.gold_assortment_performance, retail_gold.gold_gross_margin_analysis, or retail_silver.silver_product_skus on gtin_13 / sku_code / category_name.",
        [
            ("observation_date", "DATE", "REQUIRED", "Date of syndicated price observation"),
            ("gtin_13", "VARCHAR(14)", "REQUIRED", "GS1 13-digit barcode (join key to BigQuery silver_product_skus.gtin_13)"),
            ("sku_code", "VARCHAR(20)", "REQUIRED", "Standardized SKU identifier (join key to BigQuery silver_product_skus.sku_code)"),
            ("competitor_chain", "VARCHAR(60)", "REQUIRED", "Competitor retailer chain (Target, Walmart, Amazon, Costco, Kroger)"),
            ("channel", "VARCHAR(20)", "REQUIRED", "Sales channel (In-Store, Online, Marketplace)"),
            ("category_name", "VARCHAR(60)", "REQUIRED", "Merchandise category (join key to retail_gold.gold_assortment_performance & gold_gross_margin_analysis)"),
            ("competitor_regular_price", "DECIMAL(12,2)", "REQUIRED", "Competitor regular unit shelf price (USD)"),
            ("competitor_promo_price", "DECIMAL(12,2)", "NULLABLE", "Competitor active promotional price (USD)"),
            ("northwind_shelf_price", "DECIMAL(12,2)", "NULLABLE", "Northwind Retail matched shelf price (USD)"),
            ("price_index_vs_competitor", "DECIMAL(8,2)", "NULLABLE", "Northwind price index vs competitor (100 = parity, >100 = priced above competitor)"),
            ("in_stock_flag", "BOOLEAN", "REQUIRED", "Competitor in-stock availability indicator"),
            ("region_code", "VARCHAR(20)", "REQUIRED", "US Census region (Northeast, Midwest, South, West)"),
        ],
        ["gold_assortment_performance", "gold_gross_margin_analysis", "gold_markdown_risk_var"],
    ),
    (
        "nexus_category_market_share",
        "nexus_category_market_share",
        "[Retail] NEXUS Syndicated Category Market Share & Margin Benchmarks (Snowflake External / Non-GCP) — Monthly syndicated US retail category dollar share, median industry gross margin benchmarks, top-quartile margins, and YoY growth. Join to BigQuery retail_gold.gold_assortment_performance and retail_gold.gold_gross_margin_analysis on category_name.",
        [
            ("period_month", "DATE", "REQUIRED", "Reporting month start date"),
            ("category_id", "VARCHAR(20)", "REQUIRED", "Syndicated category identifier"),
            ("category_name", "VARCHAR(60)", "REQUIRED", "Merchandise category name (join key to retail_gold.gold_gross_margin_analysis & gold_assortment_performance)"),
            ("subcategory_name", "VARCHAR(60)", "NULLABLE", "Merchandise subcategory"),
            ("region_code", "VARCHAR(20)", "REQUIRED", "US market region"),
            ("total_market_sales_usd", "DECIMAL(18,2)", "REQUIRED", "Total addressable category market sales (USD)"),
            ("northwind_market_share_pct", "DECIMAL(6,2)", "REQUIRED", "Northwind Retail estimated dollar market share (%)"),
            ("benchmark_gross_margin_pct", "DECIMAL(6,2)", "REQUIRED", "Syndicated peer median gross margin benchmark (%)"),
            ("top_quartile_margin_pct", "DECIMAL(6,2)", "NULLABLE", "Syndicated peer 75th-percentile gross margin (%)"),
            ("yoy_category_growth_pct", "DECIMAL(6,2)", "NULLABLE", "Year-over-year category market growth rate (%)"),
            ("markdown_rate_benchmark_pct", "DECIMAL(6,2)", "NULLABLE", "Industry category clearance markdown rate benchmark (%)"),
        ],
        ["gold_assortment_performance", "gold_gross_margin_analysis", "gold_category_manager_scorecard"],
    ),
    (
        "nexus_consumer_panel",
        "nexus_consumer_panel",
        "[Retail] NEXUS Syndicated Consumer Panel (Snowflake External / Non-GCP) — Anonymized household shopper panel measuring cross-retailer wallet share, trip frequency, and omnichannel spend split by cohort. Governed under Vendor Data License / No PII. Join to BigQuery retail_gold.gold_customer_360 by region_code and primary_category.",
        [
            ("panel_quarter", "VARCHAR(10)", "REQUIRED", "Fiscal quarter (e.g., 2026-Q1)"),
            ("cohort_id", "VARCHAR(24)", "REQUIRED", "Anonymized demographic cohort identifier (No PII)"),
            ("income_band", "VARCHAR(30)", "REQUIRED", "Household annual income bracket"),
            ("age_group", "VARCHAR(20)", "REQUIRED", "Primary household shopper age bracket"),
            ("region_code", "VARCHAR(20)", "REQUIRED", "US geographic region"),
            ("primary_category", "VARCHAR(60)", "REQUIRED", "Primary merchandise category"),
            ("share_of_wallet_pct", "DECIMAL(6,2)", "REQUIRED", "Northwind Retail share of cohort category wallet (%)"),
            ("avg_basket_size_usd", "DECIMAL(10,2)", "REQUIRED", "Average trip basket spend across all tracked retailers (USD)"),
            ("trips_per_quarter", "DECIMAL(6,2)", "REQUIRED", "Average retail trips per household per quarter"),
            ("online_spend_share_pct", "DECIMAL(6,2)", "NULLABLE", "Digital commerce share of category spend (%)"),
        ],
        ["gold_customer_360", "gold_vip_member_revenue"],
    ),
    (
        "nexus_regional_demand_index",
        "nexus_regional_demand_index",
        "[Retail] NEXUS Regional Demand Velocity Index (Snowflake External / Non-GCP) — Weekly syndicated regional demand indices, store foot-traffic benchmarks, digital search intent, and weather elasticity by DMA and category. Join to BigQuery retail_gold.gold_store_performance and retail_gold.gold_inventory_allocation.",
        [
            ("week_ending_date", "DATE", "REQUIRED", "Week-ending Saturday date"),
            ("region_code", "VARCHAR(20)", "REQUIRED", "US region code"),
            ("dma_code", "VARCHAR(10)", "REQUIRED", "Designated Market Area (DMA) code"),
            ("dma_name", "VARCHAR(80)", "REQUIRED", "Metropolitan market name"),
            ("category_name", "VARCHAR(60)", "REQUIRED", "Merchandise category"),
            ("demand_velocity_index", "DECIMAL(8,2)", "REQUIRED", "Syndicated category demand velocity index (100 = 52-week baseline)"),
            ("foot_traffic_index", "DECIMAL(8,2)", "NULLABLE", "Regional brick-and-mortar retail traffic index"),
            ("digital_search_intent_index", "DECIMAL(8,2)", "NULLABLE", "Regional online category search demand index"),
            ("weather_sensitivity_score", "DECIMAL(6,2)", "NULLABLE", "Weather-adjusted demand elasticity score"),
            ("stockout_risk_benchmark_pct", "DECIMAL(6,2)", "NULLABLE", "Syndicated peer out-of-stock benchmark rate (%)"),
        ],
        ["gold_store_performance", "gold_inventory_allocation"],
    ),
    (
        "nexus_promo_calendar_benchmark",
        "nexus_promo_calendar_benchmark",
        "[Retail] NEXUS Promotional Calendar & Elasticity Benchmark (Snowflake External / Non-GCP) — Syndicated seasonal promotional depth, campaign duration, unit lift, and margin erosion benchmarks across retail peer segments. Join to BigQuery retail_gold.gold_promo_margin_impact and retail_gold.gold_markdown_risk_var on category_name.",
        [
            ("promo_window_id", "VARCHAR(24)", "REQUIRED", "Syndicated promotional window identifier"),
            ("seasonal_event_name", "VARCHAR(60)", "REQUIRED", "Retail seasonal event (Spring Clearance, Back to School, Black Friday, Holiday)"),
            ("category_name", "VARCHAR(60)", "REQUIRED", "Merchandise category (join key to gold_promo_margin_impact)"),
            ("competitor_tier", "VARCHAR(30)", "REQUIRED", "Competitor peer tier (Mass Merchant, Specialty, Department Store, Pure-Play Digital)"),
            ("avg_discount_depth_pct", "DECIMAL(6,2)", "REQUIRED", "Peer average promotional discount depth (%)"),
            ("promo_duration_days", "INT", "REQUIRED", "Peer median promotion duration in days"),
            ("baseline_unit_lift_pct", "DECIMAL(8,2)", "REQUIRED", "Syndicated median incremental unit lift (%)"),
            ("margin_erosion_bps", "INT", "NULLABLE", "Average category gross margin impact in basis points"),
            ("pull_forward_rate_pct", "DECIMAL(6,2)", "NULLABLE", "Post-promotion demand pull-forward dip (%)"),
        ],
        ["gold_promo_margin_impact", "gold_markdown_risk_var"],
    ),
    (
        "nexus_basket_affinity",
        "nexus_basket_affinity",
        "[Retail] NEXUS Syndicated Cross-Category Basket Affinity (Snowflake External / Non-GCP) — Market-wide omnichannel co-purchase attach rates, basket affinity lift ratios, and combined basket spend across product categories and GTIN-13 pairs. Join to BigQuery retail_gold.gold_assortment_performance and gold_loyalty_account_summary.",
        [
            ("anchor_category", "VARCHAR(60)", "REQUIRED", "Primary anchor merchandise category in basket"),
            ("attached_category", "VARCHAR(60)", "REQUIRED", "Co-purchased attached merchandise category"),
            ("anchor_gtin_13", "VARCHAR(14)", "NULLABLE", "Anchor item GTIN-13 barcode (join key to silver_product_skus.gtin_13)"),
            ("attached_gtin_13", "VARCHAR(14)", "NULLABLE", "Attached item GTIN-13 barcode"),
            ("co_occurrence_rate_pct", "DECIMAL(6,2)", "REQUIRED", "Share of anchor baskets containing attached category (%)"),
            ("affinity_lift_ratio", "DECIMAL(8,2)", "REQUIRED", "Syndicated market basket lift ratio (>1.0 indicates positive cross-sell affinity)"),
            ("avg_combined_basket_usd", "DECIMAL(10,2)", "REQUIRED", "Average total basket value when both categories co-occur (USD)"),
            ("channel", "VARCHAR(20)", "REQUIRED", "Omnichannel fulfillment mode (In-Store, Online, BOPIS)"),
        ],
        ["gold_assortment_performance", "gold_loyalty_account_summary"],
    ),
]


def map_type(t):
    t = t.upper()
    if "INT" in t or "NUMBER" in t or "DECIMAL" in t:
        return "NUMBER"
    if "VARCHAR" in t or "CHAR" in t or "TEXT" in t:
        return "STRING"
    if "BOOL" in t:
        return "BOOLEAN"
    if t == "DATE":
        return "DATETIME"
    if "TIMESTAMP" in t:
        return "TIMESTAMP"
    return "OTHER"


def ensure_existing_aspect_enums(pid):
    """Ensure existing retail-* aspect types support NEXUS off-platform values."""
    logger.info("=== Step 1: Ensuring existing retail-* aspect types have NEXUS off-platform fields ===")

    # 1. retail-data-classification -> Third-Party Licensed
    dc = api_call(f"{DATAPLEX_URL}/projects/{pid}/locations/global/aspectTypes/retail-data-classification", "GET")
    ev = dc["metadataTemplate"]["recordFields"][0]["enumValues"]
    if not any(x["name"] == "Third-Party Licensed" for x in ev):
        ev.append({"name": "Third-Party Licensed", "index": len(ev) + 1})
        op = api_call(
            f"{DATAPLEX_URL}/projects/{pid}/locations/global/aspectTypes/retail-data-classification?updateMask=metadataTemplate",
            "PATCH",
            {"metadataTemplate": dc["metadataTemplate"]},
        )
        if "operations" in op.get("name", ""):
            poll_operation(op["name"])
        logger.info("  Added 'Third-Party Licensed' to retail-data-classification")
    else:
        logger.info("  retail-data-classification already has 'Third-Party Licensed'")

    # 2. retail-access-control -> External Vendor Agreement
    ac = api_call(f"{DATAPLEX_URL}/projects/{pid}/locations/global/aspectTypes/retail-access-control", "GET")
    ev_ac = ac["metadataTemplate"]["recordFields"][0]["enumValues"]
    if not any(x["name"] == "External Vendor Agreement" for x in ev_ac):
        ev_ac.append({"name": "External Vendor Agreement", "index": len(ev_ac) + 1})
        op = api_call(
            f"{DATAPLEX_URL}/projects/{pid}/locations/global/aspectTypes/retail-access-control?updateMask=metadataTemplate",
            "PATCH",
            {"metadataTemplate": ac["metadataTemplate"]},
        )
        if "operations" in op.get("name", ""):
            poll_operation(op["name"])
        logger.info("  Added 'External Vendor Agreement' to retail-access-control")
    else:
        logger.info("  retail-access-control already has 'External Vendor Agreement'")

    # 3. retail-data-lineage-metadata -> cloud_platform, data_residency
    dl = api_call(f"{DATAPLEX_URL}/projects/{pid}/locations/global/aspectTypes/retail-data-lineage-metadata", "GET")
    rf = dl["metadataTemplate"]["recordFields"]
    if not any(x["name"] == "cloud_platform" for x in rf):
        rf.append({"name": "cloud_platform", "type": "string", "index": len(rf) + 1, "annotations": {"displayName": "Cloud Platform"}})
        rf.append({"name": "data_residency", "type": "string", "index": len(rf) + 1, "annotations": {"displayName": "Data Residency"}})
        op = api_call(
            f"{DATAPLEX_URL}/projects/{pid}/locations/global/aspectTypes/retail-data-lineage-metadata?updateMask=metadataTemplate",
            "PATCH",
            {"metadataTemplate": dl["metadataTemplate"]},
        )
        if "operations" in op.get("name", ""):
            poll_operation(op["name"])
        logger.info("  Added cloud_platform & data_residency to retail-data-lineage-metadata")
    else:
        logger.info("  retail-data-lineage-metadata already has cloud_platform & data_residency")


def create_nexus_infra(pid, et_loc, eg_loc):
    """Create entry group retail-nexus-market-intel, entry types retail-snowflake-*, and marker aspect types."""
    logger.info("=== Step 2: Creating NEXUS entry types, aspect types, and entry group ===")

    entry_types = [
        ("retail-snowflake-instance", "[Retail] Snowflake Market Intelligence Instance", ["DATABASE"], "Snowflake", "Snowflake"),
        ("retail-snowflake-schema", "[Retail] Snowflake Market Intelligence Schema", ["DATABASE_SCHEMA"], "Snowflake", "Snowflake"),
        ("retail-snowflake-table", "[Retail] Snowflake Market Intelligence Table", ["TABLE"], "Snowflake", "Snowflake"),
    ]
    for et_id, name, aliases, platform, system in entry_types:
        res = api_call(
            f"{DATAPLEX_URL}/projects/{pid}/locations/{et_loc}/entryTypes?entryTypeId={et_id}",
            "POST",
            {
                "displayName": name,
                "description": f"[Retail] Represents a {name.replace('[Retail] ', '').lower()} in Snowflake (External / Non-GCP)",
                "typeAliases": aliases,
                "platform": platform,
                "system": system,
            },
        )
        if "operations" in res.get("name", ""):
            poll_operation(res["name"])
        logger.info("  EntryType %s: %s", et_id, "exists" if res.get("_exists") else "created")
        time.sleep(1)

    marker_fields = [
        {"name": "cloud_platform", "type": "string", "index": 1, "annotations": {"displayName": "Cloud Platform"}},
        {"name": "data_residency", "type": "string", "index": 2, "annotations": {"displayName": "Data Residency"}},
        {"name": "vendor_name", "type": "string", "index": 3, "annotations": {"displayName": "Syndicated Data Vendor"}},
        {"name": "vendor_agreement_owner", "type": "string", "index": 4, "annotations": {"displayName": "Vendor Agreement Owner"}},
        {"name": "snowflake_account", "type": "string", "index": 5, "annotations": {"displayName": "Snowflake Account"}},
        {"name": "snowflake_database", "type": "string", "index": 6, "annotations": {"displayName": "Snowflake Database"}},
        {"name": "live_query_status", "type": "string", "index": 7, "annotations": {"displayName": "Cross-Cloud Live Query Status"}},
    ]

    aspect_types = [
        ("retail-snowflake-instance", "[Retail] Snowflake Instance Marker", "[Retail] Off-platform Snowflake instance metadata", marker_fields),
        ("retail-snowflake-schema", "[Retail] Snowflake Schema Marker", "[Retail] Off-platform Snowflake schema metadata", marker_fields),
        ("retail-snowflake-table", "[Retail] Snowflake Cross-Cloud Table Metadata", "[Retail] Off-platform Snowflake table residency, license, and vendor metadata", marker_fields),
    ]
    for at_id, name, desc, fields in aspect_types:
        template = {"name": at_id.replace("-", "_"), "type": "record", "recordFields": fields}
        res = api_call(
            f"{DATAPLEX_URL}/projects/{pid}/locations/{et_loc}/aspectTypes?aspectTypeId={at_id}",
            "POST",
            {"displayName": name, "description": desc, "metadataTemplate": template},
        )
        if "operations" in res.get("name", ""):
            poll_operation(res["name"])
        logger.info("  AspectType %s: %s", at_id, "exists" if res.get("_exists") else "created")
        time.sleep(1)

    # Entry Group in us multi-region
    eg_res = api_call(
        f"{DATAPLEX_URL}/projects/{pid}/locations/{eg_loc}/entryGroups?entryGroupId={ENTRY_GROUP_ID}",
        "POST",
        {
            "displayName": "[Retail] NEXUS — Syndicated Retail Market Intelligence (Snowflake)",
            "description": "[Retail] Third-party licensed syndicated retail intelligence hosted in Snowflake (External / Non-GCP): competitor pricing, category market share, consumer panel data, regional demand indices, promo calendar benchmarks, and basket affinity.",
        },
    )
    if "operations" in eg_res.get("name", ""):
        poll_operation(eg_res["name"])
    logger.info("  EntryGroup %s: %s", ENTRY_GROUP_ID, "exists" if eg_res.get("_exists") else "created")


def create_nexus_entries_and_aspects(cfg, pid, et_loc, eg_loc):
    """Create instance, schema, and 6 table entries in retail-nexus-market-intel and apply all 7 aspects."""
    logger.info("=== Step 3: Creating NEXUS entries and applying 7 retail-* aspects + off-platform markers ===")

    EG = f"projects/{pid}/locations/{eg_loc}/entryGroups/{ENTRY_GROUP_ID}"
    ET = lambda t: f"projects/{pid}/locations/{et_loc}/entryTypes/{t}"
    AT = lambda t: f"projects/{pid}/locations/{et_loc}/aspectTypes/{t}"

    marker_data = {
        "cloud_platform": "Snowflake",
        "data_residency": "External / Non-GCP",
        "vendor_name": "NEXUS — Syndicated Retail Market Intelligence",
        "vendor_agreement_owner": "Sarah Jenkins (VP of Merchandising Analytics) & Enterprise Data Procurement — Contract #NWR-NEXUS-2026",
        "snowflake_account": f"{SF_ACCOUNT}.us-east-1.aws",
        "snowflake_database": f"{SF_DATABASE}.{SF_SCHEMA}",
        "live_query_status": "Catalog-only in C1 (Snowflake external platform; not queryable via BigQuery run_sql)",
    }

    # 1. Instance entry
    inst_id = "nexus-snowflake-instance"
    inst_body = {
        "entryType": ET("retail-snowflake-instance"),
        "fullyQualifiedName": f"snowflake:{SF_ACCOUNT}.{SF_DATABASE}",
        "entrySource": {
            "resource": f"//snowflake.nexus-syndicated.external/accounts/{SF_ACCOUNT}/databases/{SF_DATABASE}",
            "displayName": f"NEXUS_MARKET_DATA (Snowflake)",
            "description": "[Retail] NEXUS — Syndicated Retail Market Intelligence Snowflake Database (cloud_platform=Snowflake, data_residency=External / Non-GCP). Third-party licensed retail market intelligence.",
            "system": "Snowflake",
            "platform": "Snowflake",
        },
        "aspects": {
            "dataplex-types.global.generic": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/generic", "data": {}},
            f"{pid}.global.retail-snowflake-instance": {"aspectType": AT("retail-snowflake-instance"), "data": marker_data},
            "dataplex-types.global.overview": {
                "aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview",
                "data": {"content": "<h2>NEXUS — Syndicated Retail Market Intelligence (Snowflake)</h2><p>External third-party licensed retail intelligence hosted on <b>Snowflake (External / Non-GCP)</b>. Governed in Google Cloud Knowledge Catalog under External Vendor Agreement #NWR-NEXUS-2026 (Owner: Sarah Jenkins, VP of Merchandising Analytics &amp; Enterprise Data Procurement).</p>"},
            },
        },
    }
    res = api_call(f"{DATAPLEX_URL}/{EG}/entries?entryId={inst_id}", "POST", inst_body)
    if res.get("_exists"):
        api_call(f"{DATAPLEX_URL}/{EG}/entries/{inst_id}", "PATCH", inst_body)
    logger.info("  Instance entry: %s", inst_id)

    # 2. Schema entry
    schema_id = "nexus-syndicated-intel-schema"
    schema_body = {
        "entryType": ET("retail-snowflake-schema"),
        "parentEntry": f"{EG}/entries/{inst_id}",
        "fullyQualifiedName": f"snowflake:{SF_ACCOUNT}.{SF_DATABASE}.{SF_SCHEMA}",
        "entrySource": {
            "resource": f"//snowflake.nexus-syndicated.external/accounts/{SF_ACCOUNT}/databases/{SF_DATABASE}/schemas/{SF_SCHEMA}",
            "displayName": SF_SCHEMA,
            "description": "[Retail] NEXUS Syndicated Retail Market Intelligence schema in Snowflake (External / Non-GCP): 6 licensed tables covering competitor prices, category market share, consumer panel, regional demand indices, promo calendar benchmarks, and basket affinity.",
            "system": "Snowflake",
            "platform": "Snowflake",
        },
        "aspects": {
            "dataplex-types.global.generic": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/generic", "data": {}},
            f"{pid}.global.retail-snowflake-schema": {"aspectType": AT("retail-snowflake-schema"), "data": marker_data},
            "dataplex-types.global.overview": {
                "aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview",
                "data": {"content": f"<h2>{SF_SCHEMA} (Snowflake)</h2><p>Syndicated retail market intelligence schema hosted in Snowflake (External / Non-GCP).</p>"},
            },
        },
    }
    res = api_call(f"{DATAPLEX_URL}/{EG}/entries?entryId={schema_id}", "POST", schema_body)
    if res.get("_exists"):
        api_call(f"{DATAPLEX_URL}/{EG}/entries/{schema_id}", "PATCH", schema_body)
    logger.info("  Schema entry: %s", schema_id)

    # 3. Table entries + all 7 retail-* aspects
    aspect_count = 0
    for tid, name, desc, cols, target_gold in NEXUS_TABLES:
        fqn = f"snowflake:{SF_ACCOUNT}.{SF_DATABASE}.{SF_SCHEMA}.{name}"
        schema_data = {
            "fields": [
                {
                    "name": c[0],
                    "dataType": c[1],
                    "metadataType": map_type(c[1]),
                    "mode": c[2],
                    "description": c[3],
                }
                for c in cols
            ]
        }
        overview_html = (
            f"<h2>{name} — NEXUS Syndicated Retail Market Intelligence (Snowflake)</h2>"
            f"<p>{desc}</p>"
            f"<ul>"
            f"<li><b>Cloud Platform:</b> Snowflake (<code>cloud_platform = Snowflake</code>)</li>"
            f"<li><b>Data Residency:</b> External / Non-GCP (<code>data_residency = External / Non-GCP</code>)</li>"
            f"<li><b>Data Classification:</b> Third-Party Licensed</li>"
            f"<li><b>Access Control:</b> External Vendor Agreement (Contract #NWR-NEXUS-2026)</li>"
            f"<li><b>Regulatory Compliance:</b> Vendor Data License / No PII</li>"
            f"<li><b>Vendor Agreement Owner:</b> Sarah Jenkins, VP of Merchandising Analytics &amp; Enterprise Data Procurement (steward: Marcus Vance, Director of External Data Partnerships)</li>"
            f"<li><b>BigQuery Join Targets:</b> {', '.join(f'retail_gold.{g}' for g in target_gold)}</li>"
            f"<li><b>Execution Note:</b> Hosted in Snowflake (<code>{SF_DATABASE}.{SF_SCHEMA}.{name}</code>). Cannot be queried via BigQuery <code>run_sql</code>; requires live Snowflake cross-cloud query connection (<code>query_snowflake</code>).</li>"
            f"</ul>"
        )
        t_body = {
            "entryType": ET("retail-snowflake-table"),
            "parentEntry": f"{EG}/entries/{schema_id}",
            "fullyQualifiedName": fqn,
            "entrySource": {
                "resource": f"//snowflake.nexus-syndicated.external/accounts/{SF_ACCOUNT}/databases/{SF_DATABASE}/schemas/{SF_SCHEMA}/tables/{name}",
                "displayName": name,
                "description": desc,
                "system": "Snowflake",
                "platform": "Snowflake",
            },
            "aspects": {
                "dataplex-types.global.generic": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/generic", "data": {}},
                "dataplex-types.global.schema": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/schema", "data": schema_data},
                "dataplex-types.global.overview": {"aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview", "data": {"content": overview_html}},
                f"{pid}.global.retail-snowflake-table": {"aspectType": AT("retail-snowflake-table"), "data": marker_data},
            },
        }
        res = api_call(f"{DATAPLEX_URL}/{EG}/entries?entryId={tid}", "POST", t_body)
        if res.get("_exists"):
            api_call(f"{DATAPLEX_URL}/{EG}/entries/{tid}", "PATCH", t_body)

        entry_path = f"{EG}/entries/{tid}"

        # Apply the 7 existing retail-* aspect types
        # 1. retail-data-classification -> Third-Party Licensed
        set_entry_aspect(cfg, entry_path, "retail-data-classification", {
            "classification_level": "Third-Party Licensed",
            "pii_category": "Not PII",
            "requires_encryption": True,
            "requires_masking": False,
            "regulatory_scope": "Vendor Data License / No PII (cloud_platform=Snowflake, data_residency=External / Non-GCP)",
        })
        # 2. retail-access-control -> External Vendor Agreement
        set_entry_aspect(cfg, entry_path, "retail-access-control", {
            "access_level": "External Vendor Agreement",
            "authorized_roles": "Merchandising Manager, Category Manager, Supply Chain Planner, Pricing Analyst (Owner: Sarah Jenkins, VP of Merchandising Analytics & Enterprise Data Procurement; Agreement #NWR-NEXUS-2026)",
            "requires_mfa": True,
            "need_to_know_applies": True,
            "audit_all_access": True,
        })
        # 3. retail-regulatory-compliance -> Vendor Data License / No PII
        set_entry_aspect(cfg, entry_path, "retail-regulatory-compliance", {
            "applicable_regulations": "Vendor Data License / No PII",
            "compliance_status": "Compliant",
            "last_audit_date": "2026-03-15",
            "audit_frequency": "Annual",
            "compliance_notes": f"Third-party licensed syndicated data in Snowflake (cloud_platform=Snowflake, data_residency=External / Non-GCP). Governed under External Vendor Agreement #NWR-NEXUS-2026 owned by Sarah Jenkins (VP of Merchandising Analytics) & Enterprise Data Procurement.",
        })
        # 4. retail-data-lineage-metadata -> cloud_platform="Snowflake", data_residency="External / Non-GCP"
        set_entry_aspect(cfg, entry_path, "retail-data-lineage-metadata", {
            "source_system": "NEXUS — Syndicated Retail Market Intelligence (Snowflake)",
            "ingestion_method": "API Integration",
            "refresh_frequency": "Daily",
            "data_flow_path": f"NEXUS Syndicated Feed -> Snowflake ({SF_DATABASE}.{SF_SCHEMA}.{name}) -> BigQuery retail_gold ({', '.join(target_gold)})",
            "cloud_platform": "Snowflake",
            "data_residency": "External / Non-GCP",
        })
        # 5. retail-data-retention
        set_entry_aspect(cfg, entry_path, "retail-data-retention", {
            "retention_period_years": 3,
            "governing_regulation": "Vendor Data License / No PII (Agreement #NWR-NEXUS-2026)",
            "retention_start_event": "Syndicated data publication date",
            "archival_required": False,
            "destruction_method": "Secure Purge",
        })
        # 6. retail-risk-classification
        set_entry_aspect(cfg, entry_path, "retail-risk-classification", {
            "risk_category": "Demand and Markdown Risk",
            "model_dependency": "Model Input",
            "materiality_level": "Significant",
            "sox_relevant": False,
        })
        # 7. retail-regulatory-reporting
        set_entry_aspect(cfg, entry_path, "retail-regulatory-reporting", {
            "report_name": "Third-Party Syndicated Data License & Residency Audit",
            "filing_frequency": "Quarterly",
            "regulatory_body": "Internal Audit",
            "schedule_line_item": "Schedule V-1: Cross-Cloud Snowflake Data Residency (External / Non-GCP)",
        })
        aspect_count += 8
        logger.info("  Table %s: created & applied 8 governance aspects (%d cols)", name, len(cols))
        time.sleep(0.5)

    logger.info("  Total table governance aspects applied: %d", aspect_count)


def create_nexus_lineage(cfg, pid):
    """Register Process 6 lineage: NEXUS (Snowflake) -> retail_gold benchmark comparison tables."""
    logger.info("=== Step 4: Creating Cross-Cloud Lineage (NEXUS Snowflake -> BigQuery retail_gold) ===")
    base = f"{LINEAGE_URL}/projects/{pid}/locations/{cfg['multi_region']}"

    process = api_call(f"{base}/processes", "POST", {
        "displayName": "NEXUS Syndicated Market Intelligence - Snowflake to BigQuery Gold Benchmarks",
        "origin": {"sourceType": "CUSTOM", "name": "nexus-snowflake-to-bq-gold"},
    })
    run = api_call(f"{LINEAGE_URL}/{process['name']}/runs", "POST", {
        "displayName": "NEXUS Cross-Cloud Benchmark Sync",
        "startTime": "2026-04-30T04:00:00Z",
        "endTime": "2026-04-30T04:20:00Z",
        "state": "COMPLETED",
    })

    links = []
    for tid, name, desc, cols, target_gold in NEXUS_TABLES:
        src_fqn = f"snowflake:{SF_ACCOUNT}.{SF_DATABASE}.{SF_SCHEMA}.{name}"
        for g_tbl in target_gold:
            tgt_fqn = f"bigquery:{pid}.retail_gold.{g_tbl}"
            links.append({
                "source": {"fullyQualifiedName": src_fqn},
                "target": {"fullyQualifiedName": tgt_fqn},
            })

    api_call(f"{LINEAGE_URL}/{run['name']}/lineageEvents", "POST", {
        "startTime": "2026-04-30T04:00:00Z",
        "endTime": "2026-04-30T04:20:00Z",
        "links": links,
    })
    logger.info("  Created %d cross-cloud lineage links (NEXUS Snowflake -> retail_gold)", len(links))


def main():
    cfg = load_config()
    pid = cfg["project_id"]
    et_loc = entry_type_location(cfg)
    eg_loc = entry_group_location(cfg)

    ensure_existing_aspect_enums(pid)
    create_nexus_infra(pid, et_loc, eg_loc)
    create_nexus_entries_and_aspects(cfg, pid, et_loc, eg_loc)
    create_nexus_lineage(cfg, pid)
    logger.info("Phase C1 NEXUS catalog + lineage setup complete!")


if __name__ == "__main__":
    main()
