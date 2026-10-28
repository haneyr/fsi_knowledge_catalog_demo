# [Retail] Northwind Retail Group — Knowledge Catalog Demo Questions

These 16 questions (`3 base categories × 4 tiers` + `1 Cross-Cloud category × 4 tiers`) are synchronized with `website-live/static/index.html`.
Every category preserves the 4-chip difficulty ladder:
- **Tier 1**: Foundational Gold query — all three agents pass (`Basic`, `Scaled`, `KC`).
- **Tier 2**: Cross-domain / multi-table — `Basic` fails (missing tables) and `Scaled` starts failing (schema ambiguity across 128 tables).
- **Tier 3**: Governance & catalog metadata — requires Knowledge Catalog certifications, data owners/stewards, lineage, PCI/CCPA classification, or DQ scan rules (`Basic` and `Scaled` fail).
- **Tier 4**: Governed analytics stress test — combines catalog metadata filtering + multi-table SQL analytics; only `KC` survives.

---

## 1. MERCHANDISING & INVENTORY
*Personas: Merchandising Manager, Supply Chain Planner*

- **Tier 1 (`1 Assortment Margin`)**
  > Which merchandise assortments had the highest YTD return and market value in gold_assortment_performance?
  - *Tables*: `retail_gold.gold_assortment_performance`
  - *Expected behavior*: All three agents query `gold_assortment_performance` and return the top assortments (`PF-10002`, `PF-10005`, `PF-10001`, `PF-10004`, `PF-10003`).

- **Tier 2 (`2 Markdown Exposure`)**
  > For active merchandise assortments, which GTIN-13 SKUs carry the largest unrealized inventory loss, who is the assigned category manager, and how does their sector's 1-day 99% Markdown Value at Risk compare?
  - *Tables*: `retail_silver.silver_merch_assortments`, `retail_silver.silver_inventory_positions`, `retail_silver.silver_product_skus`, `retail_silver.silver_category_managers`, `retail_gold.gold_markdown_risk_var`
  - *Glossary*: `[Retail] Global Trade Item Number (GTIN-13)`, `[Retail] Markdown Value at Risk (VaR)`
  - *Expected behavior*: Basic fails (lacks SKU, inventory position, category manager, and markdown VaR tables). Scaled must disambiguate Bronze vs Silver tables (`bronze_merch_assortments` vs `silver_merch_assortments`, `bronze_inventory_positions` vs `silver_inventory_positions`, `bronze_product_skus` vs `silver_product_skus` vs `ref_product_catalog`) and join across 5 tables using non-obvious keys (`assortment_id`, `security_id`, `manager_id`, `sector`) while filtering 1-day `0.99` confidence VaR without column metadata. KC uses glossary and catalog descriptions to join cleanly.

- **Tier 3 (`3 Certification & GTIN DQ`)**
  > Which assortment and product SKU tables are certified in Knowledge Catalog, who owns them, and can we trust the GTIN-13 identifiers in silver_product_skus?
  - *Tables*: `retail_gold.gold_assortment_performance`, `retail_silver.silver_merch_assortments`, `retail_silver.silver_product_skus`
  - *Glossary*: `[Retail] Global Trade Item Number (GTIN-13)`
  - *Expected behavior*: Basic and Scaled have no catalog tools and cannot see certification status, owners, or DQ rules. KC looks up `retail-certification`, `retail-governance` (owners/stewards), and flags the 7% invalid GTIN-13 check-digit DQ issue on `silver_product_skus.gtin`.

- **Tier 4 (`4 Governed Markdown Plan`)**
  > Build a markdown risk plan for underperforming assortments using only certified Gold tables with no PCI-scoped columns, and quantify the working capital impact.
  - *Tables*: `retail_gold.gold_assortment_performance`, `retail_gold.gold_markdown_risk_var`, `retail_gold.gold_working_capital_adequacy`
  - *Glossary*: `[Retail] Markdown Value at Risk (VaR)`, `[Retail] Working Capital Ratio`
  - *Expected behavior*: Only KC verifies certification (`retail-certification`) and PCI scope (`retail-data-classification`), then combines assortment performance, markdown VaR, and working capital adequacy into a governed markdown plan.

