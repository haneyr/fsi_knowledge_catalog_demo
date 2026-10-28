# PHASE E — Data Semantics Audit (`PHASE_E_DATA_AUDIT.md`)

> **Status**: **AUDIT ONLY — NO DATA OR SQL FILES MODIFIED**  
> **Date**: 2026-10-21  
> **Scope**: Audit of all SQL generation files under [`modules/bigquery-medallion/sql/`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql), [`modules/bigquery-reference/sql/`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-reference/sql), and [`modules/bigquery-dashboards/sql/`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-dashboards/sql) where financial-services (FSI / banking / wealth / AML / Basel III) semantics survived in **literal string values**, **numeric distributions**, or **uncorrelated random generators**.

---

## (a) Complete Inventory of Surviving FSI Semantics in SQL Values & Distributions

### 1. BNPL Plans, Payments & Delinquency (Originally Commercial / Mortgage Loans)
| SQL File | Table | Column(s) | Surviving FSI Values / Numeric Distribution | Why It Breaks Retail Realism |
| :--- | :--- | :--- | :--- | :--- |
| [`bronze_bnpl_plans.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_bnpl_plans.sql) | `retail_bronze.bronze_bnpl_plans` | `plan_type` | `'EXTENDED_FINANCING'`, `'AUTO'`, `'PERSONAL'`, `'HELOC'`, `'COMMERCIAL'`, `'SBA'` | Bank loan products instead of retail BNPL installment plans |
| [`bronze_bnpl_plans.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_bnpl_plans.sql) | `retail_bronze.bronze_bnpl_plans` | `risk_rating` | `'Pass'`, `'Special Mention'`, `'Substandard'`, `'Doubtful'` | OCC regulatory bank loan classifications |
| [`bronze_bnpl_plans.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_bnpl_plans.sql) | `retail_bronze.bronze_bnpl_plans` | `original_amount`, `current_balance` | `ROUND(5000 + RAND() * 5000000, 2)` ($5K–$5.005M, avg ~$449K in Gold) | Commercial real-estate / mortgage scale, resulting in $2.87B across 6,375 BNPL plans |
| [`bronze_bnpl_plans.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_bnpl_plans.sql) | `retail_bronze.bronze_bnpl_plans` | `return_risk_score_at_signup` | `CAST(300 + FLOOR(RAND() * 550) AS INT64)` (300–850, avg ~575) | FICO credit score distribution (300–850) uncorrelated with `risk_rating` |
| [`bronze_bnpl_plans.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_bnpl_plans.sql) | `retail_bronze.bronze_bnpl_plans` | `term_months`, `rate_type`, `collateral_description`, `ltv_ratio`, `dti_ratio` | `[36,60,84,120,180,240,360]`, `'ARM'`, `'Property Ln'`, LTV `50–100%`, DTI `15–55%` | 30-year adjustable-rate mortgages with property collateral |
| [`silver_bnpl_plans.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_bnpl_plans.sql) | `retail_silver.silver_bnpl_plans` | Pass-through columns | Propagates `plan_type`, `risk_rating`, `$5K–$5M` balances, and `300–850` score | Feeds all Gold BNPL tables |
| [`gold_bnpl_plan_summary.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_bnpl_plan_summary.sql) | `retail_gold.gold_bnpl_plan_summary` | `plan_type`, `risk_rating`, `total_current_balance`, `avg_return_risk_score` | Exposes OCC `Pass`/`Special Mention`/`Substandard`/`Doubtful`, ~575 FICO score, ~$449K avg plan | Directly visible in Tier 1 Privacy & Compliance agent answers |
| [`gold_bnpl_delinquency_analysis.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_bnpl_delinquency_analysis.sql) | `retail_gold.gold_bnpl_delinquency_analysis` | `WHERE l.risk_rating IN ('Substandard', 'Doubtful')` | Hardcoded filter on OCC loan classifications | Will return 0 rows if `risk_rating` values are updated without updating this filter |
| [`bronze_bnpl_payments.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_bnpl_payments.sql), [`silver_bnpl_payments.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_bnpl_payments.sql) | `bronze_bnpl_payments`, `silver_bnpl_payments` | `scheduled_amount`, `actual_amount`, `principal_amount`, `interest_amount`, `escrow_amount` | `ROUND(200 + RAND() * 15000, 2)` ($200–$15,200 monthly payment with `escrow_amount`) | Mortgage P&I + escrow payments instead of $15–$400 BNPL installments |
| [`snapshot_bnpl_vintage.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/snapshot_bnpl_vintage.sql) | `retail_snapshots.snapshot_bnpl_vintage` | `total_originated_amount`, `current_outstanding`, `avg_ltv` | `ROUND(10000000 + RAND() * 500000000, 2)` ($10M–$510M per vintage), `avg_ltv` (`55–85%`) | Mortgage origination pool balances and loan-to-value ratios |

### 2. Privacy Consents, Promo Abuse & Fraud Scoring (Originally AML / KYC / BSA / OFAC)
| SQL File | Table | Column(s) | Surviving FSI Values / Numeric Distribution | Why It Breaks Retail Realism |
| :--- | :--- | :--- | :--- | :--- |
| [`bronze_privacy_consents.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_privacy_consents.sql) | `retail_bronze.bronze_privacy_consents` | `kyc_id`, `due_diligence_level`, `id_document_type`, `pep_flag`, `sanctions_flag`, `adverse_media_flag`, `beneficial_owner_id`, `risk_score` | `'CDD'`, `'EDD'`, `'SDD'`; `'Passport'`, `'Military ID'`; `pep_flag` (2%), `sanctions_flag` (0.5%), `adverse_media_flag` (3%); `risk_score = FLOOR(RAND()*100)` uncorrelated with `risk_score_category` | Bank Customer Due Diligence / Politically Exposed Persons / OFAC sanctions screening; `risk_score` averages ~48–49 in every tier |
| [`silver_privacy_consents.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_privacy_consents.sql) | `retail_silver.silver_privacy_consents` | `review_overdue` | `DATE_ADD('2025-01-01', INTERVAL FLOOR(RAND()*700) DAY) < CURRENT_DATE()` | Produces ~93.9% `review_overdue` uniformly across High, Medium, and Low tiers |
| [`gold_promo_fraud_scoring.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_promo_fraud_scoring.sql) | `retail_gold.gold_promo_fraud_scoring` | `pep_count`, `sanctions_hit_count`, `adverse_media_count`, `sar_filings`, `large_wire_volume`, `composite_promo_fraud_score` | Aggregates PEP flags, sanctions hits, adverse media, SAR filings, and wire volume | Surface-level table name is retail promo fraud, but columns/values are bank AML/BSA metrics |
| [`gold_compliance_dashboard.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_compliance_dashboard.sql) | `retail_gold.gold_compliance_dashboard` | `overdue_rate_pct`, `avg_risk_score`, `pep_count`, `sanctions_hits`, `adverse_media_hits` | `overdue_rate_pct ≈ 93.9%` and `avg_risk_score ≈ 48–49` across all tiers; reports PEP/sanctions/adverse media | No signal across risk tiers; AML terminology in compliance dashboard |
| [`bronze_fraud_alerts.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_fraud_alerts.sql), [`silver_fraud_alerts.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_fraud_alerts.sql), [`gold_fraud_summary.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_fraud_summary.sql) | `bronze/silver_fraud_alerts`, `gold_fraud_summary` | `alert_type`, `sar_filed`, `sar_count` | `'Structuring Detected'`, `'Account Takeover'`, `'Unusual Location'`; `sar_filed` (Suspicious Activity Report) | FinCEN BSA structuring & SAR filings instead of retail return/promo/tender fraud |
| [`bronze_promo_abuse_cases.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_promo_abuse_cases.sql), [`silver_promo_abuse_cases.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_promo_abuse_cases.sql) | `bronze/silver_promo_abuse_cases` | `case_type`, `sar_filed`, `sar_filing_id` | `'Sanctioned Vendor Screening Match'`, `'Reg E Dispute'`, `'Fair Lending Review'`; `'SAR-...'` | Bank regulatory investigation types |
| [`bronze_high_value_refunds.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_high_value_refunds.sql), [`silver_high_value_refunds.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_high_value_refunds.sql) | `bronze/silver_high_value_refunds` | `wire_id`, `beneficiary_routing`, `beneficiary_account`, `ofac_screened`, `amount` | `'WIRE-...'`, `'Beneficiary N'`, `ofac_screened`, `ROUND(500 + RAND() * 100000, 2)` ($500–$100.5K) | Wire transfer schema and $50K average wire amounts instead of retail refunds ($50–$1,500) |

