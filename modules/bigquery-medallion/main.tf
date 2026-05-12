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
  # ATLAS (Retail Banking) — 14 tables
  atlas_bronze = [
    "bronze_customers", "bronze_accounts", "bronze_transactions",
    "bronze_loans", "bronze_loan_payments", "bronze_credit_cards",
    "bronze_card_transactions", "bronze_fraud_alerts", "bronze_kyc_records",
    "bronze_branches", "bronze_employees", "bronze_wire_transfers",
    "bronze_ach_transfers", "bronze_atm_transactions",
  ]

  # FORTUNA (Wealth Management) — 13 tables
  fortuna_bronze = [
    "bronze_wm_clients", "bronze_portfolios", "bronze_holdings",
    "bronze_trades", "bronze_securities", "bronze_advisors",
    "bronze_performance", "bronze_fee_schedules", "bronze_benchmarks",
    "bronze_client_goals", "bronze_risk_profiles", "bronze_distributions",
    "bronze_custodian_feeds",
  ]

  # ARGUS (Finance & Risk) — 13 tables
  argus_bronze = [
    "bronze_gl_entries", "bronze_gl_accounts", "bronze_cost_centers",
    "bronze_regulatory_capital", "bronze_risk_exposures", "bronze_counterparties",
    "bronze_market_data", "bronze_stress_tests", "bronze_audit_events",
    "bronze_regulatory_filings", "bronze_interest_rates", "bronze_fx_rates",
    "bronze_compliance_cases",
  ]

  bronze_tables = concat(local.atlas_bronze, local.fortuna_bronze, local.argus_bronze)

  silver_tables = [for t in local.bronze_tables : replace(t, "bronze_", "silver_")]

  gold_tables = [
    "gold_customer_360", "gold_account_summary", "gold_transaction_patterns",
    "gold_loan_portfolio_summary", "gold_delinquency_analysis",
    "gold_fraud_analytics", "gold_aml_risk_scoring", "gold_branch_performance",
    "gold_portfolio_performance", "gold_client_revenue", "gold_asset_allocation",
    "gold_advisor_scorecard", "gold_fee_revenue", "gold_net_interest_margin",
    "gold_capital_adequacy", "gold_liquidity_coverage", "gold_market_risk_var",
    "gold_operational_risk", "gold_regulatory_dashboard", "gold_balance_sheet_summary",
  ]

  # Additional datasets for supplementary tables
  staging_tables = [
    "staging_call_report_rc", "staging_call_report_ri",
    "staging_call_report_rc_r", "staging_call_report_rc_c", "staging_fr_y9c",
  ]

  snapshot_tables = [
    "snapshot_monthly_balances", "snapshot_quarterly_positions",
    "snapshot_daily_market_data",
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
  dataset_id  = "fsi_bronze"
  location    = var.multi_region
  description = "Meridian National Bank — raw ingestion layer (ATLAS + FORTUNA + ARGUS)"
}

resource "google_bigquery_dataset" "silver" {
  project     = var.project_id
  dataset_id  = "fsi_silver"
  location    = var.multi_region
  description = "Meridian National Bank — cleansed and conformed layer"
}

resource "google_bigquery_dataset" "gold" {
  project     = var.project_id
  dataset_id  = "fsi_gold"
  location    = var.multi_region
  description = "Meridian National Bank — business analytics layer"
}

resource "google_bigquery_dataset" "scan_results" {
  project     = var.project_id
  dataset_id  = "fsi_scan_results"
  location    = var.multi_region
  description = "Data quality and profile scan results for FSI tables"
}

resource "google_bigquery_dataset" "staging" {
  project     = var.project_id
  dataset_id  = "fsi_staging"
  location    = var.multi_region
  description = "Regulatory filing staging tables"
}

resource "google_bigquery_dataset" "snapshots" {
  project     = var.project_id
  dataset_id  = "fsi_snapshots"
  location    = var.multi_region
  description = "Historical snapshot tables"
}

resource "google_bigquery_dataset" "audit" {
  project     = var.project_id
  dataset_id  = "fsi_audit"
  location    = var.multi_region
  description = "Audit trail and model decision logs"
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
