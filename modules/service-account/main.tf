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
variable "project_number" { type = string }

resource "google_service_account" "fsi_governance" {
  project      = var.project_id
  account_id   = "fsi-governance"
  display_name = "FSI Knowledge Catalog Demo Service Account"
}

locals {
  governance_sa_roles = [
    "roles/bigquery.admin",
    "roles/dataplex.admin",
    "roles/datalineage.admin",
    "roles/aiplatform.user",
    "roles/iam.serviceAccountUser",
  ]

  agent_engine_sa       = "serviceAccount:service-${var.project_number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
  agent_engine_sa_roles = [
    "roles/bigquery.jobUser",
    "roles/bigquery.dataViewer",
    "roles/bigquery.dataEditor",
    "roles/dataplex.viewer",
    "roles/dataplex.catalogEditor",
    "roles/datalineage.viewer",
  ]

  compute_sa       = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
  compute_sa_roles = [
    "roles/aiplatform.user",
    "roles/dataplex.viewer",
    "roles/dataplex.catalogEditor",
  ]
}

resource "google_project_iam_member" "sa_roles" {
  for_each = toset(local.governance_sa_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.fsi_governance.email}"
}

resource "google_project_iam_member" "agent_engine_roles" {
  for_each = toset(local.agent_engine_sa_roles)
  project  = var.project_id
  role     = each.value
  member   = local.agent_engine_sa
}

resource "google_project_iam_member" "compute_sa_roles" {
  for_each = toset(local.compute_sa_roles)
  project  = var.project_id
  role     = each.value
  member   = local.compute_sa
}

output "email" {
  value = google_service_account.fsi_governance.email
}