### 3. Customers, VIP Members, Loyalty Accounts & Store Cards (Originally Banking / Wealth Management)
| SQL File | Table | Column(s) | Surviving FSI Values / Numeric Distribution | Why It Breaks Retail Realism |
| :--- | :--- | :--- | :--- | :--- |
| [`bronze_customers.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_customers.sql), [`silver_customers.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_customers.sql) | `bronze/silver_customers` | `kyc_risk_rating`, `kyc_status`, `annual_income` | `kyc_risk_rating` (`'Low'`, `'Medium'`, `'High'`), `kyc_status` (`'Verified'`, `'Pending'`, `'Expired'`, `'Suspended'`) | KYC banking onboarding terminology |
| [`bronze_vip_members.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_vip_members.sql), [`silver_vip_members.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_vip_members.sql) | `bronze/silver_vip_members` | `last_name`, `total_aum`, `liquid_net_worth`, `risk_tolerance`, `investment_objective`, `account_type`, `accredited_investor`, `qualified_purchaser`, `fee_schedule` | `'Rockefeller'`, `'Morgan'`, `'Vanderbilt'`, `'Lehman'`, `'Goldman'`; `total_aum` `$250K–$100.25M`; `'Capital Preservation'`, `'Tax Efficient'`; `'Trust'`, `'Entity'`, `'Joint JTWROS'`; `'AUM Tiered'` | Private wealth management / SEC Regulation D investor concepts |
| [`bronze_loyalty_accounts.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_loyalty_accounts.sql), [`silver_loyalty_accounts.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_loyalty_accounts.sql) | `bronze/silver_loyalty_accounts` | `current_balance`, `available_balance`, `interest_rate`, `routing_number`, `joint_account` | `ROUND(500 + RAND() * 1000000, 2)` ($500–$1M deposit balance), `interest_rate` (`0–5%`), `routing_number = '021000021'` | Checking/savings account balances and ABA routing numbers (`gold_customer_360` sums `current_balance` into `total_deposits` = ~$1.67B per segment) |
| [`bronze_store_cards.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_store_cards.sql), [`silver_store_cards.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_store_cards.sql) | `bronze/silver_store_cards` | `return_risk_score`, `credit_limit`, `current_balance` | `CAST(300 + FLOOR(RAND() * 550) AS INT64)` (300–850 FICO); `credit_limit` up to `$50,000` | FICO credit score distribution and high-limit bank credit cards |
| [`gold_customer_360.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_customer_360.sql) | `retail_gold.gold_customer_360` | `kyc_risk_rating`, `kyc_status`, `total_deposits`, `total_bnpl_exposure`, `total_relationship_value` | Sums `$500–$1M` loyalty balances + `$5K–$5M` BNPL balances into multi-billion-dollar segment totals | Surface values in Tier 1 Customer & Loyalty queries are ~$1.75B per 3,300 customers (~$525K/customer) |

### 4. Merchandising, Assortments, Inventory & Product SKUs (Originally Securities / Investment Portfolios)
| SQL File | Table | Column(s) | Surviving FSI Values / Numeric Distribution | Why It Breaks Retail Realism |
| :--- | :--- | :--- | :--- | :--- |
| [`bronze_product_skus.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_product_skus.sql), [`silver_product_skus.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_product_skus.sql) | `bronze/silver_product_skus` | `security_id`, `ticker`, `security_name`, `asset_class`, `sector`, `exchange`, `coupon_rate`, `maturity_date`, `credit_rating` | `'SEC-...'`, `'Security N'`, `'NYSE'`, `'NASDAQ'`, `'OTC'`, `'TREASURY'`, `'MUNI'`; `'Financial Services'`, `'Utilities'`; `'AAA'`..`'BB'` | Bond/equity security master table instead of retail SKU catalog |
| [`bronze_inventory_positions.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_inventory_positions.sql), [`silver_inventory_positions.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_inventory_positions.sql), [`gold_inventory_var_summary.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_inventory_var_summary.sql) | `bronze/silver_inventory_positions`, `gold_inventory_var_summary` | `portfolio_id`, `security_id`, `asset_class`, `market_value`, `cost_basis`, `unrealized_gain_loss` | `'PORT-...'`, `'US Large Cap Equity'`, `'US Small Cap Equity'`, `'International Equity'`, `'Alternatives'`, `'Cash & Equivalents'`; `$1K–$50M` positions | Institutional equity/bond portfolio holdings; Tier 2 Merchandising queries return `'US Large Cap Equity'` as a "product category" |
| [`bronze_merch_assortments.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_merch_assortments.sql), [`silver_merch_assortments.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_merch_assortments.sql), [`gold_assortment_performance.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_assortment_performance.sql) | `bronze/silver_merch_assortments`, `gold_assortment_performance` | `portfolio_id`, `assortment_name`, `account_type`, `strategy`, `benchmark`, `tax_status`, `market_value` | `'PORT-...'`, `'Assortment Tax-Managed'`, `'Assortment ESG Impact'`, `'ROTH_IRA'`, `'401K'`, `'TRUST'`, `'UGMA'`, `'SEP_IRA'`, `'S&P 500'`, `'Tax-Deferred'` | Retirement/wealth portfolios (`PORT-00007637`) returned in Tier 1 Merchandising queries |
| [`bronze_assortment_performance.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_assortment_performance.sql), [`silver_assortment_performance.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_assortment_performance.sql) | `bronze/silver_assortment_performance` | `portfolio_id`, `benchmark_return_pct`, `alpha`, `beta`, `sharpe_ratio`, `net_flows` | CAPM portfolio metrics (`alpha`, `beta`, `sharpe_ratio`, `PORT-...`) | Hedge-fund/wealth performance metrics instead of retail gross margin / sell-through / GMROI |
| [`bronze_competitor_pricing.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_competitor_pricing.sql), [`silver_competitor_pricing.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_competitor_pricing.sql) | `bronze/silver_competitor_pricing` | `security_id`, `bid_price`, `ask_price`, `pe_ratio`, `dividend_yield`, `market_cap` | `'SEC-...'`, bid/ask spread, P/E ratio, dividend yield, `$100M–$2T` market cap | Stock market OHLCV quote feed instead of competitor retail shelf/online prices |
| [`bronze_category_benchmarks.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_category_benchmarks.sql), [`silver_category_benchmarks.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_category_benchmarks.sql) | `bronze/silver_category_benchmarks` | `index_name`, `index_ticker`, `pe_ratio`, `dividend_yield` | `'S&P 500'`, `'Dow Jones Industrial Average'`, `'NASDAQ Composite'`, `'Russell 2000'`, `'Bloomberg US Aggregate Bond'`, `'MSCI EAFE'` | Equity/bond market indices instead of retail category benchmarks |
| [`bronze_markdown_rates.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_markdown_rates.sql), [`silver_markdown_rates.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_markdown_rates.sql) | `bronze/silver_markdown_rates` | `curve_name`, `tenor`, `rate_pct` | `'Treasury'`, `'SOFR'`, `'Fed Funds'`, `'Prime'`, `'Corporate AAA'`, `'Corporate BBB'`, `'Municipal'`; tenors `'1M'`..`'30Y'` | Yield curves / interest rates instead of seasonal retail markdown curves |
| [`bronze_supplier_orders.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_supplier_orders.sql), [`silver_supplier_orders.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_supplier_orders.sql), [`gold_order_execution_quality.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_order_execution_quality.sql) | `bronze/silver_supplier_orders`, `gold_order_execution_quality` | `trade_id`, `security_id`, `execution_venue`, `commission`, `order_type` | `'TRD-...'`, `'SEC-...'`, `'Limit'`, `'Stop'`, `'Stop-Limit'` | Institutional equity trade execution instead of purchase order fulfillment |

