#!/usr/bin/env python3
"""Finalize P1 local refactor for Northwind Retail Knowledge Catalog Demo.

Updates:
1. deploy-bq.sh, deploy-bq-nokc.sh, deploy-full.sh, clean_up.sh, post_deploy.sh
   (mTLS env vars, RETAIL_TAXONOMY_DISPLAY_NAME, [Retail] dataset descriptions, 4 required labels)
2. modules/bigquery-{medallion,reference,dashboards}/main.tf ([Retail] descriptions + 4 labels)
3. agents/agent_{basic,scaled,kc}/agent.py and agents/deploy_agents.sh
   (fix BigQueryAgentAnalyticsPlugin import, fix _BASE_SUFFIXES in agent_scaled,
   set [Retail] descriptions and retail-agent-* names)
4. modules/bigquery-*/sql/*.sql (consistent retail string literals across Bronze/Silver/Gold/Ref)
5. demo/demo_questions.md, demo/demo_script.md, eval/*, website-live/*, README.md, cloudbuild.yaml, uv.lock
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def update_deploy_scripts():
    mtls_header = (
        "# Disable gcloud mTLS client-cert helper (avoids Python 3.14 segfault in bq CLI)\n"
        "export GOOGLE_API_USE_CLIENT_CERTIFICATE=false\n"
        "export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false\n"
        "export RETAIL_TAXONOMY_DISPLAY_NAME=\"${RETAIL_TAXONOMY_DISPLAY_NAME:-Retail Demo Sensitivity Taxonomy (alitch)}\"\n"
    )

    # 1. deploy-bq.sh
    p = os.path.join(ROOT, "deploy-bq.sh")
    with open(p, "r") as f:
        c = f.read()
    if "GOOGLE_API_USE_CLIENT_CERTIFICATE" not in c:
        c = c.replace("set -e\n", "set -e\n\n" + mtls_header, 1)

    old_ds_loop = """echo "--- Creating datasets ---"
for ds in retail_bronze retail_silver retail_gold retail_scan_results retail_staging retail_snapshots retail_audit retail_reference retail_dashboards; do
  bq mk --dataset --location="${LOCATION}" --project_id="${PROJECT_ID}" "${ds}" 2>/dev/null || true
