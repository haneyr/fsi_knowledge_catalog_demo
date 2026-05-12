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
  reference_tables = [
    "ref_naics_codes", "ref_country_codes", "ref_currency_codes",
    "ref_cusip_master", "ref_isin_mapping", "ref_lei_registry",
    "ref_fed_district_codes", "ref_product_catalog", "ref_fee_tiers",
    "ref_gl_account_hierarchy",
  ]
}

resource "google_bigquery_dataset" "reference" {
  project     = var.project_id
  dataset_id  = "fsi_reference"
  location    = var.multi_region
  description = "Reference and lookup tables for FSI data validation"
}

resource "google_bigquery_job" "reference" {
  for_each = toset(local.reference_tables)
  project  = var.project_id
  job_id   = "create-${replace(each.key, "_", "-")}-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  location = var.multi_region

  query {
    query              = templatefile("${path.module}/sql/${each.key}.sql", { project_id = var.project_id })
    use_legacy_sql     = false
    create_disposition = "CREATE_IF_NEEDED"
    write_disposition  = "WRITE_TRUNCATE"
  }

  depends_on = [google_bigquery_dataset.reference]
  lifecycle { ignore_changes = [job_id] }
}
