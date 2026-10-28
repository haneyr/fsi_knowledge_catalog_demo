#!/usr/bin/env bash
set -euo pipefail

export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false
export GOOGLE_CLOUD_PROJECT=alitch-ca-demo
export PATH="$HOME/.local/bin:$PATH"

mkdir -p logs

ROLLBACK_REV=$(gcloud run services describe retail-kc-demo-ui-live --region=us-central1 --project=alitch-ca-demo --format="value(status.latestReadyRevisionName)")
echo "=== Rollback Cloud Run Revision: ${ROLLBACK_REV} ==="

echo "=== Step 1: Redeploying retail-agent-kc only ==="
bash agents/deploy_agents.sh kc

echo "=== Step 2: Deploying Cloud Run UI for badge update ==="
bash website-live/deploy.sh

NEW_REV=$(gcloud run services describe retail-kc-demo-ui-live --region=us-central1 --project=alitch-ca-demo --format="value(status.latestReadyRevisionName)")
echo "=== New Cloud Run Revision: ${NEW_REV} (Rollback: ${ROLLBACK_REV}) ==="

echo "=== Step 3: Running Cross-Cloud #2 (Price Gaps) verification ==="
python3 tools/run_k1_verify.py

echo "=== Phase K1 deploy & verify complete ==="