---

## 2. CUSTOMER & LOYALTY
*Personas: Loyalty/CRM Marketer, Store Ops Director*

- **Tier 1 (`1 Loyalty Tiers`)**
  > How many active customers and what total relationship value do we have by customer segment in gold_customer_360?
  - *Tables*: `retail_gold.gold_customer_360`
  - *Expected behavior*: All three agents group `gold_customer_360` by `customer_segment` and return customer counts and `SUM(total_relationship_value)`.

- **Tier 2 (`2 Omnichannel Revenue`)**
  > Across our active VIP loyalty tiers, how does Customer Lifetime Value (CLV) and e-commerce order volume compare against active BNPL balances and average Return-Risk Score by primary store region?
  - *Tables*: `retail_silver.silver_vip_members`, `retail_silver.silver_customers`, `retail_silver.silver_stores`, `retail_silver.silver_ecom_orders`, `retail_silver.silver_bnpl_plans`
  - *Glossary*: `[Retail] Customer Lifetime Value (CLV)`, `[Retail] Loyalty & Return-Risk Score`, `[Retail] Store Identifier`
  - *Expected behavior*: Basic fails (lacks VIP member, store region, e-commerce order, and customer-level BNPL tables). Scaled must disambiguate Bronze vs Silver vs Gold tables across 4 domains (VIP loyalty, stores, e-commerce, and BNPL) and map business terms (`Customer Lifetime Value (CLV)` → `net_worth_estimate` / `total_relationship_value`, `Return-Risk Score` → `return_risk_score_at_signup` / `return_risk_score`, `primary store region` → `silver_customers.primary_store_id = silver_stores.store_id`) without glossary context. KC uses glossary terms and catalog entries to resolve the join path cleanly.

- **Tier 3 (`3 Customer Lineage`)**
  > Where does our customer and loyalty data originate, how does it flow from source systems to gold_customer_360, and who is the data steward?
  - *Tables*: `retail_bronze.bronze_customers`, `retail_silver.silver_customers`, `retail_silver.silver_loyalty_accounts`, `retail_gold.gold_customer_360`
  - *Source Systems*: `ORION` (Core Retail ERP), `LUMEN` (Omnichannel CRM & Loyalty), `HELIOS` (Payment & Risk)
  - *Expected behavior*: Basic and Scaled have no lineage or aspect access. KC traces lineage from `ORION` / `LUMEN` / `HELIOS` through Bronze and Silver to `gold_customer_360` and cites the data steward from `retail-governance`.

- **Tier 4 (`4 Consent & Return Abuse`)**
  > Identify VIP or high-risk customers whose return and promo activity flags abuse risk, showing only their marketing consent verification status and high-value refunds.
  - *Tables*: `retail_gold.gold_promo_fraud_scoring`, `retail_gold.gold_return_fraud_analytics`, `retail_silver.silver_privacy_consents`, `retail_silver.silver_high_value_refunds`
  - *Glossary*: `[Retail] Return Abuse Alert`, `[Retail] Marketing Consent & Verification`
  - *Expected behavior*: Only KC discovers `gold_promo_fraud_scoring` via `[Retail] Return Abuse Alert` and `[Retail] Marketing Consent & Verification`, respects PII/consent governance, and joins high-value refund activity.

---

## 3. PRIVACY & COMPLIANCE
*Personas: Privacy & Compliance Officer*

- **Tier 1 (`1 BNPL Risk Tiers`)**
  > Give me a breakdown of our BNPL plans by plan type, risk rating, and average Return-Risk score.
  - *Tables*: `retail_gold.gold_bnpl_plan_summary`
  - *Glossary*: `[Retail] Return-Risk Score`
  - *Expected behavior*: All three agents query `gold_bnpl_plan_summary` and return plan counts, total outstanding, and `avg_return_risk_score` by `plan_type` and `risk_rating`.

