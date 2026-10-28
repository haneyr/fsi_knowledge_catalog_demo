# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

variable "project_id" {
  type        = string
  description = "GCP project ID for BigQuery resources."
}

variable "multi_region" {
  type        = string
  default     = "us"
  description = "BigQuery multi-region location."
}

locals {
  # ORION (Store Ops & POS) — 14 tables
  orion_bronze = [
    "bronze_customers", "bronze_loyalty_accounts", "bronze_pos_transactions",
    "bronze_bnpl_plans", "bronze_bnpl_payments", "bronze_store_cards",
    "bronze_payment_tenders", "bronze_fraud_alerts", "bronze_privacy_consents",
    "bronze_stores", "bronze_store_associates", "bronze_high_value_refunds",
    "bronze_vendor_settlements", "bronze_kiosk_transactions",
  ]

  # LUMEN (Digital Commerce & Loyalty) — 13 tables
  lumen_bronze = [
    "bronze_vip_members", "bronze_merch_assortments", "bronze_inventory_positions",
    "bronze_ecom_orders", "bronze_product_skus", "bronze_category_managers",
    "bronze_assortment_performance", "bronze_promo_rules", "bronze_category_benchmarks",
    "bronze_customer_preferences", "bronze_return_risk_profiles", "bronze_reward_redemptions",
    "bronze_carrier_feeds",
  ]

  # HELIOS (Merchandising, Supply Chain & Finance) — 13 tables
  helios_bronze = [
    "bronze_gl_entries", "bronze_gl_accounts", "bronze_cost_centers",
    "bronze_working_capital", "bronze_shrinkage_exposures", "bronze_suppliers",
    "bronze_competitor_pricing", "bronze_demand_scenarios", "bronze_audit_events",
    "bronze_compliance_attestations", "bronze_markdown_rates", "bronze_fx_rates",
    "bronze_promo_abuse_cases",
  ]

  bronze_tables = concat(local.orion_bronze, local.lumen_bronze, local.helios_bronze)

  silver_tables = [for t in local.bronze_tables : replace(t, "bronze_", "silver_")]

  gold_tables = [
    "gold_customer_360", "gold_loyalty_account_summary", "gold_order_patterns",
    "gold_bnpl_plan_summary", "gold_bnpl_delinquency_analysis",
    "gold_return_fraud_analytics", "gold_promo_fraud_scoring", "gold_store_performance",
    "gold_assortment_performance", "gold_vip_member_revenue", "gold_inventory_allocation",
    "gold_category_manager_scorecard", "gold_promo_margin_impact", "gold_gross_margin_analysis",
    "gold_working_capital_adequacy", "gold_inventory_turnover_coverage", "gold_markdown_risk_var",
    "gold_shrinkage_operational_risk", "gold_compliance_dashboard", "gold_financial_summary",
  ]

  # Additional datasets for supplementary tables
  staging_tables = [
    "staging_pci_aoc_summary", "staging_channel_revenue_recon",
    "staging_supplier_audit_schedule", "staging_ccpa_dsar_log", "staging_annual_omniretail_filing",
  ]

  snapshot_tables = [
    "snapshot_monthly_loyalty_balances", "snapshot_quarterly_inventory_positions",
    "snapshot_daily_competitor_pricing",
  ]

  audit_tables = [
    "audit_data_access_log", "audit_model_decisions",
  ]
}

# ============================================================
# Datasets
# ============================================================
resource "google_bigquery_dataset" "bronze" {
  project     = var.project_id
  dataset_id  = "retail_bronze"
  location    = var.multi_region
  description = "[Retail] Northwind Retail Group — raw ingestion layer (ORION + LUMEN + HELIOS)"
  labels = {
    use-case = "retail"
    demo     = "retail-knowledge-catalog"
    owner    = "alitch"
    env      = "demo"
  }
}

resource "google_bigquery_dataset" "silver" {
  project     = var.project_id
  dataset_id  = "retail_silver"
  location    = var.multi_region
  description = "[Retail] Northwind Retail Group — cleansed and conformed layer"
  labels = {
    use-case = "retail"
    demo     = "retail-knowledge-catalog"
    owner    = "alitch"
    env      = "demo"
  }
}

resource "google_bigquery_dataset" "gold" {
  project     = var.project_id
  dataset_id  = "retail_gold"
  location    = var.multi_region
  description = "[Retail] Northwind Retail Group — business analytics layer"
  labels = {
    use-case = "retail"
    demo     = "retail-knowledge-catalog"
    owner    = "alitch"
    env      = "demo"
  }
}

resource "google_bigquery_dataset" "scan_results" {
  project     = var.project_id
  dataset_id  = "retail_scan_results"
  location    = var.multi_region
  description = "[Retail] Data quality and profile scan results for Retail tables"
  labels = {
    use-case = "retail"
    demo     = "retail-knowledge-catalog"
    owner    = "alitch"
    env      = "demo"
  }
}

resource "google_bigquery_dataset" "staging" {
  project     = var.project_id
  dataset_id  = "retail_staging"
  location    = var.multi_region
  description = "[Retail] Regulatory filing staging tables"
  labels = {
    use-case = "retail"
    demo     = "retail-knowledge-catalog"
    owner    = "alitch"
    env      = "demo"
  }
}

