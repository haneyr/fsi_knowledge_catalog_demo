#!/usr/bin/env python3
"""
Run ONE test question against the redeployed retail-agent-kc:
"Which product categories had the highest margin last quarter?"
Writes full response and tool trace to logs/k1_test.json and prints ONLY:
- sections present Y/N
- tables touched by layer
- glossary term cited
- DQ scan cited
"""
import json
import os
import re
import time
import google.auth
import google.auth.transport.requests
import requests

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE"] = "false"

PROJECT_ID = "alitch-ca-demo"
PROJECT_NUMBER = "98236392654"
LOCATION = "us-central1"
AE_BASE = f"https://{LOCATION}-aiplatform.googleapis.com/v1"
QUESTION = "Which product categories had the highest margin last quarter?"
OUTPUT_PATH = "logs/k1_test.json"


def get_kc_agent_id() -> str:
    env_id = os.environ.get("KC_AGENT_ID")
    if env_id:
        return env_id
    return "8060330902103785472"


def main():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    token = creds.token

    agent_id = get_kc_agent_id()
    session_url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{agent_id}:query"
    user_id = f"k1-test-{int(time.time())}"
    sresp = requests.post(
        session_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"class_method": "async_create_session", "input": {"user_id": user_id}},
        timeout=30,
    )
    output = sresp.json().get("output", {})
    session_id = output.get("id", "") if isinstance(output, dict) else str(output)

    stream_url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{agent_id}:streamQuery"
    t0 = time.time()
    resp = requests.post(
        stream_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "class_method": "async_stream_query",
            "input": {"message": QUESTION, "user_id": user_id, "session_id": session_id},
        },
        stream=True,
        timeout=240,
    )

    tool_calls = []
    text_chunks = []
    touched_tables = []

    table_pat = re.compile(r"\b((?:gold|silver|bronze|ref|nexus)_[a-z0-9_]+)\b", re.IGNORECASE)

    for line in resp.iter_lines():
        if not line:
            continue
        raw = line.decode("utf-8").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        for part in data.get("content", {}).get("parts", []):
            if "function_call" in part:
                fc = part["function_call"]
                name = fc.get("name", "")
                args = fc.get("args", {})
                tables = [m.lower() for m in table_pat.findall(json.dumps(args))]
                touched_tables.extend(tables)
                tool_calls.append({"name": name, "args": args, "tables": tables})
            elif "text" in part:
                text_chunks.append(part["text"])

    full_text = "".join(text_chunks)
    cited_tables = [m.lower() for m in table_pat.findall(full_text)]
    all_touched = []
    for t in touched_tables + cited_tables:
        if t not in all_touched:
            all_touched.append(t)

    by_layer = {"gold": [], "silver": [], "bronze": [], "other": []}
    for t in all_touched:
        if t.startswith("gold_"):
            by_layer["gold"].append(t)
        elif t.startswith("silver_"):
            by_layer["silver"].append(t)
        elif t.startswith("bronze_"):
            by_layer["bronze"].append(t)
        else:
            by_layer["other"].append(t)

    sections = {
        "Data discovery": "Y" if re.search(r"\*\*Data discovery\.?\*\*", full_text, re.I) else "N",
        "Finding": "Y" if re.search(r"\*\*Finding\.?\*\*", full_text, re.I) else "N",
        "Governance Context": "Y" if re.search(r"\*\*Governance Context\.?\*\*", full_text, re.I) else "N",
        "Recommendations": "Y" if re.search(r"\*\*Recommendations\.?\*\*", full_text, re.I) else "N",
    }

    glossary_matches = re.findall(r"\[Retail\]\s+[A-Za-z0-9\s\(\)\-/&]+", full_text)
    glossary_cited = glossary_matches[0].strip() if glossary_matches else "NONE"

    dq_matches = re.findall(r"\bdq-[a-z0-9\-]+\b", full_text, re.I)
    dq_cited = dq_matches[0] if dq_matches else "NONE"

    os.makedirs("logs", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(
            {
                "question": QUESTION,
                "agent_id": agent_id,
                "latency_s": round(time.time() - t0, 1),
                "sections_present": sections,
                "tables_touched_by_layer": by_layer,
                "glossary_term_cited": glossary_cited,
                "dq_scan_cited": dq_cited,
                "tool_calls": tool_calls,
                "response": full_text,
            },
            f,
            indent=2,
        )

    print(f"sections_present: {json.dumps(sections)}")
    print(f"tables_touched_by_layer: {json.dumps(by_layer)}")
    print(f"glossary_term_cited: {glossary_cited}")
    print(f"dq_scan_cited: {dq_cited}")


if __name__ == "__main__":
    main()
