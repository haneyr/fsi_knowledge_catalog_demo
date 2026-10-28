#!/usr/bin/env bash
# Idempotent runner for F1-F5 live Cloud Run + BigQuery + Agent Engine verification
# Requires active gcloud + ADC credentials for project alitch-ca-demo (98236392654)
set -euo pipefail

export GOOGLE_CLOUD_PROJECT="alitch-ca-demo"
export GOOGLE_API_USE_CLIENT_CERTIFICATE="false"
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE="false"
export CLOUDSDK_CORE_DISABLE_PROMPTS="1"

LIVE_URL="https://retail-kc-demo-ui-live-98236392654.us-central1.run.app"
ROLLBACK_REV="retail-kc-demo-ui-live-00004-fbd"

mkdir -p logs

echo "=== 0. Verify gcloud + ADC auth ==="
gcloud auth print-access-token >/dev/null
python3 -c "import google.auth, google.auth.transport.requests; c, _ = google.auth.default(); c.refresh(google.auth.transport.requests.Request())"

echo "=== 1. Launch F2 (Phase E Option 1: BQ refresh + DQ scans + dirty data) in background ==="
nohup bash -c '
  set -euo pipefail
  export GOOGLE_CLOUD_PROJECT="alitch-ca-demo"
  export GOOGLE_API_USE_CLIENT_CERTIFICATE="false"
  export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE="false"
  export CLOUDSDK_CORE_DISABLE_PROMPTS="1"
  echo "[F2] Starting deploy-bq.sh --refresh..."
  bash deploy-bq.sh --refresh
  echo "[F2] Starting deploy-bq-nokc.sh --refresh..."
  bash deploy-bq-nokc.sh --refresh
  echo "[F2] Updating DQ rule library and scans..."
  python3 scripts/10_create_rule_library.py
  python3 scripts/02_create_scans.py
  echo "[F2] Injecting intentional dirty data defects and triggering DQ rescans..."
  python3 scripts/15_inject_dirty_data.py
  echo "[F2] COMPLETE"
' > logs/f2_phase_e.log 2>&1 &
F2_PID=$!
echo "F2 running in background (PID=$F2_PID, log=logs/f2_phase_e.log)"

echo "=== 2. Single Cloud Run Redeploy covering F1 + F3 + F4 + F5 ==="
GOOGLE_CLOUD_PROJECT=alitch-ca-demo bash website-live/deploy.sh

echo "=== 3. Smoke test live Cloud Run ($LIVE_URL) ==="
HTTP_CODE=$(curl -s -o /tmp/live_config.json -w "%{http_code}" "$LIVE_URL/api/config")
TABLE_COUNT=$(python3 -c "import json; d=json.load(open('/tmp/live_config.json')); print(len(d.get('all_table_names', []))); assert d.get('environment')=='demo' and d.get('live_mode') is True")
if [[ "$HTTP_CODE" != "200" || "$TABLE_COUNT" != "128" ]]; then
  echo "SMOKE TEST FAILED (HTTP=$HTTP_CODE, tables=$TABLE_COUNT). Rolling back to $ROLLBACK_REV..."
  gcloud run services update-traffic retail-kc-demo-ui-live --to-revisions="$ROLLBACK_REV=100" --region=us-central1 --project=alitch-ca-demo
  exit 1
fi
echo "Smoke test /api/config PASSED: HTTP 200, 128 tables, environment=demo"

echo "=== 4. Wait for F2 background job (PID=$F2_PID) ==="
while kill -0 "$F2_PID" 2>/dev/null; do
  sleep 30
  tail -n 5 logs/f2_phase_e.log || true
done
wait "$F2_PID"
echo "F2 background job completed successfully."

echo "=== 5. Run 3 agents on 'Give me an overview of customer risk across the retailer' ==="
python3 - <<'PY'
import json, time, requests, google.auth, google.auth.transport.requests

creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
creds.refresh(google.auth.transport.requests.Request())
headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}

AGENTS = {
    "basic": "2946493525224587264",
    "scaled": "1975967805526245376",
    "kc": "8060330902103785472",
}
q = "Give me an overview of customer risk across the retailer"
out = {}
for name, aid in AGENTS.items():
    base = f"https://us-central1-aiplatform.googleapis.com/v1/projects/98236392654/locations/us-central1/reasoningEngines/{aid}"
    uid = f"f2-risk-{name}-{int(time.time())}"
    s = requests.post(f"{base}:query", headers=headers, json={"class_method": "async_create_session", "input": {"user_id": uid}}, timeout=30)
    sid = s.json().get("output", {}).get("id", "") if s.status_code == 200 else ""
    body = {"class_method": "async_stream_query", "input": {"user_id": uid, "message": q}}
    if sid:
        body["input"]["session_id"] = sid
    r = requests.post(f"{base}:streamQuery", headers=headers, json=body, stream=True, timeout=120)
    texts = []
    for line in r.iter_lines(decode_unicode=True):
        if line and line.strip():
            try:
                d = json.loads(line)
                for p in d.get("content", {}).get("parts", []):
                    if "text" in p and not p.get("thought"):
                        texts.append(p["text"])
            except Exception:
                pass
    out[name] = "".join(texts).strip()
    print(f"\n--- [{name.upper()} AGENT] ---\n{out[name]}\n")

with open("logs/f2_customer_risk_overview.json", "w") as f:
    json.dump(out, f, indent=2)
PY

echo "=== 6. Run F5 Tier 2 matrix (M_T2, C_T2, P_T2 x 3 agents) ==="
python3 tools/run_bcd_tier_matrix.py --only-t2
