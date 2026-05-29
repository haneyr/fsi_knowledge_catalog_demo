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
# Deploy to an existing project via Terraform. The dev/prod project is selected by
# the ENVIRONMENT variable (default: dev) and read from env/<ENVIRONMENT>.tfvars.
# This is now a thin wrapper around deploy.sh.
####################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export ENVIRONMENT="${ENVIRONMENT:-dev}"
echo "=== Deploy (existing project) — ENVIRONMENT=${ENVIRONMENT} ==="
exec bash "${SCRIPT_DIR}/deploy.sh"