### 5. Finance, Working Capital, Associates & Reference Tables (Originally Basel III / Call Report / FINRA)
| SQL File | Table | Column(s) | Surviving FSI Values / Numeric Distribution | Why It Breaks Retail Realism |
| :--- | :--- | :--- | :--- | :--- |
| [`bronze_working_capital.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_working_capital.sql), [`silver_working_capital.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_working_capital.sql), [`gold_working_capital_adequacy.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_working_capital_adequacy.sql) | `bronze/silver_working_capital`, `gold_working_capital_adequacy` | `capital_tier`, `risk_weighted_assets`, `capital_ratio_pct`, `minimum_required_pct`, `methodology` | `'CET1'`, `'Tier 1'`, `'Total Capital'`, `'Tier 2'`; `'Standardized'`, `'Advanced IRB'` | Basel III regulatory bank capital adequacy |
| [`gold_financial_summary.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/gold_financial_summary.sql) | `retail_gold.gold_financial_summary` | `line_item` | `'Cash and Due From Retailers'`, `'Other Borrowed Funds'`, `'Total Equity Capital'` | FFIEC bank Call Report balance sheet lines (`'Cash and Due From Banks'` sed-replaced to `'Cash and Due From Retailers'`) |
| [`bronze_category_managers.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_category_managers.sql), [`silver_category_managers.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_category_managers.sql) | `bronze/silver_category_managers` | `finra_crd`, `licenses`, `book_of_business_aum`, `fee_revenue_ytd` | `'Series 7, 66'`, `'Series 7, 65, CFP'`, `'Series 7, 66, CFA'`; `$10M–$500M` AUM | Registered Investment Advisors (RIAs) with FINRA Series licenses |
| [`bronze_store_associates.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_store_associates.sql), [`silver_store_associates.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_store_associates.sql) | `bronze/silver_store_associates` | `nmls_id` | `'NMLS-...'` (Nationwide Multistate Licensing System ID) | Mortgage loan officer licensing |
| [`bronze_compliance_attestations.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/bronze_compliance_attestations.sql), [`silver_compliance_attestations.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-medallion/sql/silver_compliance_attestations.sql) | `bronze/silver_compliance_attestations` | `regulatory_body`, `report_name`, `filing_status` | `'OCC'`, `'FRB'`, `'CFPB'`, `'FINRA'`, `'SEC'`, `'FFIEC'`; `'Call Report'`, `'SAR Batch'`, `'CRA Filing'`, `'HMDA LAR'` | Bank regulatory filings instead of PCI-DSS, CCPA, CPRA, FTC, SOC2 retail compliance |
| [`ref_product_catalog.sql`](file:///home/aelitchfield/knowledge_catalog_demo/modules/bigquery-reference/sql/ref_product_catalog.sql) | `retail_reference.ref_product_catalog` | `product_name` | `'Individual Retirement Account'`, `'Home Equity Line of Credit'`, `'Roth IRA'`, `'401(k) Plan'`, `'Trust Account'`, `'Custodial Account (UGMA)'` | Bank/brokerage product catalog |

---

## (b) Proposed Retail Replacements

### 1. BNPL Plans (`bronze_bnpl_plans.sql` → `silver_bnpl_plans.sql` → `gold_bnpl_plan_summary.sql` & `gold_bnpl_delinquency_analysis.sql`)
- **`plan_type`**: Replace `'EXTENDED_FINANCING'`, `'AUTO'`, `'PERSONAL'`, `'HELOC'`, `'COMMERCIAL'`, `'SBA'` with:
  - `'PAY_IN_4'`, `'MONTHLY_3M'`, `'MONTHLY_6M'`, `'SEASONAL_PROMO_12M'`, `'APPLIANCE_FINANCING_18M'`, `'VIP_FLEX_PAY'`
- **`risk_rating`**: Replace `'Pass'`, `'Special Mention'`, `'Substandard'`, `'Doubtful'` with:
  - `'Low'`, `'Watch'`, `'Elevated'`, `'High Risk'` (and update `gold_bnpl_delinquency_analysis.sql` `WHERE l.risk_rating IN ('Elevated', 'High Risk')`)
- **`return_risk_score_at_signup`**: Replace uncorrelated `300–850` FICO range with a **`0–100` retail return-risk score correlated with `risk_rating`**:
  - `'Low'` → `8 + FLOOR(RAND() * 20)` (`8–27`, avg ~17.5)
  - `'Watch'` → `30 + FLOOR(RAND() * 22)` (`30–51`, avg ~40.5)
  - `'Elevated'` → `55 + FLOOR(RAND() * 20)` (`55–74`, avg ~64.5)
  - `'High Risk'` → `75 + FLOOR(RAND() * 24)` (`75–98`, avg ~86.5)
- **`original_amount` & `current_balance`**: Replace `$5,000–$5,005,000` with retail order sizes (`$50–$2,500`, skewed toward `$120–$450` so average plan balance is **~$280**, not ~$449K).
- **`bronze_bnpl_payments.sql` & `snapshot_bnpl_vintage.sql`**: Scale installment payments to `$15–$400` and vintage pools to `$150K–$2.5M`.

### 2. Privacy Consents, Compliance Dashboard & Promo Fraud (`bronze_privacy_consents.sql` → `silver_privacy_consents.sql` → `gold_compliance_dashboard.sql` & `gold_promo_fraud_scoring.sql`)
- **`due_diligence_level`**: Replace `'CDD'`, `'EDD'`, `'SDD'` with `'STANDARD_OPT_IN'`, `'ENHANCED_PRIVACY_REVIEW'`, `'EXPRESS_CHECKOUT_CONSENT'`.
- **`id_document_type`**: Replace `'Passport'`, `'Military ID'` with `'Email Verification'`, `'SMS OTP'`, `'Loyalty App Biometric'`, `'Store ID Check'`.
- **`risk_score` (0–100) correlated with `risk_score_category`**:
  - `'Low'` → `5 + FLOOR(RAND() * 22)` (avg ~16)
  - `'Medium'` → `32 + FLOOR(RAND() * 25)` (avg ~44)
  - `'High'` → `68 + FLOOR(RAND() * 30)` (avg ~83)
- **`review_overdue` / `overdue_rate_pct`**: Fix `next_review_date` generation so `review_overdue` is **single-digit and correlated with `risk_score_category`**:
  - `'Low'` → ~`1.8%` overdue
  - `'Medium'` → ~`4.7%` overdue
  - `'High'` → ~`11.4%` overdue
- **Flags (`pep_flag` / `sanctions_flag` / `adverse_media_flag`)**:
  - *If keeping column names (Option 1 — Low Blast Radius)*: adjust rates and document in column descriptions, or alias in Gold views.
  - *If renaming columns (Option 2 — Full Cleanse)*: rename to `serial_returner_flag`, `promo_abuse_flag`, `chargeback_history_flag` in Bronze/Silver and `serial_returner_count`, `promo_abuse_hit_count`, `chargeback_history_count`, `confirmed_abuse_filings`, `high_value_refund_volume` in `gold_promo_fraud_scoring.sql` & `gold_compliance_dashboard.sql`.

### 3. Assortments, Inventory Positions & Product SKUs (`bronze_merch_assortments.sql`, `bronze_inventory_positions.sql`, `bronze_product_skus.sql`)
- **`portfolio_id` / `assortment_name` / `account_type`**:
  - Replace `'PORT-0000...'` with `'ASRT-0000...'`
  - Replace `'Assortment Growth'`, `'Assortment Tax-Managed'`, `'Assortment ESG Impact'` with `'Spring Apparel Core'`, `'Outdoor & Activewear'`, `'Home & Kitchen Essentials'`, `'Consumer Electronics Flagship'`, `'Beauty & Personal Care'`, `'Seasonal Holiday Gifting'`, `'Footwear & Accessories'`, `'Private Label Basics'`
  - Replace `'ROTH_IRA'`, `'401K'`, `'TRUST'`, `'UGMA'`, `'SEP_IRA'` with `'FLAGSHIP_STORE'`, `'OMNICHANNEL'`, `'ECOMMERCE_ONLY'`, `'OUTLET'`, `'MARKETPLACE'`, `'POP_UP'`
- **`asset_class` (in `bronze_inventory_positions.sql` and `bronze_product_skus.sql`)**:
  - Replace `'US Large Cap Equity'`, `'US Small Cap Equity'`, `'International Equity'`, `'Emerging Markets'`, `'Alternatives'`, `'Cash & Equivalents'` with retail product categories: `'Apparel & Outerwear'`, `'Footwear'`, `'Home & Kitchen'`, `'Consumer Electronics'`, `'Beauty & Personal Care'`, `'Sporting Goods'`, `'Accessories & Jewelry'`, `'Seasonal & Promotional'`
- **`security_id` / `security_name` / `exchange`**:
  - Replace `'SEC-...'` with `'SKU-...'`, `'Security N'` with retail item names, and `'NYSE'`/`'NASDAQ'`/`'TREASURY'` with `'DIRECT_BRAND'`, `'WHOLESALE_DIST'`, `'PRIVATE_LABEL'`, `'DROPSHIP'`, `'EXCLUSIVE_COLLAB'`.

### 4. Loyalty Balances, VIP Members & Financial Summary
- **`bronze_loyalty_accounts.sql`**: Scale `current_balance` / `available_balance` from `$500–$1,000,000` down to realistic annual loyalty/spend balances (`$25–$4,500`, avg ~$620).
- **`bronze_vip_members.sql`**: Replace Gilded Age banker names (`Rockefeller`, `Morgan`, `Lehman`, `Goldman`) with normal customer surnames, and scale `total_aum` (`$250K–$100M`) to annual VIP retail spend (`$2,500–$25,000`).
- **`gold_financial_summary.sql`**: Replace `'Cash and Due From Retailers'` with `'Cash & Store Working Balances'`, `'Other Borrowed Funds'` with `'Supply Chain & Trade Payables'`, and `'Total Equity Capital'` with `'Total Retail Operating Equity'`.
- **`ref_product_catalog.sql`**: Replace `'Individual Retirement Account'`, `'Home Equity Line of Credit'`, `'Roth IRA'`, `'401(k) Plan'`, `'Trust Account'` with `'Northwind Rewards Visa'`, `'Pay-in-4 BNPL Plan'`, `'VIP Insider Annual Membership'`, `'Extended Product Protection Plan'`, `'Gift Card & Store Credit'`.

---

## (c) Exact File List & Estimated Blast Radius

There are **two options** depending on whether we only replace **values/distributions inside SQL SELECT/CREATE statements** (Option 1) or also **rename internal Bronze/Silver/Gold columns** like `pep_flag`, `kyc_risk_rating`, `portfolio_id`, `security_id` (Option 2).

### Option 1 (Recommended — Value & Distribution Fix Only, Zero Schema Breakage)
Changes literal strings, numeric ranges, and correlated formulas inside SQL files while **keeping existing table and column names unchanged**.
- **Files touched (34 SQL files)**:
  1. `modules/bigquery-medallion/sql/bronze_bnpl_plans.sql`
  2. `modules/bigquery-medallion/sql/gold_bnpl_delinquency_analysis.sql`
  3. `modules/bigquery-medallion/sql/bronze_bnpl_payments.sql`
  4. `modules/bigquery-medallion/sql/snapshot_bnpl_vintage.sql`
  5. `modules/bigquery-medallion/sql/bronze_privacy_consents.sql`
  6. `modules/bigquery-medallion/sql/silver_privacy_consents.sql`
  7. `modules/bigquery-medallion/sql/bronze_fraud_alerts.sql`
  8. `modules/bigquery-medallion/sql/bronze_promo_abuse_cases.sql`
  9. `modules/bigquery-medallion/sql/bronze_high_value_refunds.sql`
  10. `modules/bigquery-medallion/sql/bronze_vip_members.sql`
  11. `modules/bigquery-medallion/sql/bronze_loyalty_accounts.sql`
  12. `modules/bigquery-medallion/sql/bronze_store_cards.sql`
  13. `modules/bigquery-medallion/sql/bronze_product_skus.sql`
  14. `modules/bigquery-medallion/sql/bronze_inventory_positions.sql`
  15. `modules/bigquery-medallion/sql/bronze_merch_assortments.sql`
  16. `modules/bigquery-medallion/sql/bronze_competitor_pricing.sql`
  17. `modules/bigquery-medallion/sql/bronze_category_benchmarks.sql`
  18. `modules/bigquery-medallion/sql/bronze_markdown_rates.sql`
  19. `modules/bigquery-medallion/sql/bronze_supplier_orders.sql`
  20. `modules/bigquery-medallion/sql/bronze_working_capital.sql`
  21. `modules/bigquery-medallion/sql/gold_working_capital_adequacy.sql`
  22. `modules/bigquery-medallion/sql/gold_financial_summary.sql`
  23. `modules/bigquery-medallion/sql/bronze_category_managers.sql`
  24. `modules/bigquery-medallion/sql/bronze_store_associates.sql`
  25. `modules/bigquery-medallion/sql/bronze_compliance_attestations.sql`
  26. `modules/bigquery-reference/sql/ref_product_catalog.sql`
  - *(Plus 8 pass-through Silver/Gold views/tables automatically rebuilt from the Bronze tables when `deploy-bq.sh` runs.)*
- **Blast radius**: **LOW**. No Terraform schema changes, no Dataplex aspect/lineage breakage, no agent system-prompt changes, no Cloud Run UI changes.

### Option 2 (Full Column Rename + Value Fix)
Also renames legacy FSI column names (`pep_flag` → `serial_returner_flag`, `sanctions_flag` → `promo_abuse_flag`, `adverse_media_flag` → `chargeback_history_flag`, `kyc_risk_rating` → `privacy_risk_rating`, `portfolio_id` → `assortment_id`, `security_id` → `sku_id`, `total_aum` → `annual_vip_spend`, `sar_filed` → `abuse_report_filed`).
- **Files touched (~62 files)**:
  - All 34 SQL files above + their corresponding `silver_*.sql`, `gold_*.sql`, `staging_*.sql`, and `modules/bigquery-dashboards/sql/vw_*.sql` files
  - `scripts/04_tag_pii_columns.py`, `scripts/07_create_dq_scans.py`, `scripts/09_populate_column_descriptions.py`, `scripts/12_create_lineage.py`
  - `agents/agent_basic/agent.py` (hardcoded column schemas for the 10 Gold tables)
- **Blast radius**: **MEDIUM-HIGH**. Requires redeploying `retail-agent-basic` and re-running Dataplex column descriptions/lineage/DQ scans.

---

## (d) Required Deployment Steps to Apply Phase E

1. **If applying Option 1 (Values & Distributions Only)**:
   - **Re-run `deploy-bq.sh` AND `deploy-bq-nokc.sh`**: **YES (Required)** — `CREATE OR REPLACE TABLE` statements in `modules/bigquery-medallion/sql/` and `modules/bigquery-reference/sql/` must execute to regenerate the rows in both `retail_*` (KC) and `retail_*_nokc` (Scaled/Basic shadow) datasets. (~6–8 minutes total).
   - **Re-run DQ Scans (`scripts/07_create_dq_scans.py`)**: **YES (Trigger Run Only)** — Check `scripts/07_create_dq_scans.py` for any `IN (...)` value assertions on `risk_rating` or `plan_type`, update if present, and trigger a fresh DataScan execution so Dataplex Data Quality scores reflect the new table rows.
   - **Re-run Dataplex Metadata / Agents / Cloud Run**: **NO** — Existing table entries, aspects, glossary links, lineage, and deployed Agent Engines remain 100% valid.

2. **If applying Option 2 (Values + Column Renames)**:
   - Requires **both** `deploy-bq.sh` + `deploy-bq-nokc.sh` **AND** re-running `post_deploy.sh` (specifically `04_tag_pii_columns.py`, `07_create_dq_scans.py`, `09_populate_column_descriptions.py`) **AND** redeploying `retail-agent-basic` (`agents/deploy_agents.sh`).