done
echo "  9 datasets ready\""""

    new_ds_loop = """echo "--- Creating datasets with [Retail] descriptions and labels ---"
declare -A DS_DESC=(
  ["retail_bronze"]="[Retail] Northwind Retail Group — raw ingestion layer (ORION + LUMEN + HELIOS)"
  ["retail_silver"]="[Retail] Northwind Retail Group — cleansed and conformed layer"
  ["retail_gold"]="[Retail] Northwind Retail Group — business analytics layer"
  ["retail_scan_results"]="[Retail] Data quality and profile scan results for Retail tables"
  ["retail_staging"]="[Retail] Retail compliance and omnichannel filing staging tables"
  ["retail_snapshots"]="[Retail] Historical inventory, loyalty, and pricing snapshot tables"
  ["retail_audit"]="[Retail] Retail data access audit trail and model decision logs"
  ["retail_reference"]="[Retail] Reference and lookup tables for Retail data validation"
  ["retail_dashboards"]="[Retail] Pre-aggregated views for Retail Looker Studio dashboards"
)
for ds in retail_bronze retail_silver retail_gold retail_scan_results retail_staging retail_snapshots retail_audit retail_reference retail_dashboards; do
  desc="${DS_DESC[$ds]}"
  bq mk --dataset --location="${LOCATION}" --project_id="${PROJECT_ID}" \\
    --description="${desc}" \\
    --label=use-case:retail --label=demo:retail-knowledge-catalog --label=owner:alitch --label=env:demo \\
    "${ds}" 2>/dev/null || \\
  bq update --dataset --project_id="${PROJECT_ID}" \\
    --description="${desc}" \\
    --set_label=use-case:retail --set_label=demo:retail-knowledge-catalog --set_label=owner:alitch --set_label=env:demo \\
    "${PROJECT_ID}:${ds}" >/dev/null 2>&1 || true
done
echo "  9 datasets ready\""""
    c = c.replace(old_ds_loop, new_ds_loop)
    with open(p, "w") as f:
        f.write(c)

    # 2. deploy-bq-nokc.sh
    p = os.path.join(ROOT, "deploy-bq-nokc.sh")
    with open(p, "r") as f:
        c = f.read()
    if "GOOGLE_API_USE_CLIENT_CERTIFICATE" not in c:
        c = c.replace("set -e\n", "set -e\n\n" + mtls_header, 1)
    old_nokc_loop = """echo "--- Creating _nokc datasets ---"
for ds in retail_bronze_nokc retail_silver_nokc retail_gold_nokc retail_staging_nokc retail_snapshots_nokc retail_audit_nokc retail_reference_nokc retail_dashboards_nokc; do
  bq mk --dataset --location="${LOCATION}" --project_id="${PROJECT_ID}" "${ds}" 2>/dev/null || true
done
echo "  8 datasets ready\""""
    new_nokc_loop = """echo "--- Creating _nokc datasets with [Retail] descriptions and labels ---"
for ds in retail_bronze_nokc retail_silver_nokc retail_gold_nokc retail_staging_nokc retail_snapshots_nokc retail_audit_nokc retail_reference_nokc retail_dashboards_nokc; do
  desc="[Retail] Uncataloged shadow dataset (${ds}) for Scaled Agent baseline comparison"
  bq mk --dataset --location="${LOCATION}" --project_id="${PROJECT_ID}" \\
    --description="${desc}" \\
    --label=use-case:retail --label=demo:retail-knowledge-catalog --label=owner:alitch --label=env:demo \\
    "${ds}" 2>/dev/null || \\
  bq update --dataset --project_id="${PROJECT_ID}" \\
    --description="${desc}" \\
    --set_label=use-case:retail --set_label=demo:retail-knowledge-catalog --set_label=owner:alitch --set_label=env:demo \\
    "${PROJECT_ID}:${ds}" >/dev/null 2>&1 || true
done
echo "  8 datasets ready\""""
    c = c.replace(old_nokc_loop, new_nokc_loop)
    with open(p, "w") as f:
        f.write(c)

    # 3. deploy-full.sh
    p = os.path.join(ROOT, "deploy-full.sh")
    with open(p, "r") as f:
        c = f.read()
    if "GOOGLE_API_USE_CLIENT_CERTIFICATE" not in c:
        c = c.replace("set -e\n", "set -e\n\n" + mtls_header, 1)
    c = c.replace(
        'bq mk --dataset --location=us --project_id="${PROJECT_ID}" retail_agent_analytics 2>/dev/null || true',
        'bq mk --dataset --location=us --project_id="${PROJECT_ID}" --description="[Retail] ADK BigQuery Agent Analytics event log dataset" --label=use-case:retail --label=demo:retail-knowledge-catalog --label=owner:alitch --label=env:demo retail_agent_analytics 2>/dev/null || bq update --dataset --project_id="${PROJECT_ID}" --description="[Retail] ADK BigQuery Agent Analytics event log dataset" --set_label=use-case:retail --set_label=demo:retail-knowledge-catalog --set_label=owner:alitch --set_label=env:demo "${PROJECT_ID}:retail_agent_analytics" >/dev/null 2>&1 || true',
    )
    c = c.replace("secret=basic-agent-id", "secret=retail-basic-agent-id")
    c = c.replace("secret=scaled-agent-id", "secret=retail-scaled-agent-id")
    c = c.replace("secret=kc-agent-id", "secret=retail-kc-agent-id")
    with open(p, "w") as f:
        f.write(c)

    # 4. post_deploy.sh & clean_up.sh
    for script_name in ("post_deploy.sh", "clean_up.sh"):
        p = os.path.join(ROOT, script_name)
        with open(p, "r") as f:
            c = f.read()
        if "GOOGLE_API_USE_CLIENT_CERTIFICATE" not in c:
            c = c.replace("set -e\n", "set -e\n\n" + mtls_header, 1)
        with open(p, "w") as f:
            f.write(c)


