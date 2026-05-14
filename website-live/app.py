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

logging.basicConfig(level=logging.INFO)
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


_creds_cache = [None, 0]


def _get_token():
    import time
    now = time.time()
    if _creds_cache[0] is None or now - _creds_cache[1] > 250:
        creds, _ = google.auth.default()
        creds.refresh(google.auth.transport.requests.Request())
        _creds_cache[0] = creds.token
        _creds_cache[1] = now
    return _creds_cache[0]


_http_session = None


def _get_http_session():
    global _http_session
    if _http_session is None:
        _http_session = http_requests.Session()
    return _http_session


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

    try:
        token = _get_token()
        url = f"{_ae_url(agent_id)}:query"
        logger.info("Creating session: POST %s for user=%s", url, user_id)
        resp = _get_http_session().post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"class_method": "create_session", "input": {"user_id": user_id}},
            timeout=30,
        )
        logger.info("Session response: status=%d body=%s", resp.status_code, resp.text[:500])
        if resp.status_code == 200:
            output = resp.json().get("output", {})
            session_id = output.get("id", "") if isinstance(output, dict) else str(output)
            _sessions[key] = session_id
            return session_id
        return None
    except Exception as e:
        logger.exception("Failed to create session: %s", e)
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
            args = fc.get("args", {})
            args_text = str(args)
            events.append({
                "type": "tool_call",
                "name": fc.get("name", ""),
                "args": args,
                "tables": _extract_tables(args_text),
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


DATASET_MAP = {
    'gold_': 'fsi_gold', 'silver_': 'fsi_silver', 'bronze_': 'fsi_bronze',
    'ref_': 'fsi_reference', 'staging_': 'fsi_supplementary',
    'snapshot_': 'fsi_supplementary', 'audit_': 'fsi_supplementary',
    'vw_': 'fsi_views',
}

_table_info_cache = {}
_term_info_cache = {}

GLOSSARY_ID = os.environ.get("GLOSSARY_ID", "meridian-national-bank-glossary-us")


def _get_dataset(table_name):
    for prefix, ds in DATASET_MAP.items():
        if table_name.startswith(prefix):
            return ds
    return 'fsi_gold'


def _get_tier(table_name):
    for prefix in ('gold_', 'silver_', 'bronze_', 'ref_', 'staging_', 'snapshot_', 'audit_', 'vw_'):
        if table_name.startswith(prefix):
            return prefix.rstrip('_')
    return 'other'


@app.route("/api/table-info")
def table_info():
    table = request.args.get("table", "")
    if not table or not PROJECT_ID:
        return jsonify({"error": "Missing table or project"}), 400

    if table in _table_info_cache:
        return jsonify(_table_info_cache[table])

    dataset = _get_dataset(table)
    tier = _get_tier(table)
    entry_path = (
        f"projects/{PROJECT_ID}/locations/us/entryGroups/@bigquery/entries/"
        f"bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/{dataset}/tables/{table}"
    )
    catalog_url = (
        f"https://console.cloud.google.com/dataplex/projects/{PROJECT_ID}/locations/us/"
        f"entryGroups/@bigquery/entries/"
        f"bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/{dataset}/tables/{table}"
        f"?project={PROJECT_ID}"
    )

    try:
        token = _get_token()
        resp = _get_http_session().get(
            f"https://dataplex.googleapis.com/v1/{entry_path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Dataplex lookup failed: status=%d body=%s", resp.status_code, resp.text[:300])
            return jsonify({
                "name": table, "tier": tier, "description": "",
                "column_count": 0, "columns": [], "catalog_url": catalog_url,
            })

        data = resp.json()
        desc = (data.get("entrySource", {}).get("description", "") or "")[:200]
        aspects = data.get("aspects", {})

        schema_data = {}
        for k, v in aspects.items():
            if "schema" in k:
                schema_data = v.get("data", {})
                break

        fields = schema_data.get("fields", [])
        col_names = [f.get("name", "") for f in fields]

        result = {
            "name": table, "tier": tier, "description": desc,
            "column_count": len(fields),
            "columns": col_names[:8],
            "catalog_url": catalog_url,
        }
        _table_info_cache[table] = result
        return jsonify(result)

    except Exception as e:
        logger.exception("table-info error: %s", e)
        return jsonify({
            "name": table, "tier": tier, "description": "",
            "column_count": 0, "columns": [], "catalog_url": catalog_url,
        })


TERM_SLUG_MAP = {
    'FICO Score': 'fico-score', 'AUM': 'aum-abbr', 'SAR': 'sar-abbr',
    'CET1 Ratio': 'cet1-ratio', 'Customer ID': 'customer-id',
    'Delinquency': 'delinquency', 'KYC': 'kyc-abbr', 'VaR': 'var-abbr',
    'CUSIP': 'cusip', 'Branch': 'branch', 'NIM': 'nim-abbr',
    'Risk Rating': 'risk-rating',
}


@app.route("/api/term-info")
def term_info():
    term = request.args.get("term", "")
    if not term or not PROJECT_ID:
        return jsonify({"error": "Missing term or project"}), 400

    if term in _term_info_cache:
        return jsonify(_term_info_cache[term])

    slug = TERM_SLUG_MAP.get(term, term.lower().replace(' ', '-'))
    glossary_path = f"projects/{PROJECT_ID}/locations/us/glossaries/{GLOSSARY_ID}"
    term_path = f"{glossary_path}/terms/{slug}"
    catalog_url = (
        f"https://console.cloud.google.com/dataplex/glossaries/{GLOSSARY_ID}"
        f"/terms/{slug};location=us?project={PROJECT_ID}"
    )

    try:
        token = _get_token()
        resp = _get_http_session().get(
            f"https://dataplex.googleapis.com/v1/{term_path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Glossary term lookup failed: status=%d body=%s", resp.status_code, resp.text[:300])
            return jsonify({
                "term": term, "description": "", "category": "",
                "catalog_url": catalog_url,
            })

        data = resp.json()
        desc = (data.get("description", "") or "")[:200]
        parent = data.get("parent", "")
        category = parent.split("/categories/")[-1].replace("-", " ").title() if "/categories/" in parent else ""

        result = {
            "term": term, "description": desc, "category": category,
            "catalog_url": catalog_url,
        }
        _term_info_cache[term] = result
        return jsonify(result)

    except Exception as e:
        logger.exception("term-info error: %s", e)
        return jsonify({
            "term": term, "description": "", "category": "",
            "catalog_url": catalog_url,
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
                resp = _get_http_session().post(
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
                        if event["type"] in ("tool_call", "tool_response"):
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
