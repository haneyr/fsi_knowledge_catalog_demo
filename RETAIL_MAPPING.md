# Northwind Retail Knowledge Catalog Demo — Domain Mapping (`RETAIL_MAPPING.md`)

This document is the canonical reference mapping every artifact, dataset, source system, data product, governance aspect, DQ rule template, persona, and table from the original **FSI (Meridian National Bank)** demo to the **Retail (Northwind Retail Group)** demo.

---

## 1. Brand & Source Systems (14 / 13 / 13 Split Preserved)

| Dimension | Original FSI (Banking) | Refactored Retail | Platform & Ingestion | Bronze / Silver Tables |
|---|---|---|---|---|
| **Enterprise Brand** | Meridian National Bank | **Northwind Retail Group** | Omnichannel specialty retail (~1,200 stores + e-commerce, North America) | 128 total tables |
| **Source System 1** | `ATLAS` (Core Retail Banking) | **`ORION`** (Store Operations & POS) | NCR POS on IBM i · IBM CDC | **14** bronze + **14** silver |
| **Source System 2** | `FORTUNA` (Wealth Management) | **`LUMEN`** (Digital Commerce & Loyalty) | Salesforce Commerce Cloud · Commerce Export API | **13** bronze + **13** silver |
| **Source System 3** | `ARGUS` (Finance & Risk) | **`HELIOS`** (Merchandising, Supply Chain & Finance) | SAP S/4HANA Retail · SAP SLT | **13** bronze + **13** silver |

---

## 2. BigQuery Datasets & Labels

Every BigQuery dataset is created in the `us` multi-region with `[Retail] ` prefixed descriptions and four mandatory labels:
`use-case=retail`, `demo=retail-knowledge-catalog`, `owner=alitch`, `env=demo`.

| Old Dataset | New Dataset | Shadow (`_nokc`) Dataset | Purpose |
|---|---|---|---|
| `fsi_bronze` | `retail_bronze` | `retail_bronze_nokc` | Raw ingestion layer (ORION + LUMEN + HELIOS, 40 tables) |
| `fsi_silver` | `retail_silver` | `retail_silver_nokc` | Cleansed and conformed layer (40 tables) |
| `fsi_gold` | `retail_gold` | `retail_gold_nokc` | Business analytics layer (20 tables) |
| `fsi_reference` | `retail_reference` | `retail_reference_nokc` | Reference & lookup tables (10 tables) |
| `fsi_dashboards` | `retail_dashboards` | `retail_dashboards_nokc` | Pre-aggregated Looker Studio & DQ views (8 views) |
| `fsi_staging` | `retail_staging` | `retail_staging_nokc` | Compliance & omnichannel filing staging (5 tables) |
| `fsi_snapshots` | `retail_snapshots` | `retail_snapshots_nokc` | Historical loyalty, inventory & pricing snapshots (3 tables) |
| `fsi_audit` | `retail_audit` | `retail_audit_nokc` | Data access audit trail & model decision logs (2 tables) |
| `fsi_scan_results` | `retail_scan_results` | *(N/A)* | Dataplex Data Quality & Data Profile scan results |
| `agent_analytics` | `retail_agent_analytics` | *(N/A)* | ADK BigQuery Agent Analytics event plugin log |

---

## 3. Data Products (5), Personas (5), Aspect Types (7), & Rule Templates (10)

### 3.1 Data Products (`us` multi-region)
| Old Data Product | New Data Product ID | Display Name | Assets |
|---|---|---|---|
| Customer 360 (`customer-360`) | `retail-customer-loyalty-360` | `[Retail] Customer & Loyalty 360` | 7 tables |
| Lending & Credit Risk (`lending-credit-risk`) | `retail-pricing-promo-margin` | `[Retail] Pricing, Promotion & Margin` | 6 tables |
| Wealth Management (`wealth-management`) | `retail-merchandising-inventory` | `[Retail] Merchandising & Inventory` | 6 tables |
| Regulatory Compliance (`regulatory-compliance`) | `retail-privacy-consent-pci` | `[Retail] Privacy, Consent & PCI Compliance` | 5 tables |
| Financial Performance (`financial-performance`) | `retail-store-channel-performance` | `[Retail] Store & Channel Performance` | 6 tables |

### 3.2 Personas (5 Personas / 24 Simulated Queries)
| Old Persona | New Persona | Focus Area |
|---|---|---|
| Risk Analyst | **Merchandising Manager** | Assortment performance, SKU margin, markdown risk, inventory allocation |
| Branch Manager | **Store Operations Director** | Store P&L, POS & kiosk transactions, BNPL plan activity, store associates |
| Wealth Advisor | **Loyalty/CRM Marketer** | Customer 360, VIP members, loyalty tiers, reward redemptions, CLV |
| Financial Controller | **Supply Chain Planner** | Inventory positions, turnover coverage, suppliers, working capital, GL |
| Compliance Officer | **Privacy & Compliance Officer** | PCI-DSS, CCPA/CPRA consent, return/promo fraud scoring, audit logs |

