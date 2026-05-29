#!/bin/bash
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

####################################################################################
# FSI Knowledge Catalog Demo - Deploy (Terraform, ENVIRONMENT-selected: dev|prod)
# Requires Terraform and Terragrunt. For deployment without Terraform,
# use deploy-full.sh instead (recommended).
####################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "=== FSI Knowledge Catalog Demo - Deploy ==="

# Select environment (dev|prod). Defaults to dev for local/manual runs.
export ENVIRONMENT="${ENVIRONMENT:-dev}"
TFVARS="${SCRIPT_DIR}/env/${ENVIRONMENT}.tfvars"
if [ ! -f "${TFVARS}" ]; then
  echo "ERROR: ${TFVARS} not found. Valid ENVIRONMENT values: dev, prod."
  exit 1
fi
PROJECT_ID=$(grep -E '^[[:space:]]*project_id' "${TFVARS}" | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
if [ -z "${PROJECT_ID}" ]; then
  echo "ERROR: project_id is empty in ${TFVARS}. Fill it in before deploying."
  exit 1
fi
echo "=== ENVIRONMENT=${ENVIRONMENT} -> project ${PROJECT_ID} ==="

# Ensure the Terraform state bucket and secrets exist (required by remote_state).
GOOGLE_CLOUD_PROJECT="${PROJECT_ID}" bash "${SCRIPT_DIR}/bootstrap.sh"

# Terragrunt deploy all stacks
cd stacks
for stack in 01-foundation 02-networking 03-bigquery 04-dataplex-infra; do
  echo "--- Deploying ${stack} ---"
  cd "${stack}"
  terragrunt init
  terragrunt apply -auto-approve
  cd ..
done
cd ..

# Export Terraform outputs to scripts/config.json
cd stacks/01-foundation
terragrunt output -json > "${SCRIPT_DIR}/scripts/config.json"
cd "${SCRIPT_DIR}"

# Run post-deploy scripts
source post_deploy.sh

echo "=== Deploy Complete ==="
