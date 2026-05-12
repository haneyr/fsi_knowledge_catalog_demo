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

data "google_project" "project" {
  project_id = var.project_id
}

data "google_client_openid_userinfo" "me" {}

resource "random_string" "suffix" {
  length  = 10
  special = false
  upper   = false
}

output "project_number" {
  value = data.google_project.project.number
}

output "gcp_account_name" {
  value = data.google_client_openid_userinfo.me.email
}

output "random_suffix" {
  value = random_string.suffix.result
}
