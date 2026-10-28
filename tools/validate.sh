#!/usr/bin/env bash
# Idempotent End-to-End Validation Script for Northwind Retail Knowledge Catalog Demo (P6)
set -euo pipefail

export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-alitch-ca-demo}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
CANONICAL_URL="https://retail-kc-demo-ui-live-98236392654.us-central1.run.app"

echo "=== 1. Shell Script Syntax Check (bash -n) ==="
while IFS= read -r -d '' sh_file; do
  bash -n "$sh_file"
done < <(find . -maxdepth 3 -name "*.sh" -not -path "./.git/*" -print0)
echo "  PASS: All shell scripts passed bash -n (including clean_up.sh)"

echo "=== 2. Python Syntax Check (py_compile) ==="
python3 - <<'PY'
import pathlib, py_compile, sys
for p in sorted(pathlib.Path(".").rglob("*.py")):
    if ".git" in p.parts or "__pycache__" in p.parts:
        continue
    py_compile.compile(str(p), doraise=True)
print("  PASS: All Python files compiled cleanly")
PY

echo "=== 3. Cloud Run IAM Policy Check ==="
IAM_JSON=$(gcloud run services get-iam-policy retail-kc-demo-ui-live --region="${REGION}" --project="${PROJECT_ID}" --format=json)
python3 -c '
import json, sys
policy = json.loads(sys.argv[1])
invokers = [m for b in policy.get("bindings", []) if b.get("role") == "roles/run.invoker" for m in b.get("members", [])]
assert "allUsers" in invokers, f"allUsers not in roles/run.invoker: {invokers}"
print("  PASS: allUsers bound to roles/run.invoker")
' "${IAM_JSON}"

echo "=== 4. Cloud Run Live /api/config Check (${CANONICAL_URL}) ==="
CFG_JSON=$(curl -sf "${CANONICAL_URL}/api/config")
python3 -c '
import json, sys
cfg = json.loads(sys.argv[1])
assert cfg["live_mode"] is True, f"live_mode={cfg.get('"'"'live_mode'"'"')}"
assert cfg["agents"] == {"basic": True, "kc": True, "scaled": True}, f"agents={cfg.get('"'"'agents'"'"')}"
assert len(cfg["all_table_names"]) == 128, f"Expected 128 tables, got {len(cfg['"'"'all_table_names'"'"'])}"
dm = cfg["dataset_map"]
assert dm["staging_"] == "retail_staging", f"staging_ mapped to {dm.get('"'"'staging_'"'"')}"
assert dm["snapshot_"] == "retail_snapshots", f"snapshot_ mapped to {dm.get('"'"'snapshot_'"'"')}"
assert dm["audit_"] == "retail_audit", f"audit_ mapped to {dm.get('"'"'audit_'"'"')}"
assert bool(cfg.get("oauth_client_id")), "oauth_client_id missing"
print("  PASS: /api/config verified (live_mode=True, 128 tables, dataset_map=retail_staging/retail_snapshots/retail_audit)")
' "${CFG_JSON}"

echo "=== 5. P6 Tier Matrix Check (logs/p6_tier_matrix.json) ==="
if [ -f logs/p6_tier_matrix.json ]; then
  python3 - <<'PY'
import json
with open("logs/p6_tier_matrix.json", encoding="utf-8") as f:
    matrix = json.load(f)
assert len(matrix) == 15, f"Expected 15 questions, got {len(matrix)}"
print(f"  PASS: logs/p6_tier_matrix.json present with {len(matrix)} evaluated scenarios")
PY
else
  echo "  WARN: logs/p6_tier_matrix.json not yet generated"
fi

echo "=== Validation Complete ==="