### 3.3 Aspect Types (7 — `global` location, `[Retail] ` display names)
| Aspect ID | Display Name | Retail Enum Values |
|---|---|---|
| `data-classification` | `[Retail] Data Classification` | `PII`, `Payment Card Data`, `Supplier-Confidential`, `Marketing Consent`, `Public`, `Internal`, `Confidential`, `Restricted` |
| `regulatory-scope` | `[Retail] Regulatory & Compliance Scope` | `PCI-DSS`, `CCPA/CPRA`, `GDPR`, `SOX`, `FTC_ACT`, `SUPPLY_CHAIN_ACT` |
| `source-lineage` | `[Retail] Source System & Medallion Lineage` | `ORION`, `LUMEN`, `HELIOS`, `DERIVED`, `REFERENCE` |
| `data-stewardship` | `[Retail] Data Stewardship & Retention` | `7_YEARS_FINANCIAL`, `5_YEARS_LOYALTY`, `3_YEARS_MARKETING`, `1_YEAR_OPERATIONAL`, `PERMANENT` |
| `freshness-sla` | `[Retail] Freshness SLA` | `REAL_TIME`, `NEAR_REAL_TIME`, `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY` |
| `risk-materiality` | `[Retail] Risk & Margin Materiality` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `NONE` |
| `pii-inventory` | `[Retail] PII & Consent Inventory` | `SSN_TAX_ID`, `FINANCIAL_ACCOUNT`, `PAYMENT_CARD`, `NAME_DOB`, `CONTACT_INFO`, `LOYALTY_ID`, `BIOMETRIC`, `NONE` |

### 3.4 Data Quality Rule Templates (10 — `global` location)
| Old Rule ID | New Rule ID | Display Name |
|---|---|---|
| `dq-rule-cusip-format` | `retail-dq-rule-gtin-checksum` | `[Retail] DQ Rule: GTIN-13 Format & Checksum Validation` |
| `dq-rule-isin-format` | `retail-dq-rule-sku-format` | `[Retail] DQ Rule: SKU Format Regex Validation` |
| `dq-rule-ssn-masking` | `retail-dq-rule-pii-masking` | `[Retail] DQ Rule: Email & Phone PII Masking Compliance` |
| `dq-rule-fico-range` | `retail-dq-rule-return-risk-range` | `[Retail] DQ Rule: Loyalty Tier & Return-Risk Score Range (300-850)` |
| `dq-rule-non-negative-balance` | `retail-dq-rule-non-negative-qty-order-total` | `[Retail] DQ Rule: Non-Negative On-Hand Qty & Order Total Integrity` |
| `dq-rule-date-ordering` | `retail-dq-rule-order-ship-delivery-dates` | `[Retail] DQ Rule: Chronological Order/Ship/Delivery Date Ordering` |
| `dq-rule-fk-customer-id` | `retail-dq-rule-fk-customer-id` | `[Retail] DQ Rule: Customer ID Foreign Key Validation` |
| `dq-rule-currency-code` | `retail-dq-rule-tender-type-enum` | `[Retail] DQ Rule: Tender Type & ISO Currency Enumeration` |
| `dq-rule-interest-rate-bounds` | `retail-dq-rule-negative-margin-guard` | `[Retail] DQ Rule: Negative-Margin & Markdown Rate Guard` |
| `dq-rule-pk-uniqueness` | `retail-dq-rule-duplicate-loyalty-id` | `[Retail] DQ Rule: Duplicate Loyalty-ID & Primary Key Uniqueness` |

---

## 4. Complete 128-Table Mapping

### 4.1 ORION — Store Operations & POS (14 Bronze + 14 Silver = 28 Tables)
| Old Bronze / Silver | New Bronze | New Silver |
|---|---|---|
| `bronze_customers` / `silver_customers` | `bronze_customers` | `silver_customers` |
| `bronze_accounts` / `silver_accounts` | `bronze_loyalty_accounts` | `silver_loyalty_accounts` |
| `bronze_transactions` / `silver_transactions` | `bronze_pos_transactions` | `silver_pos_transactions` |
| `bronze_loans` / `silver_loans` | `bronze_bnpl_plans` | `silver_bnpl_plans` |
| `bronze_loan_payments` / `silver_loan_payments` | `bronze_bnpl_payments` | `silver_bnpl_payments` |
| `bronze_credit_cards` / `silver_credit_cards` | `bronze_store_cards` | `silver_store_cards` |
| `bronze_card_transactions` / `silver_card_transactions` | `bronze_payment_tenders` | `silver_payment_tenders` |
| `bronze_fraud_alerts` / `silver_fraud_alerts` | `bronze_fraud_alerts` | `silver_fraud_alerts` |
| `bronze_kyc_records` / `silver_kyc_records` | `bronze_privacy_consents` | `silver_privacy_consents` |
| `bronze_branches` / `silver_branches` | `bronze_stores` | `silver_stores` |
| `bronze_employees` / `silver_employees` | `bronze_store_associates` | `silver_store_associates` |
| `bronze_wire_transfers` / `silver_wire_transfers` | `bronze_high_value_refunds` | `silver_high_value_refunds` |
| `bronze_ach_transfers` / `silver_ach_transfers` | `bronze_vendor_settlements` | `silver_vendor_settlements` |
| `bronze_atm_transactions` / `silver_atm_transactions` | `bronze_kiosk_transactions` | `silver_kiosk_transactions` |

