#!/usr/bin/env python3
"""
Run the Phase B + C1 Tier Matrix against the three deployed Reasoning Engines:
- 12 Retail Questions (3 tabs x 4 tiers) across Basic, Scaled, KC
- 4 Cross-Cloud NEXUS Questions (4 tiers) on KC Agent
Saves full results to logs/bcd_tier_matrix.json (resumable/idempotent).
"""
import concurrent.futures
import json
import os
import time
import google.auth
import google.auth.transport.requests
import requests

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
PROJECT_NUMBER = "98236392654"
LOCATION = "us-central1"
AE_BASE = f"https://{LOCATION}-aiplatform.googleapis.com/v1"

AGENTS = {
    "basic": "2946493525224587264",
    "scaled": "1975967805526245376",
    "kc": "8060330902103785472",
}

QUESTIONS = [
    # Tab 1: MERCHANDISING & INVENTORY
    {
        "id": "M_T1", "tab": "MERCHANDISING & INVENTORY", "tier": 1, "chip": "1 Assortment Margin",
        "q": "Which merchandise assortments had the highest YTD return and market value in gold_assortment_performance?",
        "agents": ["basic", "scaled", "kc"],
    },
    {
        "id": "M_T2", "tab": "MERCHANDISING & INVENTORY", "tier": 2, "chip": "2 Markdown Exposure",
        "q": "For active merchandise assortments, which GTIN-13 SKUs carry the largest unrealized inventory loss, who is the assigned category manager, and how does their sector's 1-day 99% Markdown Value at Risk compare?",
        "agents": ["basic", "scaled", "kc"],
    },
    {
        "id": "M_T3", "tab": "MERCHANDISING & INVENTORY", "tier": 3, "chip": "3 Certification & GTIN DQ",
        "q": "Which assortment and product SKU tables are certified in Knowledge Catalog, who owns them, and can we trust the GTIN-13 identifiers in silver_product_skus?",
        "agents": ["basic", "scaled", "kc"],
    },
    {
        "id": "M_T4", "tab": "MERCHANDISING & INVENTORY", "tier": 4, "chip": "4 Governed Markdown Plan",
        "q": "Build a markdown risk plan for underperforming assortments using only certified Gold tables with no PCI-scoped columns, and quantify the working capital impact.",
        "agents": ["basic", "scaled", "kc"],
    },
    # Tab 2: CUSTOMER & LOYALTY
    {
        "id": "C_T1", "tab": "CUSTOMER & LOYALTY", "tier": 1, "chip": "1 Loyalty Tiers",
        "q": "How many active customers and what total relationship value do we have by customer segment in gold_customer_360?",
        "agents": ["basic", "scaled", "kc"],
    },
    {
        "id": "C_T2", "tab": "CUSTOMER & LOYALTY", "tier": 2, "chip": "2 Omnichannel Revenue",
        "q": "Across our active VIP loyalty tiers, how does Customer Lifetime Value (CLV) and e-commerce order volume compare against active BNPL balances and average Return-Risk Score by primary store region?",
        "agents": ["basic", "scaled", "kc"],
    },
    {
        "id": "C_T3", "tab": "CUSTOMER & LOYALTY", "tier": 3, "chip": "3 Customer Lineage",
        "q": "Where does our customer and loyalty data originate, how does it flow from source systems to gold_customer_360, and who is the data steward?",
        "agents": ["basic", "scaled", "kc"],
    },
    {
        "id": "C_T4", "tab": "CUSTOMER & LOYALTY", "tier": 4, "chip": "4 Consent & Return Abuse",
        "q": "Identify VIP or high-risk customers whose return and promo activity flags abuse risk, showing only their marketing consent verification status and high-value refunds.",
        "agents": ["basic", "scaled", "kc"],
    },
    # Tab 3: PRIVACY & COMPLIANCE
    {
        "id": "P_T1", "tab": "PRIVACY & COMPLIANCE", "tier": 1, "chip": "1 BNPL Risk Tiers",
        "q": "Give me a breakdown of our BNPL plans by plan type, risk rating, and average Return-Risk score.",
        "agents": ["basic", "scaled", "kc"],
    },
    {
        "id": "P_T2", "tab": "PRIVACY & COMPLIANCE", "tier": 2, "chip": "2 Vintage Delinquency",
        "q": "Are BNPL delinquencies trending up or down across origination vintages, and which segments have the highest 90+ day delinquency rate?",
        "agents": ["basic", "scaled", "kc"],
    },
    {
        "id": "P_T3", "tab": "PRIVACY & COMPLIANCE", "tier": 3, "chip": "3 PCI & PII Scope",
        "q": "Which tables contain PCI-DSS payment card data or CCPA-regulated PII in Knowledge Catalog, and what are their data classification and access control levels?",
        "agents": ["basic", "scaled", "kc"],
    },
    {
        "id": "P_T4", "tab": "PRIVACY & COMPLIANCE", "tier": 4, "chip": "4 Dashboard Lineage & Audit",
        "q": "Which PCI-scoped or PII-classified columns feed our compliance and executive dashboards, what is their lineage back to the source system, and are all compliance schedules met?",
        "agents": ["basic", "scaled", "kc"],
    },
    # Tab 4: CROSS-CLOUD (KC only)
    {
        "id": "X_T1", "tab": "CROSS-CLOUD", "tier": 1, "chip": "1 NEXUS Discovery",
        "q": "What external syndicated retail market intelligence tables are available in the NEXUS catalog?",
        "agents": ["kc"],
    },
    {
        "id": "X_T2", "tab": "CROSS-CLOUD", "tier": 2, "chip": "2 Cross-Cloud Joins",
        "q": "Which NEXUS syndicated tables can I join to our Gold category and assortment performance data, and on what keys?",
        "agents": ["kc"],
    },
    {
        "id": "X_T3", "tab": "CROSS-CLOUD", "tier": 3, "chip": "3 License & Residency",
        "q": "What is the license classification and data residency of our NEXUS syndicated data, and who owns the external vendor agreement?",
        "agents": ["kc"],
    },
    {
        "id": "X_T4", "tab": "CROSS-CLOUD", "tier": 4, "chip": "4 Margin & Price Benchmarks",
        "q": "How do our margins on top-selling categories compare to syndicated market benchmarks, and which of our SKUs are priced above competitors?",
        "agents": ["kc"],
    },
]

