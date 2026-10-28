#!/usr/bin/env python3
"""Phase P6 End-to-End Validation Script for Northwind Retail Knowledge Catalog Demo.

Tests:
1. Cloud Run service (`retail-kc-demo-ui-live`) health, `/`, `/api/config`, and `/static/static-responses.json`.
2. Vertex AI Agent Engine live query smoke test against all 3 deployed retail agents:
   - Basic Agent (`2946493525224587264` — `[Retail] retail-agent-basic`)
   - Scaled Agent (`1975967805526245376` — `[Retail] retail-agent-scaled`)
   - KC-Guided Agent (`8060330902103785472` — `[Retail] retail-agent-kc`)
3. Summary report written to stdout and `logs/verify_p6.json`.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request

PROJECT_ID = "alitch-ca-demo"
PROJECT_NUMBER = "98236392654"
REGION = "us-central1"
CLOUD_RUN_URL = "https://retail-kc-demo-ui-live-98236392654.us-central1.run.app"
CLOUD_RUN_ALT_URL = "https://retail-kc-demo-ui-live-esoohbbsma-uc.a.run.app"

AGENTS = {
    "basic": {
        "id": "2946493525224587264",
        "display_name": "[Retail] retail-agent-basic",
        "prompt": "Using gold_customer_360, how many customers are in each customer_segment and what is their average total_relationship_value? Run the SQL query.",
    },
    "scaled": {
        "id": "1975967805526245376",
        "display_name": "[Retail] retail-agent-scaled",
        "prompt": "Which table should I use for store return rates and net margin by region, and what are the top 3 stores by revenue in gold_store_performance?",
    },
    "kc": {
        "id": "8060330902103785472",
        "display_name": "[Retail] retail-agent-kc",
        "prompt": "Search the Northwind Retail Business Glossary for Gross Margin and check the governance aspects and upstream lineage for retail_gold.gold_gross_margin_analysis.",
    },
}


def get_token() -> str:
    return (
        subprocess.check_output(["gcloud", "auth", "print-access-token"])
        .decode()
        .strip()
    )


def verify_cloud_run() -> dict:
    print("=== 1. Verifying Cloud Run Service (retail-kc-demo-ui-live) ===")
    results = {}

    # 1a. GET /
    req = urllib.request.Request(f"{CLOUD_RUN_URL}/")
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        results["index_status"] = resp.status
        results["has_northwind_branding"] = "Northwind Retail" in html
        results["has_meridian_bank"] = "Meridian National Bank" in html
        print(
            f"  GET / -> HTTP {resp.status}, Northwind Retail branding={results['has_northwind_branding']}, Meridian Bank={results['has_meridian_bank']}"
        )

    # 1b. GET /api/config
    req_cfg = urllib.request.Request(f"{CLOUD_RUN_URL}/api/config")
    with urllib.request.urlopen(req_cfg, timeout=20) as resp:
        cfg = json.loads(resp.read().decode("utf-8"))
        results["api_config_status"] = resp.status
        results["api_config"] = {
            "live_mode": cfg.get("live_mode"),
            "oauth_client_id_set": bool(cfg.get("oauth_client_id")),
            "project_id": cfg.get("project_id"),
            "agents": cfg.get("agents"),
        }
        print(f"  GET /api/config -> HTTP {resp.status}: {results['api_config']}")

    # 1c. GET /static/static-responses.json
    req_static = urllib.request.Request(
        f"{CLOUD_RUN_URL}/static/static-responses.json"
    )
    with urllib.request.urlopen(req_static, timeout=20) as resp:
        static_data = json.loads(resp.read().decode("utf-8"))
        results["static_responses_status"] = resp.status
        results["static_responses_count"] = len(static_data)
        print(
            f"  GET /static/static-responses.json -> HTTP {resp.status}, keys={len(static_data)}"
        )

    return results


def query_agent(agent_key: str, spec: dict, token: str) -> dict:
    engine_id = spec["id"]
    prompt = spec["prompt"]
    print(f"\n=== 2.{agent_key}: Querying {spec['display_name']} ({engine_id}) ===")
    t0 = time.time()

    # Step 1: Create session via :query
    url_query = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/reasoningEngines/{engine_id}:query"
    session_payload = {
        "class_method": "async_create_session",
        "input": {"user_id": "p6-validator"},
    }
    req_sess = urllib.request.Request(
        url_query,
        data=json.dumps(session_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req_sess, timeout=60) as resp:
        sess_resp = json.loads(resp.read().decode("utf-8"))
    session_id = sess_resp.get("output", {}).get("id")
    print(f"  Created session_id={session_id}")

    # Step 2: Stream query via :streamQuery?alt=sse
    url_stream = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/reasoningEngines/{engine_id}:streamQuery?alt=sse"
    stream_payload = {
        "class_method": "async_stream_query",
        "input": {
            "user_id": "p6-validator",
            "session_id": session_id,
            "message": prompt,
        },
    }
    req_stream = urllib.request.Request(
        url_stream,
        data=json.dumps(stream_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    text_chunks = []
    tool_calls = []
    with urllib.request.urlopen(req_stream, timeout=180) as resp:
        raw_body = resp.read().decode("utf-8", errors="replace")

    for line in raw_body.splitlines():
        line = line.strip()
        if not line:
            continue
        json_str = line[5:].strip() if line.startswith("data:") else line
        try:
            evt = json.loads(json_str)
        except Exception:
            continue
        parts = evt.get("content", {}).get("parts", [])
        for part in parts:
            if "function_call" in part:
                fc = part["function_call"]
                tool_calls.append(fc.get("name", "unknown"))
            if "text" in part and not part.get("thought"):
                text_chunks.append(part["text"])

    full_text = "".join(text_chunks).strip()
    elapsed = round(time.time() - t0, 2)
    print(
        f"  Completed in {elapsed}s | tool_calls={tool_calls} | response_len={len(full_text)}"
    )
    preview = full_text[:300].replace("\n", " ")
    print(f"  Preview: {preview}...")

    return {
        "engine_id": engine_id,
        "display_name": spec["display_name"],
        "session_id": session_id,
        "elapsed_sec": elapsed,
        "tool_calls": tool_calls,
        "response_length": len(full_text),
        "response_preview": full_text[:600],
        "success": len(full_text) > 0,
    }


def main():
    token = get_token()
    report = {
        "cloud_run_url": CLOUD_RUN_URL,
        "cloud_run_alt_url": CLOUD_RUN_ALT_URL,
        "cloud_run": verify_cloud_run(),
        "agents": {},
    }

    for key, spec in AGENTS.items():
        try:
            report["agents"][key] = query_agent(key, spec, token)
        except Exception as e:
            print(f"  ERROR querying {key}: {e}")
            report["agents"][key] = {"error": str(e), "success": False}

    os.makedirs("logs", exist_ok=True)
    with open("logs/verify_p6.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    all_ok = (
        report["cloud_run"].get("index_status") == 200
        and report["cloud_run"].get("has_northwind_branding") is True
        and report["cloud_run"].get("has_meridian_bank") is False
        and all(a.get("success") for a in report["agents"].values())
    )
    print(f"\n=== P6 VALIDATION OVERALL PASS: {all_ok} ===")
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
