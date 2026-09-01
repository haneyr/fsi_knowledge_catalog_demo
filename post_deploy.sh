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
# FSI Knowledge Catalog Demo - Post Deploy
# Runs all Python scripts that create Knowledge Catalog and governance resources.
# Called after BigQuery tables are created (deploy-bq.sh or Terraform).
####################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/scripts" && pwd)"
cd "${SCRIPT_DIR}"

# Fail fast if the Python auth stack cannot mint tokens — every step below
# depends on it, and a broken credential otherwise fails all 15 steps one by
# one with confusing per-step errors. Uses the same code path the steps use
# (common.get_access_token). return/exit keeps this safe when sourced.
if ! ADC_ERROR=$(python3 -c "import common; common.get_access_token()" 2>&1 >/dev/null); then
    echo "ERROR: credentials preflight failed:"
    echo "${ADC_ERROR}" | tail -n 3 | sed 's/^/    /'
    echo "  GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-<unset>}"
    echo "  If it is set, it may point to a stale or invalid service-account key —"
    echo "  unset it, or refresh user credentials with:"
    echo "    gcloud auth application-default login"
    return 1 2>/dev/null || exit 1
fi

TOTAL=15
FAILED=0
SUCCEEDED=0

run_step() {
    local step="$1"
    local desc="$2"
    local cmd="$3"
    echo "[${step}/${TOTAL}] ${desc}..."
    if eval "${cmd}"; then
        SUCCEEDED=$((SUCCEEDED + 1))
    else
        echo "  WARNING: Step ${step} failed (${desc}) — continuing"
        FAILED=$((FAILED + 1))
    fi
}

echo "=== Post-Deploy: Creating FSI governance resources ==="

run_step  1 "Creating Knowledge Catalog infrastructure" "python3 00_create_dataplex_infra.py"
run_step  2 "Creating business glossary & links"    "python3 01_create_glossary.py"
run_step  3 "Creating data scans"                   "python3 02_create_scans.py"
run_step  4 "Creating source system entries"        "python3 03_create_source_entries.py"
run_step  5 "Applying custom aspects"               "python3 04_create_aspects.py"
run_step  6 "Creating data products"                "python3 05_create_data_products.py"
run_step  7 "Creating data lineage"                 "python3 07_create_lineage.py"
run_step  8 "Publishing scan results"               "python3 08_publish_scans.py"
run_step  9 "Running query simulation"              "python3 09_simulate_queries.py --iterations 1"
run_step 10 "Creating reusable rule library"        "python3 10_create_rule_library.py"
run_step 11 "Running profile and insights scans"    "python3 11_run_scans_and_apply_insights.py"
run_step 12 "Enriching glossary term overviews"     "python3 12_enrich_glossary.py"
run_step 13 "Applying insights descriptions"        "python3 13_apply_insights_descriptions.py"
run_step 14 "Injecting dirty data for DQ failures"  "python3 15_inject_dirty_data.py"
run_step 15 "Creating column-level policy tags"     "python3 16_create_policy_tags.py"

echo ""
echo "=== Post-Deploy Complete ==="
echo "  Succeeded: ${SUCCEEDED}/${TOTAL}"
if [ ${FAILED} -gt 0 ]; then
    echo "  Failed:    ${FAILED}/${TOTAL} (check logs above)"
    exit 1
fi