def update_terraform_files():
    labels_block = """  labels = {
    use-case = "retail"
    demo     = "retail-knowledge-catalog"
    owner    = "alitch"
    env      = "demo"
  }"""
    for rel in (
        "modules/bigquery-medallion/main.tf",
        "modules/bigquery-reference/main.tf",
        "modules/bigquery-dashboards/main.tf",
    ):
        p = os.path.join(ROOT, rel)
        with open(p, "r") as f:
            c = f.read()
        c = c.replace("# ORION (Retail Retail)", "# ORION (Store Ops & POS)")
        c = c.replace("# LUMEN (Omnichannel Loyalty Management)", "# LUMEN (Digital Commerce & Loyalty)")
        c = c.replace("# HELIOS (Finance & Risk)", "# HELIOS (Merchandising, Supply Chain & Finance)")

        def repl_ds(match):
            block = match.group(0)
            if 'description = "[Retail] ' not in block:
                block = re.sub(r'description\s*=\s*"([^"]+)"', r'description = "[Retail] \1"', block)
            if "labels =" not in block:
                block = block[:-1] + labels_block + "\n}"
            return block

        c = re.sub(r'resource "google_bigquery_dataset" "[a-z_]+" \{[^}]+\}', repl_ds, c)
        with open(p, "w") as f:
            f.write(c)


def update_agents():
    # 1. Fix BigQueryAgentAnalyticsPlugin import & add [Retail] descriptions in agent_basic, agent_scaled, agent_kc
    for rel, agent_id_name, desc in [
        ("agents/agent_basic/agent.py", "retail_agent_basic", "[Retail] Northwind Retail Basic Agent (5 gold tables)"),
        ("agents/agent_scaled/agent.py", "retail_agent_scaled", "[Retail] Northwind Retail Scaled Agent (128 tables without Knowledge Catalog)"),
        ("agents/agent_kc/agent.py", "retail_agent_kc", "[Retail] Northwind Retail Knowledge Catalog Agent (128+ tables with KC MCP discovery)"),
    ]:
        p = os.path.join(ROOT, rel)
        with open(p, "r") as f:
            c = f.read()
        c = c.replace(
            "from google.adk.plugins.bigquery_retail_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin",
            "from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin",
        )
        c = c.replace("senior financial data analyst", "senior retail & merchandising data analyst")
        c = c.replace("financial data analyst", "retail data analyst")
        # Add description="[Retail] ..." to Agent() if not present
        if 'description="[Retail]' not in c:
            c = c.replace(
                'model="gemini-2.5-flash",',
                f'model="gemini-2.5-flash",\n    description="{desc}",',
            )
        with open(p, "w") as f:
            f.write(c)

    # 2. Fix _BASE_SUFFIXES and _OTHER_TABLES in agents/agent_scaled/agent.py
    p = os.path.join(ROOT, "agents/agent_scaled/agent.py")
    with open(p, "r") as f:
        c = f.read()
    old_suffixes = re.search(r"_BASE_SUFFIXES = \[[^\]]+\]", c, re.DOTALL)
    new_suffixes = """_BASE_SUFFIXES = [
    'customers','loyalty_accounts','pos_transactions','bnpl_plans','bnpl_payments','store_cards',
    'payment_tenders','fraud_alerts','privacy_consents','stores','store_associates','high_value_refunds',
    'vendor_settlements','kiosk_transactions','vip_members','merch_assortments','inventory_positions','ecom_orders',
    'product_skus','category_managers','assortment_performance','promo_rules','category_benchmarks','customer_preferences',
    'return_risk_profiles','reward_redemptions','carrier_feeds','gl_entries','gl_accounts',
    'cost_centers','working_capital','shrinkage_exposures','suppliers','competitor_pricing',
    'demand_scenarios','audit_events','compliance_attestations','markdown_rates','fx_rates',
    'promo_abuse_cases',
]"""
    if old_suffixes:
        c = c.replace(old_suffixes.group(0), new_suffixes)

    old_other = re.search(r"_OTHER_TABLES = \[[^\]]+\]", c, re.DOTALL)
    new_other = """_OTHER_TABLES = [
    'ref_merch_category_codes','ref_country_codes','ref_currency_codes','ref_gtin_master',
    'ref_sku_gtin_mapping','ref_supplier_registry','ref_sales_region_codes','ref_product_catalog',
    'ref_loyalty_tiers','ref_gl_account_hierarchy',
    'staging_pci_aoc_summary','staging_channel_revenue_recon','staging_supplier_audit_schedule',
    'staging_ccpa_dsar_log','staging_annual_omniretail_filing',
    'snapshot_monthly_loyalty_balances','snapshot_quarterly_inventory_positions','snapshot_daily_competitor_pricing',
    'audit_data_access_log','audit_model_decisions',
]"""
    if old_other:
        c = c.replace(old_other.group(0), new_other)
    with open(p, "w") as f:
        f.write(c)

    # 3. Clean up agents/agent_kc/agent.py examples & Snowflake prompt
    p = os.path.join(ROOT, "agents/agent_kc/agent.py")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace("What is our total relationship value for high-net-worth clients?", "What is our total lifetime value for VIP loyalty members?")
    c = c.replace("Show me suspicious activity trends by quarter", "Show me return fraud and promo abuse trends by quarter")
    c = c.replace("What is our CET1 capital ratio and how does it compare to minimums?", "What is our working capital ratio and how does it compare to minimums?")
    c = c.replace("Which stores have the highest combined retail + loyalty revenue?", "Which stores have the highest combined POS + e-commerce loyalty revenue?")
    c = c.replace("SOFR, Treasury, yield, interest rate, benchmark, prices, product_skus", "markdown rate, promotional discount, category benchmark, prices, product_skus")
    c = c.replace("FX, forex, credit spread, volatility, economic indicators, market data, index, fundamentals", "FX, forex, supplier terms, demand volatility, retail indicators, competitor pricing, index, fundamentals")
    c = c.replace('search_entries("snowflake SOFR"), search_entries("snowflake Treasury yield")', 'search_entries("snowflake competitor pricing"), search_entries("snowflake category benchmark")')
    c = c.replace("interest rates", "markdown rates")
    c = c.replace("interest rate curves (SOFR, Fed Funds, Treasuries)", "markdown rate curves and promotional elasticity")
    c = c.replace("credit spreads", "supplier margin spreads")
    with open(p, "w") as f:
        f.write(c)

    # 4. Update agents/deploy_agents.sh for retail-agent-* names & [Retail] display names
    p = os.path.join(ROOT, "agents/deploy_agents.sh")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace(
        'adk deploy agent_engine \\\n      --project="${PROJECT_ID}" \\\n      --region="${REGION}" \\\n      "${agent_dir}" 2>&1',
        'adk deploy agent_engine \\\n      --project="${PROJECT_ID}" \\\n      --region="${REGION}" \\\n      --display_name="[Retail] retail-${agent_dir/_/-}" \\\n      "${agent_dir}" 2>&1',
    )
    c = c.replace('secret_name="${agent_dir#agent_}-agent-id"', 'secret_name="retail-${agent_dir#agent_}-agent-id"')
    c = c.replace("secret=basic-agent-id", "secret=retail-basic-agent-id")
    c = c.replace("secret=scaled-agent-id", "secret=retail-scaled-agent-id")
    c = c.replace("secret=kc-agent-id", "secret=retail-kc-agent-id")
    with open(p, "w") as f:
        f.write(c)


