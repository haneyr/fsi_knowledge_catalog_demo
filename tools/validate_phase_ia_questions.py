#!/usr/bin/env python3
"""Validate all 16 preset questions in website-live/static/index.html against post-Phase-E schemas."""

import json
import re
from pathlib import Path

FORBIDDEN_CROSS_CLOUD_WORDS = [
    "table", "tables", "join", "joins", "key", "keys", "schema", "schemas",
    "catalog", "lineage", "residency", "license", "licensing", "vendor agreement", "snowflake"
]


def load_all_schemas() -> dict[str, list[str]]:
    schema_map: dict[str, list[str]] = {}

    # 1. Load all 128 BigQuery table names from modules/bigquery-*/main.tf and website-live/app.py
    for tf_path in Path("modules").rglob("*.tf"):
        text = tf_path.read_text()
        for t in re.findall(r'"((?:gold|silver|bronze|ref|staging|snapshot|audit|vw)_[a-z0-9_]+)"', text):
            schema_map.setdefault(t, [])

    if Path("website-live/app.py").exists():
        app_text = Path("website-live/app.py").read_text()
        for t in re.findall(r"['\"]((?:gold|silver|bronze|ref|staging|snapshot|audit|vw|nexus)_[a-z0-9_]+)['\"]", app_text):
            schema_map.setdefault(t, [])

    # 2. Load table -> column mappings from scripts/01_create_glossary.py, scripts/09_simulate_queries.py, scripts/10_create_rule_library.py, agents/prompts.py
    if Path("scripts/01_create_glossary.py").exists():
        g_text = Path("scripts/01_create_glossary.py").read_text()
        for _, ds, tbl, col in re.findall(r"\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*(?:'([^']+)'|None)\)", g_text):
            cols = schema_map.setdefault(tbl, [])
            if col and col not in cols:
                cols.append(col)

    for py_path in [Path("scripts/09_simulate_queries.py"), Path("scripts/10_create_rule_library.py"), Path("scripts/02_create_scans.py")]:
        if py_path.exists():
            q_text = py_path.read_text()
            for m in re.finditer(r"SELECT\s+(.*?)\s+FROM\s+[^`\"]*[`\"\.]?((?:gold|silver|bronze|ref|staging|snapshot|audit)_[a-z0-9_]+)", q_text, re.I | re.S):
                cols_part, tbl = m.group(1), m.group(2)
                cols = schema_map.setdefault(tbl, [])
                for c in re.findall(r"\b([a-z][a-z0-9_]+)\b", cols_part.lower()):
                    if c not in {"select", "count", "sum", "avg", "min", "max", "distinct", "as", "case", "when", "then", "else", "end", "round", "safe_divide"} and c not in cols:
                        cols.append(c)

    # 3. Load all 6 NEXUS tables & columns from scripts/17_create_nexus_c1.py
    if Path("scripts/17_create_nexus_c1.py").exists():
        n_text = Path("scripts/17_create_nexus_c1.py").read_text()
        for m in re.finditer(r'"(nexus_[a-z0-9_]+)"', n_text):
            tbl = m.group(1)
            chunk = n_text[m.start():m.start() + 1600]
            cols = re.findall(r'\("([a-z0-9_]+)",\s*"[A-Z]', chunk)
            existing = schema_map.setdefault(tbl, [])
            for c in cols:
                if c not in existing:
                    existing.append(c)

    return schema_map


