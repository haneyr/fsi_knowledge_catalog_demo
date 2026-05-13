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
# Runs all Python scripts that create Dataplex and governance resources.
# Called after BigQuery tables are created (deploy-bq.sh or Terraform).
####################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/scripts" && pwd)"
cd "${SCRIPT_DIR}"

echo "=== Post-Deploy: Creating FSI governance resources ==="

echo "[0/15] Creating Dataplex infrastructure (entry types, aspect types, entry groups)..."
python3 00_create_dataplex_infra.py

echo "[1/15] Creating business glossary..."
python3 01_create_glossary.py

echo "[2/15] Creating Dataplex scans..."
python3 02_create_scans.py

echo "[3/15] Creating source system entries..."
python3 03_create_source_entries.py

echo "[4/15] Applying custom aspects..."
python3 04_create_aspects.py

echo "[5/15] Creating data products..."
python3 05_create_data_products.py

echo "[6/15] Creating glossary-to-column links..."
python3 06_create_glossary_links.py

echo "[7/15] Creating data lineage..."
python3 07_create_lineage.py

echo "[8/15] Publishing scan results..."
python3 08_publish_scans.py

echo "[9/15] Running query simulation..."
python3 09_simulate_queries.py --iterations 1

echo "[10/15] Creating reusable rule library..."
python3 10_create_rule_library.py

echo "[11/15] Running profile and insights scans..."
python3 11_run_scans_and_apply_insights.py

echo "[12/15] Enriching glossary term overviews..."
python3 12_enrich_glossary.py

echo "[13/15] Applying insights descriptions to BigQuery..."
python3 13_apply_insights_descriptions.py

echo "[14/15] Linking glossary terms to data assets..."
python3 14_link_glossary_to_assets.py

echo "=== Post-Deploy Complete ==="