resource "google_bigquery_dataset" "snapshots" {
  project     = var.project_id
  dataset_id  = "retail_snapshots"
  location    = var.multi_region
  description = "[Retail] Historical snapshot tables"
  labels = {
    use-case = "retail"
    demo     = "retail-knowledge-catalog"
    owner    = "alitch"
    env      = "demo"
  }
}

resource "google_bigquery_dataset" "audit" {
  project     = var.project_id
  dataset_id  = "retail_audit"
  location    = var.multi_region
  description = "[Retail] Audit trail and model decision logs"
  labels = {
    use-case = "retail"
    demo     = "retail-knowledge-catalog"
    owner    = "alitch"
    env      = "demo"
  }
}

# ============================================================
# Bronze tables
# ============================================================
resource "google_bigquery_job" "bronze" {
  for_each = toset(local.bronze_tables)
  project  = var.project_id
  job_id   = "create-${replace(each.key, "_", "-")}-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  location = var.multi_region

  query {
    query              = templatefile("${path.module}/sql/${each.key}.sql", { project_id = var.project_id })
    use_legacy_sql     = false
    create_disposition = "CREATE_IF_NEEDED"
    write_disposition  = "WRITE_TRUNCATE"
  }

  depends_on = [google_bigquery_dataset.bronze]
  lifecycle { ignore_changes = [job_id] }
}

# ============================================================
# Silver tables (depend on bronze)
# ============================================================
resource "google_bigquery_job" "silver" {
  for_each = toset(local.silver_tables)
  project  = var.project_id
  job_id   = "create-${replace(each.key, "_", "-")}-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  location = var.multi_region

  query {
    query              = templatefile("${path.module}/sql/${each.key}.sql", { project_id = var.project_id })
    use_legacy_sql     = false
    create_disposition = "CREATE_IF_NEEDED"
    write_disposition  = "WRITE_TRUNCATE"
  }

  depends_on = [google_bigquery_dataset.silver, google_bigquery_job.bronze]
  lifecycle { ignore_changes = [job_id] }
}

# ============================================================
# Gold tables (depend on silver)
# ============================================================
resource "google_bigquery_job" "gold" {
  for_each = toset(local.gold_tables)
  project  = var.project_id
  job_id   = "create-${replace(each.key, "_", "-")}-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  location = var.multi_region

  query {
    query              = templatefile("${path.module}/sql/${each.key}.sql", { project_id = var.project_id })
    use_legacy_sql     = false
    create_disposition = "CREATE_IF_NEEDED"
    write_disposition  = "WRITE_TRUNCATE"
  }

  depends_on = [google_bigquery_dataset.gold, google_bigquery_job.silver]
  lifecycle { ignore_changes = [job_id] }
}

# ============================================================
# Staging tables
# ============================================================
resource "google_bigquery_job" "staging" {
  for_each = toset(local.staging_tables)
  project  = var.project_id
  job_id   = "create-${replace(each.key, "_", "-")}-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  location = var.multi_region

  query {
    query              = templatefile("${path.module}/sql/${each.key}.sql", { project_id = var.project_id })
    use_legacy_sql     = false
    create_disposition = "CREATE_IF_NEEDED"
    write_disposition  = "WRITE_TRUNCATE"
  }

  depends_on = [google_bigquery_dataset.staging, google_bigquery_job.silver]
  lifecycle { ignore_changes = [job_id] }
}

# ============================================================
# Snapshot tables
# ============================================================
resource "google_bigquery_job" "snapshots" {
  for_each = toset(local.snapshot_tables)
  project  = var.project_id
  job_id   = "create-${replace(each.key, "_", "-")}-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  location = var.multi_region

  query {
    query              = templatefile("${path.module}/sql/${each.key}.sql", { project_id = var.project_id })
    use_legacy_sql     = false
    create_disposition = "CREATE_IF_NEEDED"
    write_disposition  = "WRITE_TRUNCATE"
  }

  depends_on = [google_bigquery_dataset.snapshots, google_bigquery_job.silver]
  lifecycle { ignore_changes = [job_id] }
}

# ============================================================
# Audit tables
# ============================================================
resource "google_bigquery_job" "audit" {
  for_each = toset(local.audit_tables)
  project  = var.project_id
  job_id   = "create-${replace(each.key, "_", "-")}-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  location = var.multi_region

  query {
    query              = templatefile("${path.module}/sql/${each.key}.sql", { project_id = var.project_id })
    use_legacy_sql     = false
    create_disposition = "CREATE_IF_NEEDED"
    write_disposition  = "WRITE_TRUNCATE"
  }

  depends_on = [google_bigquery_dataset.audit]
  lifecycle { ignore_changes = [job_id] }
}

# ============================================================
# Outputs
# ============================================================
output "bronze_dataset_id" { value = google_bigquery_dataset.bronze.dataset_id }
output "silver_dataset_id" { value = google_bigquery_dataset.silver.dataset_id }
output "gold_dataset_id" { value = google_bigquery_dataset.gold.dataset_id }
output "scan_results_dataset_id" { value = google_bigquery_dataset.scan_results.dataset_id }