EXPECTED_QUESTION_MAPPING = {
    ("merchandising", 1): {
        "tables": ["gold_assortment_performance"],
        "columns": {"gold_assortment_performance": ["assortment_name", "market_value", "ytd_return"]},
    },
    ("merchandising", 2): {
        "tables": ["silver_inventory_positions", "silver_product_skus", "silver_merch_assortments", "gold_markdown_risk_var"],
        "columns": {
            "silver_product_skus": ["gtin_13", "sku_code"],
            "gold_markdown_risk_var": ["var_99_1d"],
        },
    },
    ("merchandising", 3): {
        "tables": ["gold_assortment_performance", "silver_merch_assortments", "silver_product_skus"],
        "columns": {
            "silver_product_skus": ["gtin_13", "sku_code"],
        },
    },
    ("merchandising", 4): {
        "tables": ["gold_assortment_performance", "gold_markdown_risk_var", "gold_financial_summary"],
        "columns": {
            "gold_assortment_performance": ["assortment_name", "market_value", "ytd_return"],
            "gold_markdown_risk_var": ["var_99_1d"],
        },
    },
    ("customer", 1): {
        "tables": ["gold_customer_360"],
        "columns": {"gold_customer_360": ["customer_id", "customer_segment", "total_loyalty_balance"]},
    },
    ("customer", 2): {
        "tables": ["gold_customer_360", "silver_stores", "silver_bnpl_plans", "silver_ecom_orders"],
        "columns": {
            "gold_customer_360": ["customer_id", "customer_segment", "total_loyalty_balance", "primary_store_id"],
            "silver_bnpl_plans": ["return_risk_score_at_signup"],
        },
    },
    ("customer", 3): {
        "tables": ["gold_customer_360", "silver_customers", "silver_loyalty_accounts", "bronze_customers", "bronze_loyalty_accounts"],
        "columns": {
            "gold_customer_360": ["customer_id", "customer_segment", "total_loyalty_balance"],
            "silver_customers": ["customer_id", "customer_segment"],
            "silver_loyalty_accounts": ["current_balance"],
        },
    },
    ("customer", 4): {
        "tables": ["gold_customer_360", "silver_customers", "silver_privacy_consents", "gold_promo_fraud_scoring", "bronze_fraud_alerts", "bronze_high_value_refunds"],
        "columns": {
            "gold_customer_360": ["customer_id", "kyc_status", "kyc_risk_rating"],
            "gold_promo_fraud_scoring": ["kyc_risk_rating"],
        },
    },
    ("privacy", 1): {
        "tables": ["gold_bnpl_plan_summary", "silver_bnpl_plans"],
        "columns": {
            "gold_bnpl_plan_summary": ["plan_type", "risk_rating", "avg_return_risk_score"],
            "silver_bnpl_plans": ["return_risk_score_at_signup"],
        },
    },
    ("privacy", 2): {
        "tables": ["gold_bnpl_delinquency_analysis", "silver_bnpl_plans", "bronze_bnpl_plans"],
        "columns": {
            "gold_bnpl_delinquency_analysis": ["classified_count", "avg_origination_risk_score"],
            "silver_bnpl_plans": ["delinquency_status"],
            "bronze_bnpl_plans": ["delinquency_status"],
        },
    },
    ("privacy", 3): {
        "tables": ["silver_customers", "bronze_customers", "bronze_store_cards", "bronze_payment_tenders"],
        "columns": {
            "silver_customers": ["customer_id", "member_tin_masked"],
            "bronze_customers": ["customer_id", "member_tin"],
        },
    },
    ("privacy", 4): {
        "tables": ["gold_compliance_dashboard", "staging_pci_aoc_summary", "staging_ccpa_dsar_log"],
        "columns": {},
    },
    ("multicloud", 1): {
        "tables": ["gold_assortment_performance", "gold_gross_margin_analysis", "nexus_category_market_share"],
        "columns": {
            "gold_assortment_performance": ["assortment_name", "market_value", "ytd_return"],
            "nexus_category_market_share": ["category_name", "total_market_sales_usd", "northwind_market_share_pct", "benchmark_gross_margin_pct"],
        },
    },
    ("multicloud", 2): {
        "tables": ["silver_product_skus", "silver_competitor_pricing", "nexus_competitor_prices"],
        "columns": {
            "silver_product_skus": ["gtin_13", "sku_code"],
            "nexus_competitor_prices": ["gtin_13", "sku_code", "competitor_regular_price", "competitor_promo_price", "northwind_shelf_price"],
        },
    },
    ("multicloud", 3): {
        "tables": ["gold_store_performance", "silver_stores", "nexus_regional_demand_index"],
        "columns": {
            "nexus_regional_demand_index": ["region_code", "category_name", "demand_velocity_index", "foot_traffic_index"],
        },
    },
    ("multicloud", 4): {
        "tables": ["gold_assortment_performance", "gold_loyalty_account_summary", "nexus_basket_affinity"],
        "columns": {
            "gold_assortment_performance": ["assortment_name"],
            "nexus_basket_affinity": ["anchor_category", "attached_category", "co_occurrence_rate_pct", "affinity_lift_ratio"],
        },
    },
}


def main():
    html = Path("website-live/static/index.html").read_text()
    narratives = {}
    for tab in ["merchandising", "customer", "privacy", "multicloud"]:
        m = re.search(rf"{tab}:\s*\{{.*?steps:\s*\[(.*?)\],\s*\}}", html, re.S)
        steps = []
        if m:
            for sm in re.finditer(r"\{\s*cat:\s*'([^']+)',\s*q:\s*'((?:\\'|[^'])+)'\s*\}", m.group(1)):
                steps.append({"cat": sm.group(1), "q": sm.group(2).replace("\\'", "'")})
        narratives[tab] = steps

    schema_map = load_all_schemas()

    results = []
    failed = []
    for tab, steps in narratives.items():
        for idx, step in enumerate(steps, 1):
            spec = EXPECTED_QUESTION_MAPPING[(tab, idx)]
            missing_tables = [t for t in spec["tables"] if t not in schema_map]

            explicit_tables = re.findall(r"\b((?:gold|silver|bronze|ref|staging|snapshot|audit|nexus)_[a-z0-9_]+)\b", step["q"])
            for et in explicit_tables:
                if et not in schema_map and et not in missing_tables:
                    missing_tables.append(et)

            missing_cols = {}
            for t, cols in spec["columns"].items():
                actual = set(schema_map.get(t, []))
                mcols = [c for c in cols if c not in actual]
                if mcols:
                    missing_cols[t] = mcols

            forbidden_hits = []
            if tab == "multicloud":
                q_lower = step["q"].lower()
                for w in FORBIDDEN_CROSS_CLOUD_WORDS:
                    if re.search(rf"\b{re.escape(w)}\b", q_lower):
                        forbidden_hits.append(w)

            ok = not missing_tables and not missing_cols and not forbidden_hits
            rec = {
                "tab": tab,
                "index": idx,
                "chip": step["cat"],
                "question": step["q"],
                "validated_tables": spec["tables"],
                "explicit_tables_in_q": explicit_tables,
                "missing_tables": missing_tables,
                "missing_columns": missing_cols,
                "forbidden_words": forbidden_hits,
                "valid": ok,
            }
            results.append(rec)
            if not ok:
                failed.append(rec)

    Path("logs").mkdir(exist_ok=True)
    Path("logs/phase_ia_schema_validation.json").write_text(json.dumps(results, indent=2))
    print(f"Total tables in catalog: {len(schema_map)} | Questions validated: {len(results)} | Passed: {len(results) - len(failed)} | Failed: {len(failed)}")
    if failed:
        print("FAILED:", json.dumps(failed, indent=2))


if __name__ == "__main__":
    main()