def update_sql_files():
    sql_files = glob.glob(os.path.join(ROOT, "modules/bigquery-*/sql/*.sql"))
    replacements = [
        ("CONCAT('fsi_',", "CONCAT('retail_',"),
        ("'CHECKING'", "'POINTS_REWARDS'"),
        ("'SAVINGS'", "'VIP_CASHBACK'"),
        ("'MONEY_MARKET'", "'STORE_CREDIT'"),
        ("'CD'", "'GIFT_WALLET'"),
        ("'IRA'", "'EMPLOYEE_PERKS'"),
        ("'Personal Checking'", "'Northwind Points Rewards'"),
        ("'Personal Savings'", "'VIP Cashback Tier'"),
        ("'Money Market Account'", "'Omnichannel Store Credit'"),
        ("'Common Stock'", "'Apparel & Footwear'"),
        ("'Preferred Stock'", "'Accessories & Jewelry'"),
        ("'Corporate Bond'", "'Home & Living'"),
        ("'Treasury Bond'", "'Core Essentials'"),
        ("'Municipal Bond'", "'Outdoor & Activewear'"),
        ("'Municipal Bonds'", "'Outdoor & Activewear'"),
        ("'Mutual Fund'", "'Seasonal & Gifting'"),
        ("'Money Market'", "'Beauty & Personal Care'"),
        ("'Fixed Income'", "'Hardlines'"),
        ("'Equity'", "'Softlines'"),
        ("'ETF'", "'Essentials Bundle'"),
        ("'Real Estate'", "'Home Furnishings'"),
        ("'Treasury'", "'Core Essentials'"),
        ("'Municipal'", "'Outdoor & Activewear'"),
        ("'DFAST Summary'", "'CCPA Annual Privacy Audit'"),
        ("'SAR Filing'", "'Promo Abuse Incident Report'"),
        ("'CTR Filing'", "'High-Value Refund Report'"),
        ("'PCI-SSC/OCC'", "'PCI-SSC'"),
        ("'Federal Reserve'", "'FTC / California Privacy Protection Agency'"),
        ("'OCC'", "'PCI Security Standards Council'"),
        ("'Suspicious Wire Transfer'", "'Suspicious High-Value Refund'"),
        ("CONCAT('ATM-',", "CONCAT('KSK-',"),
        ("CONCAT('ATM-TERM-',", "CONCAT('KSK-TERM-',"),
        ("'ACH Debit'", "'Store Card Debit'"),
        ("'ACH Credit'", "'Loyalty Credit Refund'"),
        ("'Wire Transfer'", "'Vendor EFT Settlement'"),
        ("'ATM Withdrawal'", "'In-Store Kiosk Redemption'"),
        ("'ATM'", "'In-Store Kiosk'"),
        ("'Wire'", "'Vendor EFT'"),
        ("'ACH'", "'Direct Debit'"),
        ("CONCAT('KYC-',", "CONCAT('CNS-',"),
        ("'SAR Investigation'", "'Serial Return Abuse Investigation'"),
        ("'CTR Review'", "'High-Value Refund Review'"),
        ("'OFAC Match'", "'Sanctioned Vendor Screening Match'"),
        ("'BSA/Promo-Fraud Alert'", "'Promo Stacking & Coupon Fraud Alert'"),
        ("'Closed - SAR Filed'", "'Closed - Fraud Report Filed'"),
        ("CONCAT('SAR-',", "CONCAT('FRD-',"),
        ("CONCAT('Meridian ',", "CONCAT('Northwind ',"),
        ("CONCAT('ACH-',", "CONCAT('VND-',"),
        ("'UHNW'", "'Diamond VIP'"),
        ("'Ultra HNW'", "'Diamond VIP'"),
        ("'HNW'", "'Platinum VIP'"),
        ("'BSA/Promo-Fraud'", "'Promo & Return Fraud'"),
        ("CONCAT('KYC Overdue Rate - ',", "CONCAT('Consent Renewal Overdue Rate - ',"),
        ("'Fed Funds Sold'", "'In-Transit Inventory'"),
        ("'ALLL'", "'Inventory Shrinkage Reserve'"),
        ("'Other RE Owned'", "'Store Leasehold Improvements'"),
        ("'Fed Funds Purchased'", "'Trade Payables - Merchandise'"),
    ]
    for path in sql_files:
        with open(path, "r") as f:
            c = f.read()
        orig = c
        for old, new in replacements:
            c = c.replace(old, new)
        if c != orig:
            with open(path, "w") as f:
                f.write(c)


