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
# Bootstrap a target GCP project for the Terraform path and/or Cloud Build CI.
# Idempotent: safe to re-run. Creates the Terraform state bucket and the agent-id
# Secret Manager secrets. Does NOT create the project itself.
#
# Usage:
#   export GOOGLE_CLOUD_PROJECT=fsi-kc-demo-dev
#   bash bootstrap.sh
####################################################################################

set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT before running bootstrap.sh}"
STATE_LOCATION="${BOOTSTRAP_STATE_LOCATION:-us}"
BUCKET="${PROJECT}-tfstate"

echo "=== Bootstrapping ${PROJECT} ==="

# 1. Enable required APIs (superset of deploy-full.sh, plus storage + secretmanager)
echo "--- Enabling APIs ---"
gcloud services enable \
    bigquery.googleapis.com \
    dataplex.googleapis.com \
    datalineage.googleapis.com \
    datacatalog.googleapis.com \
    aiplatform.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    cloudaicompanion.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com \
    --project="${PROJECT}"

# 2. Terraform state bucket (idempotent)
echo "--- Terraform state bucket ---"
if gcloud storage buckets describe "gs://${BUCKET}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "  gs://${BUCKET} already exists"
else
    gcloud storage buckets create "gs://${BUCKET}" \
        --project="${PROJECT}" \
        --location="${STATE_LOCATION}" \
        --uniform-bucket-level-access
    echo "  created gs://${BUCKET}"
fi
# Enforce versioning unconditionally (covers buckets created outside this script).
gcloud storage buckets update "gs://${BUCKET}" --versioning --project="${PROJECT}"

# 3. Agent-id secrets (idempotent placeholders)
echo "--- Agent-id secrets ---"
for secret in basic-agent-id scaled-agent-id kc-agent-id; do
    if gcloud secrets describe "${secret}" --project="${PROJECT}" >/dev/null 2>&1; then
        echo "  secret ${secret} already exists"
    else
        gcloud secrets create "${secret}" \
            --project="${PROJECT}" \
            --replication-policy=automatic
        echo "  created secret ${secret}"
    fi
done

echo "=== Bootstrap complete for ${PROJECT} ==="
