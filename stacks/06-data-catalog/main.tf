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

variable "region" {
  type    = string
  default = "us-central1"
}

variable "multi_region" {
  type    = string
  default = "us"
}

data "google_project" "project" {
  project_id = var.project_id
}

module "taxonomy" {
  source         = "../../modules/data-catalog-taxonomy"
  project_id     = var.project_id
  multi_region   = var.multi_region
  project_number = data.google_project.project.number
}

output "taxonomy_id" {
  value = module.taxonomy.taxonomy_id
}

output "policy_tag_ids" {
  value = module.taxonomy.policy_tag_ids
}