def update_demo_eval_website():
    # 1. website-live/deploy.sh: support retail-*-agent-id secrets
    p = os.path.join(ROOT, "website-live/deploy.sh")
    with open(p, "r") as f:
        c = f.read()
    if "GOOGLE_API_USE_CLIENT_CERTIFICATE" not in c:
        c = c.replace(
            "set -e\n",
            "set -e\n\nexport GOOGLE_API_USE_CLIENT_CERTIFICATE=false\nexport CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false\n",
            1,
        )
    with open(p, "w") as f:
        f.write(c)

    # 2. website-live/app.py: fix isinstance(output, dict) for Tier A regex (`isin`),
    #    update GLOSSARY_LINKS and _discover_glossary for [Retail] prefixed terms
    p = os.path.join(ROOT, "website-live/app.py")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace("isinstance(output, dict)", "type(output) is dict")
    old_glinks = re.search(r"GLOSSARY_LINKS = \{[^}]+\}", c, re.DOTALL)
    new_glinks = """GLOSSARY_LINKS = {
    '[Retail] Return-Risk Score': ['gold_bnpl_plan_summary', 'silver_bnpl_plans', 'bronze_bnpl_plans', 'gold_bnpl_delinquency_analysis'],
    'Return-Risk Score': ['gold_bnpl_plan_summary', 'silver_bnpl_plans', 'bronze_bnpl_plans', 'gold_bnpl_delinquency_analysis'],
    '[Retail] Customer Lifetime Value (CLV)': ['gold_customer_360', 'gold_category_manager_scorecard', 'gold_vip_member_revenue', 'silver_vip_members'],
    'CLV': ['gold_customer_360', 'gold_category_manager_scorecard', 'gold_vip_member_revenue', 'silver_vip_members'],
    '[Retail] Return Abuse Alert': ['gold_return_fraud_analytics', 'gold_promo_fraud_scoring', 'bronze_fraud_alerts', 'bronze_promo_abuse_cases'],
    'Return Abuse Alert': ['gold_return_fraud_analytics', 'gold_promo_fraud_scoring', 'bronze_fraud_alerts', 'bronze_promo_abuse_cases'],
    '[Retail] Working Capital Ratio': ['gold_working_capital_adequacy', 'silver_working_capital', 'bronze_working_capital'],
    'Working Capital Ratio': ['gold_working_capital_adequacy', 'silver_working_capital', 'bronze_working_capital'],
    '[Retail] Customer ID': ['gold_customer_360', 'silver_customers', 'bronze_customers', 'gold_loyalty_account_summary'],
    'Customer ID': ['gold_customer_360', 'silver_customers', 'bronze_customers', 'gold_loyalty_account_summary'],
    '[Retail] BNPL Delinquency Rate': ['gold_bnpl_plan_summary', 'gold_bnpl_delinquency_analysis', 'silver_bnpl_plans'],
    'Delinquency': ['gold_bnpl_plan_summary', 'gold_bnpl_delinquency_analysis', 'silver_bnpl_plans'],
    '[Retail] Marketing Consent & Verification': ['gold_promo_fraud_scoring', 'bronze_privacy_consents', 'gold_customer_360'],
    'Consent Verification': ['gold_promo_fraud_scoring', 'bronze_privacy_consents', 'gold_customer_360'],
    '[Retail] Markdown Value at Risk (VaR)': ['gold_markdown_risk_var', 'silver_inventory_positions', 'silver_competitor_pricing'],
    'VaR': ['gold_markdown_risk_var', 'silver_inventory_positions', 'silver_competitor_pricing'],
    '[Retail] Global Trade Item Number (GTIN-13)': ['silver_product_skus', 'bronze_product_skus', 'gold_inventory_allocation'],
    'GTIN': ['silver_product_skus', 'bronze_product_skus', 'gold_inventory_allocation'],
    '[Retail] Store ID': ['gold_store_performance', 'gold_customer_360', 'bronze_stores', 'gold_gross_margin_analysis'],
    'Store': ['gold_store_performance', 'gold_customer_360', 'bronze_stores', 'gold_gross_margin_analysis'],
    '[Retail] Gross Margin Percentage': ['gold_gross_margin_analysis', 'silver_loyalty_accounts', 'silver_bnpl_plans'],
    'Gross Margin': ['gold_gross_margin_analysis', 'silver_loyalty_accounts', 'silver_bnpl_plans'],
    '[Retail] Return Risk Tier': ['gold_bnpl_plan_summary', 'silver_bnpl_plans', 'bronze_bnpl_plans'],
    'Risk Rating': ['gold_bnpl_plan_summary', 'silver_bnpl_plans', 'bronze_bnpl_plans'],
}"""
    if old_glinks:
        c = c.replace(old_glinks.group(0), new_glinks)

    old_disc_loop = """            for display_name in terms:
                lower = display_name.lower()
                GLOSSARY_TERM_MAP[lower] = [display_name]
                words = lower.split()
                if len(words) > 1:
                    existing = GLOSSARY_TERM_MAP.get(words[0], [])
                    if display_name not in existing:
                        GLOSSARY_TERM_MAP[words[0]] = existing + [display_name]"""
    new_disc_loop = """            for display_name in terms:
                lower = display_name.lower()
                GLOSSARY_TERM_MAP[lower] = [display_name]
                clean = lower.replace('[retail] ', '').strip()
                if clean:
                    GLOSSARY_TERM_MAP[clean] = [display_name]
                    words = clean.split()
                    if len(words) > 1 and len(words[0]) >= 3:
                        existing = GLOSSARY_TERM_MAP.get(words[0], [])
                        if display_name not in existing:
                            GLOSSARY_TERM_MAP[words[0]] = existing + [display_name]"""
    c = c.replace(old_disc_loop, new_disc_loop)
    with open(p, "w") as f:
        f.write(c)

    # 3. website-live/static/index.html
    p = os.path.join(ROOT, "website-live/static/index.html")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace("Meridian <span>National Retailer</span>", "Northwind <span>Retail Group</span>")
    c = c.replace(
        "If commercial real estate defaults increased 5%, what would happen to our capital ratios?",
        "If seasonal apparel markdowns increased 5%, what would happen to our working capital and gross margin?",
    )
    c = c.replace(
        "Which stores have the highest combined retail and loyalty management revenue?",
        "Which stores have the highest combined in-store POS and e-commerce loyalty revenue?",
    )
    c = c.replace(
        "Are we meeting our PCI-DSS III capital requirements? What\\'s our buffer above the minimum?",
        "Are we meeting our working capital adequacy requirements, and what is our PCI-DSS compliance posture?",
    )
    c = c.replace(
        "Are we ready for our next regulatory filing? Summarize our key metrics across the call report schedules.",
        "Are we ready for our next compliance audit? Summarize our key metrics across PCI-DSS and CCPA/CPRA schedules.",
    )
    c = c.replace(
        "I need to investigate Promo-Fraud risk. Show me high-risk customers with their KYC status and any recent wire transfer activity.",
        "I need to investigate promo and return fraud risk. Show me high-risk customers with their consent verification status and recent high-value refund activity.",
    )
    c = c.replace(
        "Show me the current SOFR and Treasury yield curve alongside our net interest margin.",
        "Show me current competitor markdown rates alongside our gross margin performance.",
    )
    c = c.replace(
        "What\\'s our credit spread exposure by sector? Show current market spreads alongside our assortment risk.",
        "What\\'s our markdown Value-at-Risk exposure by category? Show competitor pricing alongside our assortment risk.",
    )
    with open(p, "w") as f:
        f.write(c)

    # 4. website-live/static/static-responses.json
    p = os.path.join(ROOT, "website-live/static/static-responses.json")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace("Meridian", "Northwind")
    c = c.replace('"AUM"', '"CLV"')
    c = c.replace('"SAR"', '"Return Abuse Alert"')
    c = c.replace('"KYC"', '"Consent Verification"')
    c = c.replace('"CET1 Ratio"', '"Working Capital Ratio"')
    with open(p, "w") as f:
        f.write(c)

    # 5. demo/demo_questions.md and demo/demo_script.md
    for rel in ("demo/demo_questions.md", "demo/demo_script.md"):
        p = os.path.join(ROOT, rel)
        with open(p, "r") as f:
            c = f.read()
        c = c.replace("branch revenue", "store revenue")
        c = c.replace("No branch manager", "No store manager")
        c = c.replace("branch manager", "store manager")
        c = c.replace("high-net-worth clients", "VIP loyalty members")
        c = c.replace("HNW clients", "VIP members")
        c = c.replace("HNW total exposure", "VIP member total relationship")
        c = c.replace("HNW Total Exposure", "VIP Member Total Relationship")
        c = c.replace("suspicious activity", "return fraud and promo abuse")
        c = c.replace("Suspicious Activity", "Return Fraud & Promo Abuse")
        c = c.replace("Interest Rate Risk", "Markdown & Gross Margin Risk")
        c = c.replace("interest rate exposure", "markdown and margin exposure")
        c = c.replace("interest rate risk", "markdown and margin risk")
        c = c.replace("Interest rate exposure", "Markdown and margin exposure")
        c = c.replace("PCI-DSS III Capital", "Working Capital & PCI-DSS Compliance")
        c = c.replace("PCI-DSS III capital", "working capital adequacy")
        c = c.replace("PCI-DSS III", "working capital & PCI-DSS")
        c = c.replace("Call Report Schedule RC-R", "Annual Omnichannel Retail Filing")
        c = c.replace("CRE stress test", "Seasonal Markdown Stress Test")
        c = c.replace("SOFR/Treasury yields", "competitor markdown curves")
        c = c.replace("Yield curve + NIM", "Competitor pricing + Gross Margin")
        with open(p, "w") as f:
            f.write(c)

    # 6. eval/metrics.py, eval/run_eval.py, eval/test_cases.yaml, demo/agent_comparison.ipynb
    p = os.path.join(ROOT, "eval/metrics.py")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace('"credit score", "fair isaac"', '"return risk", "return_risk_score"')
    c = c.replace('"AUM": ["aum", "assets under management"]', '"CLV": ["clv", "customer lifetime value"]')
    c = c.replace('"SAR": ["sar", "suspicious activity"]', '"Return Abuse Alert": ["return abuse", "fraud alert", "promo fraud"]')
    c = c.replace('"CET1 Ratio": ["cet1", "common equity tier", "capital ratio"]', '"Working Capital Ratio": ["working capital", "liquidity", "capital ratio"]')
    c = c.replace('"KYC": ["kyc", "know your customer"]', '"Consent Verification": ["privacy consent", "ccpa", "gdpr", "consent"]')
    c = c.replace('"Store": ["branch"]', '"Store": ["store", "store_id", "location"]')
    c = c.replace('"NIM": ["nim", "net interest margin"]', '"Gross Margin": ["gross margin", "margin", "markdown"]')
    c = c.replace('"Risk Rating": ["risk rating", "risk_rating", "credit quality"]', '"Risk Rating": ["risk rating", "risk_rating", "return risk"]')
    with open(p, "w") as f:
        f.write(c)

    p = os.path.join(ROOT, "eval/run_eval.py")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace("isinstance(args, dict)", "type(args) is dict")
    c = c.replace("digital_merchandising", "digital_commerce")
    with open(p, "w") as f:
        f.write(c)

    p = os.path.join(ROOT, "eval/test_cases.yaml")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace("digital_merchandising", "digital_commerce")
    c = c.replace("high-net-worth clients", "VIP loyalty members")
    c = c.replace("suspicious activity", "return fraud and promo abuse")
    c = c.replace("CET1", "Working Capital Ratio")
    c = c.replace("SAR", "Return Abuse Alert")
    c = c.replace("KYC", "Consent Verification")
    c = c.replace("AUM", "CLV")
    c = c.replace("NIM", "Gross Margin")
    with open(p, "w") as f:
        f.write(c)

    p = os.path.join(ROOT, "demo/agent_comparison.ipynb")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace("isinstance(fc.args, dict)", "type(fc.args) is dict")
    with open(p, "w") as f:
        f.write(c)

    # 7. cloudbuild.yaml, uv.lock, README.md
    p = os.path.join(ROOT, "cloudbuild.yaml")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace("fsi_knowledge_catalog_demo", "knowledge_catalog_demo")
    with open(p, "w") as f:
        f.write(c)

    p = os.path.join(ROOT, "uv.lock")
    with open(p, "r") as f:
        c = f.read()
    c = c.replace('name = "fsi-knowledge-catalog-demo"', 'name = "retail-knowledge-catalog-demo"')
    with open(p, "w") as f:
        f.write(c)

    p = os.path.join(ROOT, "README.md")
    with open(p, "r") as f:
        c = f.read()
    if "Derived from:" not in c:
        c = c.replace(
            "# [Retail] Northwind Retail Knowledge Catalog Demo",
            "# [Retail] Northwind Retail Knowledge Catalog Demo\n\n> **Derived from:** `https://github.com/haneyr/fsi_knowledge_catalog_demo` (refactored for the Northwind Retail Group omnichannel specialty retail domain).",
            1,
        )
    with open(p, "w") as f:
        f.write(c)


if __name__ == "__main__":
    update_deploy_scripts()
    update_terraform_files()
    update_agents()
    update_sql_files()
    update_demo_eval_website()
    print("Done finalizing retail refactor.")
