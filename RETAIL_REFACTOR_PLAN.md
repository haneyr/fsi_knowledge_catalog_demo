# Retail Domain Refactor Plan (`RETAIL_REFACTOR_PLAN.md`)

## 1. Transformation Strategy: Mechanical vs. Authored

Per **Rule 2** (never hand-edit >3 files; drive bulk transforms via [`tools/transform.py`](file:///home/aelitchfield/knowledge_catalog_demo/tools/transform.py) and [`tools/retail_mapping.json`](file:///home/aelitchfield/knowledge_catalog_demo/tools/retail_mapping.json)), we split the 238 repository files into two tracks:

### Track A — Mechanically Transformed via `tools/transform.py` (~215 files)
`tools/transform.py` will execute deterministic, longest-match-first, boundary-aware replacements and file renames across:
1. **128 SQL Files** (`modules/bigquery-{medallion,reference,dashboards}/sql/*.sql`):
   - Rename SQL filenames (e.g., `bronze_loans.sql` → `bronze_bnpl_plans.sql`, `ref_cusip_master.sql` → `ref_gtin_master.sql`) and their internal `CREATE OR REPLACE TABLE/VIEW` target names.
   - Replace dataset names (`fsi_*` → `retail_*`), FK references (`silver_loans` → `silver_bnpl_plans`), column names (`cusip` → `gtin_13`, `isin` → `sku_code`, `ssn` → `customer_phone_masked` / `tax_id_masked`, `fico_score` → `return_risk_score`, `branch_id` → `store_id`, `loan_id` → `bnpl_plan_id`, `wm_client_id` → `vip_member_id`, `portfolio_id` → `assortment_id`, `security_id` → `sku_id`, `advisor_id` → `category_manager_id`, etc.), and synthetic string literals (loan types → BNPL/payment plan types, banking segments → loyalty tiers, CUSIP/ISIN strings → GTIN-13/SKU formats) while preserving exact row counts, `MOD(n, ...)` defect patterns, and join keys (`CUST-00000001`, etc.).
2. **Terraform / Terragrunt & CI/CD Files** (`modules/*/main.tf`, `stacks/*/`, `env/*.tfvars`, `terragrunt.hcl`, `cloudbuild*.yaml`):
   - Rename resource IDs, dataset IDs, table IDs, entry/aspect types, and descriptions (`[Retail] ...`) for 100% naming parity.
3. **Shell Orchestrators** (`deploy-bq.sh`, `deploy-bq-nokc.sh`, `deploy-full.sh`, `deploy.sh`, `deploy-existing-project.sh`, `bootstrap.sh`, `post_deploy.sh`, `clean_up.sh`):
   - Swap `fsi_*` datasets to `retail_*`, inject `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` and `CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false` to prevent the `bq` CLI mTLS crash, and apply dataset labels (`use-case=retail`, `demo=retail-knowledge-catalog`, `owner=alitch`, `env=demo`) and `[Retail] ` descriptions on every dataset.
4. **Snowflake Directory** (`snowflake/*`):
   - Mechanically rename `fsi_` / `Meridian` references to `retail_` / `Northwind` while leaving code paths intact (not executed).

### Track B — Domain-Authored Content (~23 files, generated via structured Python builders or targeted edits)
1. **Business Glossary & Rich HTML Overviews** ([`scripts/01_create_glossary.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/01_create_glossary.py), [`scripts/12_enrich_glossary.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/12_enrich_glossary.py)):
   - Glossary display name: `[Retail] Northwind Retail Business Glossary` (`retail-northwind-glossary-us`).
   - 28 categories (10 L1 + 18 L2), every display name prefixed `Retail — ` and description prefixed `[Retail] `.
   - 84 retail terms (72 core terms + 12 retail abbreviations: `SKU`, `GTIN`, `POS`, `BOPIS`, `BNPL`, `GMROI`, `AOV`, `CLV`, `OTB`, `DC`, `RMA`, `DSAR`), 10 retail data stewards/contacts (`@northwindretail.example.com`), 14 synonym links, 67 related links, 181 column definition links, and 84 rich HTML overviews.
2. **Governance Pipeline Scripts** ([`scripts/common.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/common.py), `scripts/00` through `16`):
   - `00_create_dataplex_infra.py`: 9 `retail-*` entry types (`retail-ibmi-*`, `retail-sfcc-*`, `retail-sap-*`), 7 marker aspects, 7 custom aspect types (`retail-data-classification`, `retail-data-retention`, `retail-regulatory-compliance`, `retail-data-lineage-metadata`, `retail-access-control`, `retail-risk-classification`, `retail-regulatory-reporting`) with retail enum values (`PCI-DSS`, `CCPA/CPRA`, `GDPR`, `PII`, `Payment Card Data`, `Supplier-Confidential`, `Marketing Consent`), and 3 entry groups (`retail-orion-store-pos`, `retail-lumen-commerce-loyalty`, `retail-helios-merch-supply`).
   - `02_create_scans.py` & `15_inject_dirty_data.py`: Retail DQ rules & 6 dirty-data injections (invalid return-risk scores, negative loyalty balances, invalid phone/email PII formats, invalid GTIN-13/SKU formats, extreme store-card APRs, high-value refund structuring `$10,000.01`).
   - `03_create_source_entries.py` & `07_create_lineage.py`: ORION (14), LUMEN (13), HELIOS (13) source entries and 5 lineage processes (125 links).
   - `04_create_aspects.py`, `05_create_data_products.py`, `08_publish_scans.py`, `09_simulate_queries.py` (5 retail personas, 24 queries), `10_create_rule_library.py` (10 retail rule templates), `11`, `13`, `16_create_policy_tags.py` (using `RETAIL_TAXONOMY_DISPLAY_NAME="Retail Demo Sensitivity Taxonomy (alitch)"`).
3. **3 ADK Agents & Deploy Script** ([`agents/agent_basic/agent.py`](file:///home/aelitchfield/knowledge_catalog_demo/agents/agent_basic/agent.py), [`agents/agent_scaled/agent.py`](file:///home/aelitchfield/knowledge_catalog_demo/agents/agent_scaled/agent.py), [`agents/agent_kc/agent.py`](file:///home/aelitchfield/knowledge_catalog_demo/agents/agent_kc/agent.py), [`agents/deploy_agents.sh`](file:///home/aelitchfield/knowledge_catalog_demo/agents/deploy_agents.sh)):
   - Deployed as `retail-agent-basic`, `retail-agent-scaled`, `retail-agent-kc` logging to `retail_agent_analytics`.
   - **Basic Agent**: Hardcoded 5 gold `_nokc` tables (`gold_customer_360`, `gold_loyalty_account_summary`, `gold_bnpl_plan_summary`, `gold_assortment_performance`, `gold_financial_summary`).
   - **Scaled Agent**: Hardcoded all 128 `_nokc` table names with zero descriptions/schemas — reproduces table-disambiguation and cross-domain failures.
   - **KC-Guided Agent**: Uses Dataplex Knowledge Catalog discovery tools over `retail_*` governed datasets, glossary terms, DQ scores, and aspects.
4. **Demo Questions, Eval & Live Website** ([`demo/demo_questions.md`](file:///home/aelitchfield/knowledge_catalog_demo/demo/demo_questions.md), [`demo/demo_script.md`](file:///home/aelitchfield/knowledge_catalog_demo/demo/demo_script.md), [`eval/test_cases.yaml`](file:///home/aelitchfield/knowledge_catalog_demo/eval/test_cases.yaml), [`website-live/`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/)):
   - 15 retail questions across 3 tiers preserving exact failure modes:
     - **Tier 1 (Baseline — all 3 succeed)**: Customer 360 spend by loyalty tier; BNPL plan summary by return-risk rating; Assortment performance & GMROI.
     - **Tier 2 (Disambiguation & DQ Trust — Scaled fails, Basic lacks tables, KC succeeds)**: Promo/coupon abuse & high-value refund structuring (Scaled picks `gold_return_fraud_analytics` instead of `gold_promo_fraud_scoring` + `silver_promo_abuse_cases`); Return-risk score & GTIN-13 data quality trustworthiness (KC checks DQ scan pass rates and flags dirty bronze rows); Markdown rate risk vs. gross margin impact.
     - **Tier 3 (Cross-Domain Discovery & Governance — Basic & Scaled fail, KC succeeds)**: VIP member total omnichannel exposure across ORION POS + LUMEN E-Commerce + BNPL; Store omnichannel revenue combining store POS + digital BOPIS/clienteling (`vw_store_omnichannel_performance`); CCPA/PCI-DSS compliance gaps & consent verification; Peak-season supply-chain demand stress test on high-shrinkage categories; Cross-sell opportunity (high POS spenders with zero VIP digital assortment purchases).
   - `website-live/` rebranded to **Northwind Retail Group — Knowledge Catalog Demo** and deployed to Cloud Run service `retail-kc-demo-ui-live`.

---

## 2. Structural Parity & 128-Table Mapping Summary

| Tier / Category | Count | Old (`fsi_*`) | New (`retail_*`) |
|---|---:|---|---|
| **ORION Bronze/Silver** (NCR POS on IBM i, 14) | 14×2 | `customers`, `accounts`, `transactions`, `loans`, `loan_payments`, `credit_cards`, `card_transactions`, `fraud_alerts`, `kyc_records`, `branches`, `employees`, `wire_transfers`, `ach_transfers`, `atm_transactions` | `customers`, `loyalty_accounts`, `pos_transactions`, `bnpl_plans`, `bnpl_payments`, `store_cards`, `payment_tenders`, `fraud_alerts`, `privacy_consents`, `stores`, `store_associates`, `high_value_refunds`, `vendor_settlements`, `kiosk_transactions` |
| **LUMEN Bronze/Silver** (SFCC, 13) | 13×2 | `wm_clients`, `portfolios`, `holdings`, `trades`, `securities`, `advisors`, `performance`, `fee_schedules`, `benchmarks`, `client_goals`, `risk_profiles`, `distributions`, `custodian_feeds` | `vip_members`, `merch_assortments`, `inventory_positions`, `ecom_orders`, `product_skus`, `category_managers`, `assortment_performance`, `promo_rules`, `category_benchmarks`, `customer_preferences`, `return_risk_profiles`, `reward_redemptions`, `carrier_feeds` |
| **HELIOS Bronze/Silver** (SAP S/4HANA Retail, 13) | 13×2 | `gl_entries`, `gl_accounts`, `cost_centers`, `regulatory_capital`, `risk_exposures`, `counterparties`, `market_data`, `stress_tests`, `audit_events`, `regulatory_filings`, `interest_rates`, `fx_rates`, `compliance_cases` | `gl_entries`, `gl_accounts`, `cost_centers`, `working_capital`, `shrinkage_exposures`, `suppliers`, `competitor_pricing`, `demand_scenarios`, `audit_events`, `compliance_attestations`, `markdown_rates`, `fx_rates`, `promo_abuse_cases` |
| **Gold Tables** (`retail_gold`) | 20 | `gold_customer_360`, `gold_account_summary`, `gold_loan_portfolio_summary`, `gold_portfolio_performance`, `gold_balance_sheet_summary`, + 15 domain tables | `gold_customer_360`, `gold_loyalty_account_summary`, `gold_bnpl_plan_summary`, `gold_assortment_performance`, `gold_financial_summary`, + 15 retail gold tables |
| **Dashboard Views** (`retail_dashboards`) | 8 | `vw_branch_retail_wealth`, `vw_customer_total_relationship`, `vw_regulatory_summary`, + 5 DQ/profile views | `vw_store_omnichannel_performance`, `vw_customer_lifetime_value`, `vw_compliance_summary`, + 5 DQ/profile views |
| **Reference Tables** (`retail_reference`) | 10 | `ref_cusip_master`, `ref_isin_mapping`, `ref_fed_district_codes`, `ref_fee_tiers`, `ref_lei_registry`, `ref_naics_codes`, + 4 | `ref_gtin_master`, `ref_sku_gtin_mapping`, `ref_sales_region_codes`, `ref_loyalty_tiers`, `ref_supplier_registry`, `ref_merch_category_codes`, + 4 |
| **Staging Tables** (`retail_staging`) | 5 | `staging_call_report_rc{,_c,_r,_ri}`, `staging_fr_y9c` | `staging_pci_aoc_summary`, `staging_ccpa_dsar_log`, `staging_supplier_audit_schedule`, `staging_channel_revenue_recon`, `staging_annual_omniretail_filing` |
| **Snapshots & Audit** | 3 + 2 | `snapshot_daily_market_data`, `snapshot_monthly_balances`, `snapshot_quarterly_positions`, `audit_*` | `snapshot_daily_competitor_pricing`, `snapshot_monthly_loyalty_balances`, `snapshot_quarterly_inventory_positions`, `audit_*` |

---

## 3. Order of Operations (P1 → P6)

1. **P1 — Local Refactor (Zero Cloud Calls)**:
   - `git checkout -b retail-refactor`
   - Build & run `tools/transform.py --dry-run` against `tools/retail_mapping.json`; review per-file counts; run `tools/transform.py --apply`; spot-check 5 representative files.
   - Run domain content generators for `01_create_glossary.py`, `12_enrich_glossary.py`, `demo/demo_questions.md`, `website-live/static/static-responses.json`, and agent prompts.
   - Verify FK integrity across Bronze → Silver → Gold → Views.
   - Run Tier A (= 0 hits) and Tier B banking-term purge gates, `bash -n` on all `.sh`, and `python3 -m py_compile` on all `.py`.
   - Write `RETAIL_MAPPING.md` and commit locally on `retail-refactor`.
2. **P2 — GCP Pre-Flight & Gate 2**:
   - Confirm APIs, write `scripts/config.json` (`alitch-ca-demo`, `98236392654`, `us-central1`, `us`), verify org-policy status (`allowAll: true` / `enforce: false` already active), verify Agent Engine quota, and stop at **🛑 GATE 2**.
3. **P3 — Data Layer**:
   - Run `deploy-bq.sh` and `deploy-bq-nokc.sh` (backgrounded to `logs/`). Verify 10 governed datasets + 8 `_nokc` shadow datasets, required labels (`use-case=retail`, `demo=retail-knowledge-catalog`, `owner=alitch`, `env=demo`), `[Retail] ` descriptions, and 128 non-empty tables.
4. **P4 — Governance Layer**:
   - Export `RETAIL_TAXONOMY_DISPLAY_NAME="Retail Demo Sensitivity Taxonomy (alitch)"` and run `post_deploy.sh` backgrounded (`logs/post_deploy.log`), polling every ~3 min. Verify all 15 steps.
5. **P5 — Agents + Website & Gate 3**:
   - Deploy `retail-agent-basic`, `retail-agent-scaled`, `retail-agent-kc` via `agents/deploy_agents.sh`.
   - Print click-by-click OAuth Client ID instructions and stop at **🛑 GATE 3**.
   - Deploy `retail-kc-demo-ui-live` via `website-live/deploy.sh`, configure Authorized JS Origin, apply Cloud Run IAM binding, and smoke-test.
6. **P6 — Validation & Handoff**:
   - Run `tools/validate.sh`, test all 15 demo questions across all 3 agents (confirming Tier 2 breaks Scaled and Tier 3 breaks Basic & Scaled), write `DEMO_SCRIPT.md`, verify `clean_up.sh`, update `STATE.md`, and stop at **🛑 FINAL**.
