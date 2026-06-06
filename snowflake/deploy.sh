#!/bin/bash
# Orchestrates Snowflake NEXUS integration setup.
# Requires: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [ -z "${SNOWFLAKE_ACCOUNT}" ]; then
    echo "ERROR: SNOWFLAKE_ACCOUNT not set. Skipping Snowflake setup."
    exit 1
fi

TOTAL=4
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

echo "=== Snowflake NEXUS Integration Setup ==="

run_step 1 "Creating NEXUS database and data in Snowflake"  "python3 00_setup_nexus_data.py"
run_step 2 "Creating Knowledge Catalog infrastructure"       "python3 01_create_dataplex_infra.py"
run_step 3 "Ingesting Horizon metadata into Knowledge Catalog" "python3 02_ingest_metadata.py"
run_step 4 "Enriching entries with glossary and aspects"     "python3 03_enrich_entries.py"

echo ""
echo "=== Snowflake Setup Complete ==="
echo "  Succeeded: ${SUCCEEDED}/${TOTAL}"
if [ ${FAILED} -gt 0 ]; then
    echo "  Failed:    ${FAILED}/${TOTAL} (check logs above)"
    exit 1
fi
