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

variable "project_id" { type = string }
variable "multi_region" {
  type    = string
  default = "us"
}

locals {
  dashboard_views = [
    "vw_dq_scorecard", "vw_dq_by_dimension", "vw_dq_failed_rules",
    "vw_dq_rule_detail", "vw_profile_summary",
    "vw_customer_total_relationship", "vw_branch_retail_wealth",
    "vw_regulatory_summary",
  ]
}

resource "google_bigquery_dataset" "dashboards" {
  project     = var.project_id
  dataset_id  = "fsi_dashboards"
  location    = var.multi_region
  description = "Pre-aggregated views for Looker Studio dashboards"
}

resource "google_bigquery_job" "dashboards" {
  for_each = toset(local.dashboard_views)
  project  = var.project_id
  job_id   = "create-${replace(each.key, "_", "-")}-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  location = var.multi_region

  query {
    query              = templatefile("${path.module}/sql/${each.key}.sql", { project_id = var.project_id })
    use_legacy_sql     = false
    create_disposition = "CREATE_IF_NEEDED"
    write_disposition  = "WRITE_TRUNCATE"
  }

  depends_on = [google_bigquery_dataset.dashboards]
  lifecycle { ignore_changes = [job_id] }
}
