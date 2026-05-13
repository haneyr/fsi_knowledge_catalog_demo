#!/usr/bin/env python3
"""
FSI Knowledge Catalog Demo — Live WebSocket Web Application

Streams agent responses in real-time via WebSocket, parsing Agent Engine
streamQuery events to drive point cloud animations on the frontend.

Env vars:
    GOOGLE_CLOUD_PROJECT — GCP project ID
    GOOGLE_CLOUD_LOCATION — Agent Engine region (default: us-central1)
    BASIC_AGENT_ID — Agent Engine ID for basic agent
    SCALED_AGENT_ID — Agent Engine ID for scaled agent
    KC_AGENT_ID — Agent Engine ID for KC agent
"""

import json
import os
import re
import time
import logging

import google.auth
import google.auth.transport.requests
import requests as http_requests
from flask import Flask, send_from_directory, request, jsonify

app = Flask(__name__, static_folder="static")
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
PROJECT_NUMBER = os.environ.get("PROJECT_NUMBER", "")

AGENT_IDS = {
    "basic": os.environ.get("BASIC_AGENT_ID", ""),
    "scaled": os.environ.get("SCALED_AGENT_ID", ""),
    "kc": os.environ.get("KC_AGENT_ID", ""),
}

AE_BASE = f"https://{LOCATION}-aiplatform.googleapis.com/v1"
_sessions = {}

ALL_TABLE_NAMES = []
for prefix in ['bronze_', 'silver_', 'gold_', 'ref_', 'staging_', 'snapshot_', 'audit_', 'vw_']:
    for suffix in ['customers','accounts','transactions','loans','loan_payments','credit_cards',
        'card_transactions','fraud_alerts','kyc_records','branches','employees','wire_transfers',
        'ach_transfers','atm_transactions','wm_clients','portfolios','holdings','trades',
        'securities','advisors','performance','fee_schedules','benchmarks','client_goals',
        'risk_profiles','distributions','custodian_feeds','gl_entries','gl_accounts',
        'cost_centers','regulatory_capital','risk_exposures','counterparties','market_data',
        'stress_tests','audit_events','regulatory_filings','interest_rates','fx_rates',
        'compliance_cases','customer_360','account_summary','transaction_patterns',
        'loan_portfolio_summary','delinquency_analysis','fraud_analytics','aml_risk_scoring',
        'branch_performance','portfolio_performance','client_revenue','asset_allocation',
        'advisor_scorecard','fee_revenue','net_interest_margin','capital_adequacy',
        'liquidity_coverage','market_risk_var','operational_risk','regulatory_dashboard',
        'balance_sheet_summary']:
        ALL_TABLE_NAMES.append(f"{prefix}{suffix}")

GLOSSARY_TERM_MAP = {
    'search_entries': [],
    'fico': ['FICO Score'], 'cusip': ['CUSIP'], 'isin': ['ISIN'],
    'aum': ['AUM'], 'sar': ['SAR'], 'bsa': ['SAR'],
    'cet1': ['CET1 Ratio'], 'capital': ['CET1 Ratio'],
    'kyc': ['KYC'], 'delinquen': ['Delinquency'],
    'customer': ['Customer ID'], 'branch': ['Branch'],
    'nim': ['NIM'], 'interest rate': ['NIM'],
    'var': ['VaR'], 'risk': ['Risk Rating'],
}


def _get_token():
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _get_project_number():
    global PROJECT_NUMBER
    if not PROJECT_NUMBER and PROJECT_ID:
        try:
            import subprocess
            result = subprocess.run(
                ["gcloud", "projects", "describe", PROJECT_ID, "--format=value(projectNumber)"],
                capture_output=True, text=True, timeout=10)
            PROJECT_NUMBER = result.stdout.strip()
        except Exception:
            pass
    return PROJECT_NUMBER


def _ae_url(agent_id):
    pn = _get_project_number()
    return f"{AE_BASE}/projects/{pn}/locations/{LOCATION}/reasoningEngines/{agent_id}"


