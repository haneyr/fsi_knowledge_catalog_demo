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

module "medallion" {
  source       = "../../modules/bigquery-medallion"
  project_id   = var.project_id
  multi_region = var.multi_region
}

module "reference" {
  source       = "../../modules/bigquery-reference"
  project_id   = var.project_id
  multi_region = var.multi_region
}

module "dashboards" {
  source       = "../../modules/bigquery-dashboards"
  project_id   = var.project_id
  multi_region = var.multi_region
  depends_on   = [module.medallion]
}

output "bronze_dataset" { value = module.medallion.bronze_dataset_id }
output "silver_dataset" { value = module.medallion.silver_dataset_id }
output "gold_dataset" { value = module.medallion.gold_dataset_id }
