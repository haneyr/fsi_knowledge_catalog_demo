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

locals {
  env = read_terragrunt_config(
    fileexists("${get_repo_root()}/env/existing-project.tfvars")
      ? "${get_repo_root()}/env/existing-project.tfvars"
      : "${get_repo_root()}/env/new-project.tfvars"
  )
}

inputs = {
  project_id   = local.env.locals.project_id
  region       = local.env.locals.region
  multi_region = local.env.locals.multi_region
}