def _get_or_create_session(agent_id, user_id):
    key = f"{agent_id}:{user_id}"
    if key in _sessions:
        return _sessions[key]

    token = _get_token()
    resp = http_requests.post(
        f"{_ae_url(agent_id)}:query",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"class_method": "create_session", "input": {"user_id": user_id}},
        timeout=30,
    )
    if resp.status_code == 200:
        session_id = resp.json().get("output", {}).get("id", "")
        _sessions[key] = session_id
        return session_id
    return None


def _extract_tables(text):
    return [t for t in ALL_TABLE_NAMES if t in text.lower()]


def _extract_glossary_terms(text):
    terms = set()
    lower = text.lower()
    for keyword, term_list in GLOSSARY_TERM_MAP.items():
        if keyword in lower:
            terms.update(term_list)
    return list(terms)


def _parse_stream_chunk(raw_text):
    """Parse a single streamQuery response line into typed events."""
    events = []
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return events

    content = data.get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        if "function_call" in part:
            fc = part["function_call"]
            events.append({
                "type": "tool_call",
                "name": fc.get("name", ""),
                "args": fc.get("args", {}),
            })
        elif "function_response" in part:
            fr = part["function_response"]
            resp_data = fr.get("response", {})
            result_text = resp_data.get("result", str(resp_data))
            tables = _extract_tables(result_text)
            glossary = _extract_glossary_terms(result_text)
            events.append({
                "type": "tool_response",
                "name": fr.get("name", ""),
                "tables": tables,
                "glossary_terms": glossary,
            })
        elif "text" in part:
            events.append({
                "type": "text_chunk",
                "text": part["text"],
            })

    return events


# ---- Routes ----

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


@app.route("/api/config")
def config():
    return jsonify({
        "project_id": PROJECT_ID,
        "live_mode": any(AGENT_IDS.values()),
        "agents": {k: bool(v) for k, v in AGENT_IDS.items()},
    })


# ---- WebSocket ----

try:
    from flask_sock import Sock
    sock = Sock(app)

    @sock.route("/api/ws")
    def websocket_chat(ws):
        user_id = f"ws_user_{id(ws)}"

        while True:
            raw = ws.receive()
            if raw is None:
                break

            msg = json.loads(raw)
            agent_type = msg.get("agent", "basic")
            question = msg.get("question", "")
            agent_id = AGENT_IDS.get(agent_type, "")

            if not agent_id:
                ws.send(json.dumps({"type": "error", "message": f"No {agent_type} agent configured"}))
                continue

            start = time.time()
            ws.send(json.dumps({"type": "status", "message": "Connecting to agent..."}))

            try:
                session_id = _get_or_create_session(agent_id, user_id)
                if not session_id:
                    ws.send(json.dumps({"type": "error", "message": "Failed to create session"}))
                    continue

                token = _get_token()
                resp = http_requests.post(
                    f"{_ae_url(agent_id)}:streamQuery",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"input": {
                        "message": question,
                        "user_id": user_id,
                        "session_id": session_id,
                    }},
                    stream=True,
                    timeout=120,
                )

                if resp.status_code != 200:
                    ws.send(json.dumps({"type": "error", "message": f"Agent returned {resp.status_code}"}))
                    continue

                all_tables = []
                all_glossary = []

                for line in resp.iter_lines():
                    if not line:
                        continue
                    text = line.decode("utf-8").strip()
                    if not text:
                        continue

                    events = _parse_stream_chunk(text)
                    for event in events:
                        if event["type"] == "tool_response":
                            all_tables.extend(event.get("tables", []))
                            all_glossary.extend(event.get("glossary_terms", []))
                        ws.send(json.dumps(event))

                latency = time.time() - start
                ws.send(json.dumps({
                    "type": "done",
                    "latency": round(latency, 1),
                    "all_tables": list(set(all_tables)),
                    "all_glossary": list(set(all_glossary)),
                }))

            except Exception as e:
                ws.send(json.dumps({"type": "error", "message": str(e)[:300]}))

except ImportError:
    logger.warning("flask-sock not installed — WebSocket mode disabled")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _get_project_number()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