OUT_PATH = "logs/bcd_tier_matrix.json"


def get_token():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def query_agent(agent_key, question, q_id):
    token = get_token()
    agent_id = AGENTS[agent_key]
    base_url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{agent_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    user_id = f"matrix-{q_id}-{agent_key}-{int(time.time())}"

    s_resp = requests.post(
        f"{base_url}:query",
        headers=headers,
        json={"class_method": "async_create_session", "input": {"user_id": user_id}},
        timeout=30,
    )
    session_id = s_resp.json().get("output", {}).get("id", "") if s_resp.status_code == 200 else ""

    body = {"class_method": "async_stream_query", "input": {"user_id": user_id, "message": question}}
    if session_id:
        body["input"]["session_id"] = session_id

    resp = requests.post(f"{base_url}:streamQuery", headers=headers, json=body, stream=True, timeout=120)
    tools = []
    texts = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.strip():
            continue
        try:
            d = json.loads(line)
            for p in d.get("content", {}).get("parts", []):
                if "function_call" in p:
                    fc = p["function_call"]
                    tools.append(f"{fc.get('name')}:{json.dumps(fc.get('args', {}))[:100]}")
                elif "text" in p and not p.get("thought"):
                    texts.append(p["text"])
        except Exception:
            pass
    return {
        "status": resp.status_code,
        "tools": tools,
        "text": "".join(texts).strip(),
    }


def main():
    import sys
    only_t2 = "--only-t2" in sys.argv
    results = {}
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH) as f:
                results = json.load(f)
        except Exception:
            results = {}

    tasks = []
    for item in QUESTIONS:
        qid = item["id"]
        if only_t2 and qid not in ("M_T2", "C_T2", "P_T2"):
            continue
        if qid not in results or only_t2:
            results[qid] = {
                "tab": item["tab"],
                "tier": item["tier"],
                "chip": item["chip"],
                "question": item["q"],
                "responses": {},
            }
        for ag in item["agents"]:
            if only_t2 or ag not in results[qid]["responses"] or not results[qid]["responses"][ag].get("text"):
                tasks.append((qid, ag, item["q"]))

    print(f"Running {len(tasks)} agent queries with 6 workers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        future_map = {
            ex.submit(query_agent, ag, q, qid): (qid, ag)
            for (qid, ag, q) in tasks
        }
        for fut in concurrent.futures.as_completed(future_map):
            qid, ag = future_map[fut]
            try:
                res = fut.result()
                results[qid]["responses"][ag] = res
                print(f"Done {qid} [{ag}]: status={res['status']} tools={len(res['tools'])} len={len(res['text'])}")
            except Exception as e:
                print(f"Error {qid} [{ag}]: {e}")
                results[qid]["responses"][ag] = {"status": 500, "tools": [], "text": f"ERROR: {e}"}
            with open(OUT_PATH, "w") as f:
                json.dump(results, f, indent=2)

    print("All queries finished and saved to", OUT_PATH)


if __name__ == "__main__":
    main()