### 4.2 LUMEN — Digital Commerce & Loyalty (13 Bronze + 13 Silver = 26 Tables)
| Old Bronze / Silver | New Bronze | New Silver |
|---|---|---|
| `bronze_wm_clients` / `silver_wm_clients` | `bronze_vip_members` | `silver_vip_members` |
| `bronze_portfolios` / `silver_portfolios` | `bronze_merch_assortments` | `silver_merch_assortments` |
| `bronze_holdings` / `silver_holdings` | `bronze_inventory_positions` | `silver_inventory_positions` |
| `bronze_trades` / `silver_trades` | `bronze_ecom_orders` | `silver_ecom_orders` |
| `bronze_securities` / `silver_securities` | `bronze_product_skus` | `silver_product_skus` |
| `bronze_advisors` / `silver_advisors` | `bronze_category_managers` | `silver_category_managers` |
| `bronze_performance` / `silver_performance` | `bronze_assortment_performance` | `silver_assortment_performance` |
| `bronze_fee_schedules` / `silver_fee_schedules` | `bronze_promo_rules` | `silver_promo_rules` |
| `bronze_benchmarks` / `silver_benchmarks` | `bronze_category_benchmarks` | `silver_category_benchmarks` |
| `bronze_client_goals` / `silver_client_goals` | `bronze_customer_preferences` | `silver_customer_preferences` |
| `bronze_risk_profiles` / `silver_risk_profiles` | `bronze_return_risk_profiles` | `silver_return_risk_profiles` |
| `bronze_distributions` / `silver_distributions` | `bronze_reward_redemptions` | `silver_reward_redemptions` |
| `bronze_custodian_feeds` / `silver_custodian_feeds` | `bronze_carrier_feeds` | `silver_carrier_feeds` |

### 4.3 HELIOS — Merchandising, Supply Chain & Finance (13 Bronze + 13 Silver = 26 Tables)
| Old Bronze / Silver | New Bronze | New Silver |
|---|---|---|
| `bronze_gl_entries` / `silver_gl_entries` | `bronze_gl_entries` | `silver_gl_entries` |
| `bronze_gl_accounts` / `silver_gl_accounts` | `bronze_gl_accounts` | `silver_gl_accounts` |
| `bronze_cost_centers` / `silver_cost_centers` | `bronze_cost_centers` | `silver_cost_centers` |
| `bronze_regulatory_capital` / `silver_regulatory_capital` | `bronze_working_capital` | `silver_working_capital` |
| `bronze_risk_exposures` / `silver_risk_exposures` | `bronze_shrinkage_exposures` | `silver_shrinkage_exposures` |
| `bronze_counterparties` / `silver_counterparties` | `bronze_suppliers` | `silver_suppliers` |
| `bronze_market_data` / `silver_market_data` | `bronze_competitor_pricing` | `silver_competitor_pricing` |
| `bronze_stress_tests` / `silver_stress_tests` | `bronze_demand_scenarios` | `silver_demand_scenarios` |
| `bronze_audit_events` / `silver_audit_events` | `bronze_audit_events` | `silver_audit_events` |
| `bronze_regulatory_filings` / `silver_regulatory_filings` | `bronze_compliance_attestations` | `silver_compliance_attestations` |
| `bronze_interest_rates` / `silver_interest_rates` | `bronze_markdown_rates` | `silver_markdown_rates` |
| `bronze_fx_rates` / `silver_fx_rates` | `bronze_fx_rates` | `silver_fx_rates` |
| `bronze_compliance_cases` / `silver_compliance_cases` | `bronze_promo_abuse_cases` | `silver_promo_abuse_cases` |

