#!/usr/bin/env python3
"""Run Phase K1 verification on Cross-Cloud #2 (Price Gaps) and save to logs/k1.json."""

import json
import os
import re
import subprocess
import time
import google.auth
import google.auth.transport.requests
import requests

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE"] = "false"

PROJECT_NUMBER = "98236392654"
LOCATION = "us-central1"
QUESTION = "Which of our SKUs are priced above competitors right now, and what is that costing us in units?"
OUT_PATH = "logs/k1.json"


def get_kc_agent_id():
    try:
        out = subprocess.check_output(
            [
                "gcloud", "secrets", "versions", "access", "latest",
                "--secret=retail-kc-agent-id", "--project=alitch-ca-demo",
            ],
            text=True,
        ).strip()
        if out:
            return out
    except Exception:
        pass
    return "8060330902103785472"


def get_token():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def main():
    os.makedirs("logs", exist_ok=True)
    agent_id = get_kc_agent_id()
    ae_base = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{agent_id}"

    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Create session
    sess_resp = requests.post(
        f"{ae_base}:query",
        headers=headers,
        json={"class_method": "async_create_session", "input": {"user_id": "k1_verifier"}},
        timeout=60,
    )
    sess_resp.raise_for_status()
    out = sess_resp.json().get("output", {})
    session_id = out.get("id", "") if isinstance(out, dict) else str(out)
    print(f"Created session {session_id} on KC agent {agent_id}")

    t0 = time.time()
    stream_resp = requests.post(
        f"{ae_base}:streamQuery",
        headers=headers,
        json={
            "class_method": "async_stream_query",
            "input": {
                "message": QUESTION,
                "user_id": "k1_verifier",
                "session_id": session_id,
            },
        },
        stream=True,
        timeout=(30, 360),
    )
    stream_resp.raise_for_status()

    tool_calls = []
    text_chunks = []
    raw_events = []

    for line in stream_resp.iter_lines():
        if not line:
            continue
        raw = line.decode("utf-8").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        raw_events.append(data)
        parts = data.get("content", {}).get("parts", [])
        for p in parts:
            if "function_call" in p:
                fc = p["function_call"]
                tool_calls.append({"name": fc.get("name", ""), "args": fc.get("args", {})})
                print(f"  [tool_call] {fc.get('name', '')}")
            elif "text" in p:
                text_chunks.append(p["text"])

    elapsed = round(time.time() - t0, 2)
    full_text = "".join(text_chunks)

    sections_present = {
        "Data discovery": bool(re.search(r"\*\*Data discovery\.?\*\*", full_text, re.I)),
        "Finding": bool(re.search(r"\*\*Finding\.?\*\*", full_text, re.I)),
        "Governance Context": bool(re.search(r"\*\*Governance Context\.?\*\*", full_text, re.I)),
        "Recommendations": bool(re.search(r"\*\*Recommendations\.?\*\*", full_text, re.I)),
    }

    payload = {
        "agent_id": agent_id,
        "question": QUESTION,
        "latency_s": elapsed,
        "tool_calls": tool_calls,
        "tool_names": [tc["name"] for tc in tool_calls],
        "sections_present": sections_present,
        "all_4_sections": all(sections_present.values()),
        "response": full_text,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Saved logs/k1.json in {elapsed}s | tools={payload['tool_names']} | all_4_sections={payload['all_4_sections']}")


if __name__ == "__main__":
    main()
