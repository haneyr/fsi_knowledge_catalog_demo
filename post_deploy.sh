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
# Runs all Python scripts that create Dataplex resources via REST APIs.
# Called automatically by deploy.sh / deploy-existing-project.sh
####################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/scripts" && pwd)"
cd "${SCRIPT_DIR}"

echo "=== Post-Deploy: Creating FSI governance resources ==="

echo "[1/10] Creating business glossary..."
python3 01_create_glossary.py

echo "[2/10] Creating Dataplex scans..."
python3 02_create_scans.py

echo "[3/10] Creating source system entries..."
python3 03_create_source_entries.py

echo "[4/10] Applying custom aspects..."
python3 04_create_aspects.py

echo "[5/10] Creating data products..."
python3 05_create_data_products.py

echo "[6/10] Creating glossary-to-column links..."
python3 06_create_glossary_links.py

echo "[7/10] Creating data lineage..."
python3 07_create_lineage.py

echo "[8/10] Publishing scan results..."
python3 08_publish_scans.py

echo "[9/10] Running query simulation..."
python3 09_simulate_queries.py --iterations 1

echo "[10/10] Creating reusable rule library..."
python3 10_create_rule_library.py

echo "=== Post-Deploy Complete ==="