### 4.4 Gold Layer (20 Tables)
| Old Gold Table | New Gold Table |
|---|---|
| `gold_customer_360` | `gold_customer_360` |
| `gold_account_summary` | `gold_loyalty_account_summary` |
| `gold_transaction_patterns` | `gold_order_patterns` |
| `gold_loan_portfolio` | `gold_bnpl_plan_summary` |
| `gold_delinquency_analysis` | `gold_bnpl_delinquency_analysis` |
| `gold_fraud_analytics` | `gold_return_fraud_analytics` |
| `gold_aml_risk_scoring` | `gold_promo_fraud_scoring` |
| `gold_branch_performance` | `gold_store_performance` |
| `gold_portfolio_performance` | `gold_assortment_performance` |
| `gold_wm_client_revenue` | `gold_vip_member_revenue` |
| `gold_asset_allocation` | `gold_inventory_allocation` |
| `gold_advisor_scorecard` | `gold_category_manager_scorecard` |
| `gold_fee_revenue_analysis` | `gold_promo_margin_impact` |
| `gold_net_interest_margin` | `gold_gross_margin_analysis` |
| `gold_capital_adequacy` | `gold_working_capital_adequacy` |
| `gold_liquidity_coverage` | `gold_inventory_turnover_coverage` |
| `gold_market_risk_var` | `gold_markdown_risk_var` |
| `gold_operational_risk` | `gold_shrinkage_operational_risk` |
| `gold_compliance_dashboard` | `gold_compliance_dashboard` |
| `gold_balance_sheet` | `gold_financial_summary` |

### 4.5 Reference (10), Views (8), Staging (5), Snapshots (3), & Audit (2)
| Category | Old Name | New Name |
|---|---|---|
| **Reference** | `ref_mcc_codes` | `ref_merch_category_codes` |
| **Reference** | `ref_country_codes` | `ref_country_codes` |
| **Reference** | `ref_currency_codes` | `ref_currency_codes` |
| **Reference** | `ref_cusip_directory` | `ref_gtin_master` |
| **Reference** | `ref_isin_mapping` | `ref_sku_gtin_mapping` |
| **Reference** | `ref_institution_registry` | `ref_supplier_registry` |
| **Reference** | `ref_fips_codes` | `ref_sales_region_codes` |
| **Reference** | `ref_product_catalog` | `ref_product_catalog` |
| **Reference** | `ref_fee_tiers` | `ref_loyalty_tiers` |
| **Reference** | `ref_gl_account_hierarchy` | `ref_gl_account_hierarchy` |
| **Views** | `vw_dq_scorecard` | `vw_dq_scorecard` |
| **Views** | `vw_dq_by_dimension` | `vw_dq_by_dimension` |
| **Views** | `vw_dq_failed_rules` | `vw_dq_failed_rules` |
| **Views** | `vw_dq_rule_detail` | `vw_dq_rule_detail` |
| **Views** | `vw_profile_summary` | `vw_profile_summary` |
| **Views** | `vw_customer_relationship_summary` | `vw_customer_lifetime_value` |
| **Views** | `vw_branch_wealth_combined` | `vw_store_omnichannel_performance` |
| **Views** | `vw_regulatory_summary` | `vw_compliance_summary` |
| **Staging** | `staging_call_report_rc` | `staging_pci_aoc_summary` |
| **Staging** | `staging_call_report_ri` | `staging_channel_revenue_recon` |
| **Staging** | `staging_fr_y9c` | `staging_supplier_audit_schedule` |
| **Staging** | `staging_sar_batch` | `staging_ccpa_dsar_log` |
| **Staging** | `staging_10k_data` | `staging_annual_omniretail_filing` |
| **Snapshots** | `snapshot_monthly_balances` | `snapshot_monthly_loyalty_balances` |
| **Snapshots** | `snapshot_quarterly_holdings` | `snapshot_quarterly_inventory_positions` |
| **Snapshots** | `snapshot_daily_rates` | `snapshot_daily_competitor_pricing` |
| **Audit** | `audit_data_access_log` | `audit_data_access_log` |
| **Audit** | `audit_model_decisions` | `audit_model_decisions` |

---

## 5. Agents & Cloud Run Service

| Resource | Old Name | New Name | Display Name |
|---|---|---|---|
| **Basic Agent** | `fsi_basic_agent` | `retail-agent-basic` (`retail_basic_agent`) | `[Retail] retail-agent-basic` |
| **Scaled Agent** | `fsi_scaled_agent` | `retail-agent-scaled` (`retail_scaled_agent`) | `[Retail] retail-agent-scaled` |
| **KC Agent** | `fsi_kc_agent` | `retail-agent-kc` (`retail_kc_agent`) | `[Retail] retail-agent-kc` |
| **Cloud Run UI** | `fsi-kc-demo-ui-live` | `retail-kc-demo-ui-live` | `[Retail] Northwind Retail KC Demo UI` |
| **Policy Taxonomy** | `FSI Demo Sensitivity Taxonomy` | `RETAIL_TAXONOMY_DISPLAY_NAME` | `Retail Demo Sensitivity Taxonomy (alitch)` |