- **Tier 2 (`2 Vintage Delinquency`)**
  > Are BNPL delinquencies trending up or down across origination vintages, and which segments have the highest 90+ day delinquency rate?
  - *Tables*: `retail_gold.gold_bnpl_delinquency_analysis`, `retail_gold.gold_bnpl_plan_summary`, `retail_snapshots.snapshot_bnpl_vintage`
  - *Glossary*: `[Retail] BNPL Delinquency Rate`
  - *Expected behavior*: Basic fails (`gold_bnpl_plan_summary` has no vintage column). Scaled gets confused across `gold_bnpl_plan_summary`, `silver_bnpl_plans`, and `snapshot_bnpl_vintage`. KC uses `[Retail] BNPL Delinquency Rate` to query `gold_bnpl_delinquency_analysis` by `vintage` and `segment`.

- **Tier 3 (`3 PCI & PII Scope`)**
  > Which tables contain PCI-DSS payment card data or CCPA-regulated PII in Knowledge Catalog, and what are their data classification and access control levels?
  - *Tables*: `retail_silver.silver_store_cards`, `retail_silver.silver_customers`, `retail_silver.silver_privacy_consents`, `retail_gold.gold_compliance_dashboard`
  - *Expected behavior*: Basic and Scaled cannot read catalog aspects. KC inspects `retail-data-classification`, `retail-access-control`, and `retail-regulatory` aspects across payment card and customer tables.

- **Tier 4 (`4 Dashboard Lineage & Audit`)**
  > Which PCI-scoped or PII-classified columns feed our compliance and executive dashboards, what is their lineage back to the source system, and are all compliance schedules met?
  - *Tables*: `retail_gold.gold_compliance_dashboard`, `retail_dashboards.vw_compliance_summary`, `retail_dashboards.vw_executive_kpis`, `retail_silver.silver_compliance_attestations`
  - *Expected behavior*: Only KC combines catalog classification/lineage metadata with live SQL over `gold_compliance_dashboard` to report which compliance schedules are met vs at risk.

---

## 4. CROSS-CLOUD (NEXUS · Snowflake — KC Agent Only)
*Available exclusively on the KC Agent tab (disabled with explanatory tooltip on Basic & Scaled).*

- **Tier 1 (`1 NEXUS Discovery`)**
  > What external syndicated retail market intelligence tables are available in the NEXUS catalog?
  - *Catalog Entries*: `retail-nexus-market-intel` (`nexus_competitor_prices`, `nexus_category_market_share`, `nexus_consumer_panel`, `nexus_regional_demand_index`, `nexus_promo_calendar_benchmark`, `nexus_basket_affinity`)

- **Tier 2 (`2 Cross-Cloud Joins`)**
  > Which NEXUS syndicated tables can I join to our Gold category and assortment performance data, and on what keys?
  - *Catalog Entries & Targets*: `nexus_category_market_share`, `nexus_competitor_prices`, `nexus_basket_affinity` → `gold_assortment_performance`, `gold_gross_margin_analysis`, `gold_category_manager_scorecard`

- **Tier 3 (`3 License & Residency`)**
  > What is the license classification and data residency of our NEXUS syndicated data, and who owns the external vendor agreement?
  - *Governance Aspects*: `classification_level = "Third-Party Licensed"`, `access_level = "External Vendor Agreement"`, `cloud_platform = "Snowflake"`, `data_residency = "External / Non-GCP"`, `owner = "Sarah Jenkins, VP of Merchandising Analytics & Enterprise Data Procurement"`

- **Tier 4 (`4 Margin & Price Benchmarks`)**
  > How do our margins on top-selling categories compare to syndicated market benchmarks, and which of our SKUs are priced above competitors?
  - *C1 (Catalog-only)*: Queries BigQuery `gold_assortment_performance`, `gold_gross_margin_analysis`, and `silver_product_skus`, identifies `nexus_category_market_share` and `nexus_competitor_prices` plus join keys from Knowledge Catalog, and explicitly notes that live Snowflake cross-cloud query execution is not connected in C1 without fabricating numbers.
  - *C2 (Live Snowflake)*: Executes `query_snowflake` and combines Snowflake benchmark rows with BigQuery actuals.
