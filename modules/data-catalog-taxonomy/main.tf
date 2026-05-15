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

variable "project_number" { type = string }

resource "google_data_catalog_taxonomy" "fsi_classification" {
  project      = var.project_id
  region       = var.multi_region
  display_name = "FSI Data Classification"
  description  = "Data classification taxonomy for Meridian National Bank FSI demo. Defines sensitivity levels for column-level policy enforcement."

  activated_policy_types = ["FINE_GRAINED_ACCESS_CONTROL"]
}

locals {
  policy_tags = {
    highly-sensitive = {
      display_name = "Highly Sensitive PII"
      description  = "Direct identifiers: SSN/TIN, date of birth. Requires encryption at rest, column-level access control, and audit logging for every access."
    }
    sensitive = {
      display_name = "Sensitive PII"
      description  = "Personal identifiers: name, email, phone, address. Requires role-based access and masking in non-production environments."
    }
    confidential = {
      display_name = "Confidential Financial"
      description  = "Non-public financial data: FICO scores, APR, AUM, account balances, transaction amounts. Restricted to authorized personnel."
    }
    internal = {
      display_name = "Internal"
      description  = "Business operational data not for external distribution. Standard access controls apply."
    }
  }

  agent_engine_sa = "serviceAccount:service-${var.project_number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
}

resource "google_data_catalog_policy_tag" "tags" {
  for_each = local.policy_tags

  taxonomy     = google_data_catalog_taxonomy.fsi_classification.id
  display_name = each.value.display_name
  description  = each.value.description
}

resource "google_data_catalog_taxonomy_iam_member" "agent_engine_reader" {
  taxonomy = google_data_catalog_taxonomy.fsi_classification.id
  role     = "roles/datacatalog.categoryFineGrainedReader"
  member   = local.agent_engine_sa
}

output "taxonomy_id" {
  value = google_data_catalog_taxonomy.fsi_classification.id
}

output "taxonomy_name" {
  value = google_data_catalog_taxonomy.fsi_classification.name
}

output "policy_tag_ids" {
  value = { for k, v in google_data_catalog_policy_tag.tags : k => v.id }
}
