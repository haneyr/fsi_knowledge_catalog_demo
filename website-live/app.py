#!/usr/bin/env python3
"""
[Retail] Northwind Retail Knowledge Catalog Demo — Live WebSocket Web Application

Streams agent responses in real-time via WebSocket, parsing Agent Engine
streamQuery events to drive point cloud animations on the frontend.

Env vars:
    GOOGLE_CLOUD_PROJECT — GCP project ID
    GOOGLE_CLOUD_LOCATION — Agent Engine region (default: us-central1)
    BASIC_AGENT_ID — Agent Engine ID for basic agent
    SCALED_AGENT_ID — Agent Engine ID for scaled agent
    KC_AGENT_ID — Agent Engine ID for KC agent
    OAUTH_CLIENT_ID — Google OAuth 2.0 client ID (optional, enables auth)
"""

import functools
import json
import os
import re
import time
import logging

import google.auth
import google.auth.transport.requests
from google.oauth2 import id_token as google_id_token
import requests as http_requests
from flask import Flask, g, send_from_directory, request, jsonify

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

OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "")
ENVIRONMENT_LABEL = os.environ.get("ENVIRONMENT_LABEL", "demo") or "demo"

AE_BASE = f"https://{LOCATION}-aiplatform.googleapis.com/v1"
_SESSION_TTL = 3600
_sessions = {}
_session_times = {}

_RETAIL_DATASETS = {
    'retail_gold', 'retail_silver', 'retail_bronze',
    'retail_reference', 'retail_staging', 'retail_snapshots',
    'retail_audit', 'retail_dashboards',
}
_DATASET_TO_TIER = {
    'retail_gold': 'gold', 'retail_silver': 'silver', 'retail_bronze': 'bronze',
    'retail_reference': 'ref', 'retail_staging': 'ref', 'retail_snapshots': 'ref',
    'retail_audit': 'ref', 'retail_dashboards': 'ref',
}

BASIC_TABLES = [
    'gold_customer_360', 'gold_loyalty_account_summary', 'gold_bnpl_plan_summary',
    'gold_assortment_performance', 'gold_financial_summary',
]

GOLD_SOURCES = {
    'gold_customer_360': ['silver_customers', 'silver_loyalty_accounts', 'silver_bnpl_plans', 'silver_store_cards', 'silver_vip_members'],
    'gold_loyalty_account_summary': ['silver_loyalty_accounts', 'silver_pos_transactions'],
    'gold_order_patterns': ['silver_pos_transactions'],
    'gold_bnpl_plan_summary': ['silver_bnpl_plans'],
    'gold_bnpl_delinquency_analysis': ['silver_bnpl_plans'],
    'gold_return_fraud_analytics': ['silver_fraud_alerts'],
    'gold_promo_fraud_scoring': ['silver_customers', 'silver_privacy_consents', 'silver_promo_abuse_cases', 'silver_high_value_refunds'],
    'gold_store_performance': ['silver_stores', 'silver_loyalty_accounts', 'silver_bnpl_plans', 'silver_pos_transactions'],
    'gold_assortment_performance': ['silver_merch_assortments', 'silver_assortment_performance', 'silver_inventory_positions', 'silver_category_benchmarks'],
    'gold_vip_member_revenue': ['silver_vip_members', 'silver_promo_rules', 'silver_merch_assortments', 'silver_ecom_orders'],
    'gold_inventory_allocation': ['silver_inventory_positions'],
    'gold_category_manager_scorecard': ['silver_category_managers', 'silver_merch_assortments', 'silver_assortment_performance', 'silver_ecom_orders'],
    'gold_promo_margin_impact': ['silver_promo_rules', 'silver_vip_members'],
    'gold_gross_margin_analysis': ['silver_loyalty_accounts', 'silver_bnpl_plans'],
    'gold_working_capital_adequacy': ['silver_working_capital'],
    'gold_inventory_turnover_coverage': ['silver_loyalty_accounts'],
    'gold_markdown_risk_var': ['silver_inventory_positions', 'silver_competitor_pricing'],
    'gold_shrinkage_operational_risk': ['silver_audit_events'],
    'gold_compliance_dashboard': ['silver_working_capital', 'silver_privacy_consents', 'silver_compliance_attestations'],
    'gold_financial_summary': ['silver_loyalty_accounts', 'silver_bnpl_plans', 'silver_inventory_positions', 'silver_working_capital'],
}

GLOSSARY_LINKS = {
    '[Retail] Return-Risk Score': ['gold_bnpl_plan_summary', 'silver_bnpl_plans', 'bronze_bnpl_plans', 'gold_bnpl_delinquency_analysis'],
    'Return-Risk Score': ['gold_bnpl_plan_summary', 'silver_bnpl_plans', 'bronze_bnpl_plans', 'gold_bnpl_delinquency_analysis'],
    '[Retail] Customer Lifetime Value (CLV)': ['gold_customer_360', 'gold_category_manager_scorecard', 'gold_vip_member_revenue', 'silver_vip_members'],
    'CLV': ['gold_customer_360', 'gold_category_manager_scorecard', 'gold_vip_member_revenue', 'silver_vip_members'],
    '[Retail] Return Abuse Alert': ['gold_return_fraud_analytics', 'gold_promo_fraud_scoring', 'bronze_fraud_alerts', 'bronze_promo_abuse_cases'],
    'Return Abuse Alert': ['gold_return_fraud_analytics', 'gold_promo_fraud_scoring', 'bronze_fraud_alerts', 'bronze_promo_abuse_cases'],
    '[Retail] Working Capital Ratio': ['gold_working_capital_adequacy', 'silver_working_capital', 'bronze_working_capital'],
    'Working Capital Ratio': ['gold_working_capital_adequacy', 'silver_working_capital', 'bronze_working_capital'],
    '[Retail] Customer ID': ['gold_customer_360', 'silver_customers', 'bronze_customers', 'gold_loyalty_account_summary'],
    'Customer ID': ['gold_customer_360', 'silver_customers', 'bronze_customers', 'gold_loyalty_account_summary'],
    '[Retail] BNPL Delinquency Rate': ['gold_bnpl_plan_summary', 'gold_bnpl_delinquency_analysis', 'silver_bnpl_plans'],
    'Delinquency': ['gold_bnpl_plan_summary', 'gold_bnpl_delinquency_analysis', 'silver_bnpl_plans'],
    '[Retail] Marketing Consent & Verification': ['gold_promo_fraud_scoring', 'bronze_privacy_consents', 'gold_customer_360'],
    'Consent Verification': ['gold_promo_fraud_scoring', 'bronze_privacy_consents', 'gold_customer_360'],
    '[Retail] Markdown Value at Risk (VaR)': ['gold_markdown_risk_var', 'silver_inventory_positions', 'silver_competitor_pricing'],
    'VaR': ['gold_markdown_risk_var', 'silver_inventory_positions', 'silver_competitor_pricing'],
    '[Retail] Global Trade Item Number (GTIN-13)': ['silver_product_skus', 'bronze_product_skus', 'gold_inventory_allocation'],
    'GTIN': ['silver_product_skus', 'bronze_product_skus', 'gold_inventory_allocation'],
    '[Retail] Store ID': ['gold_store_performance', 'gold_customer_360', 'bronze_stores', 'gold_gross_margin_analysis'],
    'Store': ['gold_store_performance', 'gold_customer_360', 'bronze_stores', 'gold_gross_margin_analysis'],
    '[Retail] Gross Margin Percentage': ['gold_gross_margin_analysis', 'silver_loyalty_accounts', 'silver_bnpl_plans'],
    'Gross Margin': ['gold_gross_margin_analysis', 'silver_loyalty_accounts', 'silver_bnpl_plans'],
    '[Retail] Return Risk Tier': ['gold_bnpl_plan_summary', 'silver_bnpl_plans', 'bronze_bnpl_plans'],
    'Risk Rating': ['gold_bnpl_plan_summary', 'silver_bnpl_plans', 'bronze_bnpl_plans'],
}

# Discovered state — populated at startup by _discover_*() functions
_TABLES_BY_TIER = {}
_TABLE_DATASET = {}
ALL_TABLE_NAMES = []
GLOSSARY_TERM_MAP = {}
TERM_SLUG_MAP = {}


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


def _get_or_create_session(agent_id, user_id, category="merchandising"):
    cat_key = (category or "merchandising").strip().lower()
    key = f"{agent_id}:{user_id}:{cat_key}"
    if key in _sessions:
        if time.time() - _session_times.get(key, 0) < _SESSION_TTL:
            return _sessions[key]
        del _sessions[key]
        del _session_times[key]

    try:
        token = _get_token()
        url = f"{_ae_url(agent_id)}:query"
        logger.info("Creating session: POST %s for user=%s category=%s", url, user_id, cat_key)
        resp = _get_http_session().post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"class_method": "async_create_session", "input": {"user_id": user_id}},
            timeout=30,
        )
        logger.info("Session response: status=%d body=%s", resp.status_code, resp.text[:500])
        if resp.status_code == 200:
            output = resp.json().get("output", {})
            session_id = output.get("id", "") if type(output) is dict else str(output)
            _sessions[key] = session_id
            _session_times[key] = time.time()
            return session_id
        return None
    except Exception as e:
        logger.exception("Failed to create session: %s", e)
        return None


_INTERNAL_SCOPE_INSTRUCTION = (
    "\n\n[MANDATORY SCOPE GATE — INTERNAL BIGQUERY ONLY]\n"
    "Active UI Tab: INTERNAL (Merchandising / Customer / Privacy).\n"
    "Strict rules for this turn:\n"
    "1. Do NOT call `query_snowflake`.\n"
    "2. Do NOT search for or pass any `retail-nexus-market-intel` or `nexus_*` entry in `search_entries` or `lookup_context`.\n"
    "3. Use ONLY internal BigQuery tables (`retail_gold.*`, `retail_silver.*`, `retail_bronze.*`, `retail_reference.*`).\n"
    "4. Do NOT output the words `NEXUS`, `Snowflake`, `SYNDICATED_INTEL`, `Third-Party Licensed`, `Vendor Data License`, `#NWR-NEXUS-2026`, or `external market data` anywhere in your response (not even in negative disclaimers). In **Governance Context.**, cite only internal source systems (`ORION`, `LUMEN`, `HELIOS`) and internal sensitivity classifications (`Internal`, `Confidential`, `Restricted` under `PCI-DSS` / `CCPA`)."
)

_CROSS_CLOUD_SCOPE_INSTRUCTION = (
    "\n\n[MANDATORY SCOPE GATE — CROSS-CLOUD TAB]\n"
    "Active UI Tab: CROSS-CLOUD.\n"
    "Strict rules for this turn:\n"
    "1. You MUST invoke BOTH the `query_snowflake` tool (against at least one `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_*` table such as `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES`) AND the `run_sql` tool (against internal BigQuery tables) BEFORE generating your text response. Never skip calling `query_snowflake` or `run_sql`.\n"
    "2. In `lookup_context`, you MUST inspect the corresponding NEXUS entry (`projects/alitch-ca-demo/locations/us/entryGroups/retail-nexus-market-intel/entries/nexus_*`) alongside at least one Bronze (`bronze_product_skus`), one Silver (`silver_product_skus` or `silver_inventory_positions`), and one Gold (`gold_inventory_allocation`) BigQuery table. Do NOT use internal `bronze_competitor_pricing` or `silver_competitor_pricing`.\n"
    "3. Cite the `nexus_*` asset in **Data discovery.** and **Governance Context.** (including `NEXUS`, `Snowflake`, `Third-Party Licensed`, and `Vendor Data License #NWR-NEXUS-2026`)."
)

_CROSS_CLOUD_EXCLUDED_INTERNAL = {
    "bronze_competitor_pricing",
    "silver_competitor_pricing",
    "snapshot_daily_competitor_pricing",
}


def _is_cross_cloud_category(category):
    return str(category or "").strip().lower() in ("multicloud", "cross-cloud", "cross_cloud")


def _build_scoped_question(agent_type, question, category):
    if agent_type != "kc":
        return question
    if _is_cross_cloud_category(category):
        return f"{question}{_CROSS_CLOUD_SCOPE_INSTRUCTION}"
    return f"{question}{_INTERNAL_SCOPE_INSTRUCTION}"


def _extract_tables(text, is_cross_cloud=False):
    lower = text.lower()
    if is_cross_cloud:
        candidates = [
            t for t in (ALL_TABLE_NAMES + _SNOWFLAKE_TABLES)
            if t not in _CROSS_CLOUD_EXCLUDED_INTERNAL
        ]
    else:
        candidates = ALL_TABLE_NAMES
    return [t for t in candidates if t in lower]


def _extract_glossary_terms(text):
    terms = set()
    lower = text.lower()
    for keyword, term_list in GLOSSARY_TERM_MAP.items():
        if keyword in lower:
            terms.update(term_list)
    return list(terms)


def _iter_stream_lines(resp):
    """Yield newline-delimited JSON chunks immediately as HTTP chunks arrive."""
    buf = b""
    for chunk in resp.raw.stream(65536, decode_content=True):
        if not chunk:
            continue
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.strip()
            if line:
                yield line.decode("utf-8", errors="replace")
    if buf.strip():
        yield buf.strip().decode("utf-8", errors="replace")


def _parse_stream_chunk(raw_text, is_cross_cloud=False, sse_mode=False):
    """Parse a single streamQuery response line into typed events."""
    events = []
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return events

    is_partial = bool(data.get("partial"))
    content = data.get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        if "function_call" in part:
            # In ADK SSE mode, function_call is emitted twice (partial=True then partial=False).
            # Emit tool_call only on the finalized event to avoid duplicate tool chips.
            if is_partial:
                continue
            fc = part["function_call"]
            args = fc.get("args", {})
            args_text = str(args)
            events.append({
                "type": "tool_call",
                "name": fc.get("name", ""),
                "args": args,
                "tables": _extract_tables(args_text, is_cross_cloud=is_cross_cloud),
            })
        elif "function_response" in part:
            fr = part["function_response"]
            resp_data = fr.get("response", {})
            result_text = resp_data.get("result", str(resp_data))
            tables = _extract_tables(result_text, is_cross_cloud=is_cross_cloud)
            glossary = _extract_glossary_terms(result_text)
            events.append({
                "type": "tool_response",
                "name": fr.get("name", ""),
                "tables": tables,
                "glossary_terms": glossary,
            })
        elif "text" in part and part["text"] and not part.get("thought"):
            # In ADK SSE mode, all tokens stream as partial=True and partial=False is the
            # turn-end aggregate duplicate saved to the session.
            if sse_mode and not is_partial:
                continue
            events.append({
                "type": "text_chunk",
                "text": part["text"],
            })

    return events


# ---- Auth ----

_auth_request = google.auth.transport.requests.Request()


def _verify_id_token(token):
    if not token:
        return None
    try:
        idinfo = google_id_token.verify_oauth2_token(
            token, _auth_request, OAUTH_CLIENT_ID
        )
        return {
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
        }
    except Exception:
        return None


def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not OAUTH_CLIENT_ID:
            return jsonify({"error": "OAuth not configured. Set OAUTH_CLIENT_ID."}), 503
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = _verify_id_token(token)
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        g.user = user
        return f(*args, **kwargs)
    return wrapper


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
        "project_number": _get_project_number(),
        "oauth_client_id": OAUTH_CLIENT_ID,
        "live_mode": any(AGENT_IDS.values()),
        "agents": {k: bool(v) for k, v in AGENT_IDS.items()},
        "snowflake_enabled": bool(_SNOWFLAKE_TABLES),
        "snowflake_live": bool(os.environ.get("SNOWFLAKE_ACCOUNT")),
        "snowflake_tables": _SNOWFLAKE_TABLES,
        "environment": ENVIRONMENT_LABEL,
        "tables": _TABLES_BY_TIER,
        "all_table_names": ALL_TABLE_NAMES,
        "basic_tables": BASIC_TABLES,
        "gold_sources": GOLD_SOURCES,
        "glossary_terms": TERM_SLUG_MAP,
        "glossary_links": GLOSSARY_LINKS,
        "dataset_map": DATASET_MAP,
    })


@app.route("/api/reset-session", methods=["POST"])
def reset_session():
    data = request.get_json(silent=True) or {}
    agent_type = data.get("agent", "")
    agent_id = AGENT_IDS.get(agent_type, "")
    if not agent_id:
        return jsonify({"error": f"Unknown agent: {agent_type}"}), 400

    if OAUTH_CLIENT_ID:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user = _verify_id_token(token)
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        user_id = user["email"]
    else:
        return jsonify({"status": "ok"})

    prefix = f"{agent_id}:{user_id}"
    for k in [k for k in list(_sessions.keys()) if k == prefix or k.startswith(f"{prefix}:")]:
        _sessions.pop(k, None)
        _session_times.pop(k, None)
    logger.info("Reset session prefix: %s", prefix)
    return jsonify({"status": "ok"})


DATASET_MAP = {
    'gold_': 'retail_gold', 'silver_': 'retail_silver', 'bronze_': 'retail_bronze',
    'ref_': 'retail_reference', 'staging_': 'retail_staging',
    'snapshot_': 'retail_snapshots', 'audit_': 'retail_audit',
    'vw_': 'retail_dashboards',
}

_table_info_cache = {}
_term_info_cache = {}

GLOSSARY_ID = os.environ.get("GLOSSARY_ID", "retail-northwind-glossary-us")

_SNOWFLAKE_TABLES = []
_SNOWFLAKE_SCHEMA_MAP = {}
_SNOWFLAKE_ENTRY_MAP = {}
_NEXUS_ENTRY_GROUP = "retail-nexus-market-intel"
_DEFAULT_NEXUS_TABLES = [
    "nexus_competitor_prices",
    "nexus_category_market_share",
    "nexus_consumer_panel",
    "nexus_regional_demand_index",
    "nexus_promo_calendar_benchmark",
    "nexus_basket_affinity",
]


def _discover_snowflake_tables():
    global _SNOWFLAKE_TABLES, _SNOWFLAKE_SCHEMA_MAP, _SNOWFLAKE_ENTRY_MAP
    if _SNOWFLAKE_TABLES:
        return
    if not PROJECT_ID:
        for t in _DEFAULT_NEXUS_TABLES:
            _SNOWFLAKE_TABLES.append(t)
            _SNOWFLAKE_SCHEMA_MAP[t] = "syndicated_intel"
            _SNOWFLAKE_ENTRY_MAP[t] = t
        return
    try:
        token = _get_token()
        base_url = f"https://dataplex.googleapis.com/v1/projects/{PROJECT_ID}/locations/us/entryGroups/{_NEXUS_ENTRY_GROUP}/entries"
        page_token = None
        while True:
            url = base_url + (f"?pageToken={page_token}" if page_token else "")
            resp = _get_http_session().get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
            if resp.status_code != 200:
                logger.warning("Snowflake table discovery failed: %d", resp.status_code)
                break
            data = resp.json()
            for entry in data.get("entries", []):
                fqn = entry.get("fullyQualifiedName", "")
                entry_type = entry.get("entryType", "")
                entry_name = entry.get("name", "")
                entry_id = entry_name.rsplit("/", 1)[-1] if "/" in entry_name else ""
                if "snowflake-table" not in entry_type:
                    continue
                parts = fqn.split(".")
                if len(parts) >= 4:
                    schema = parts[-2].lower()
                    table = parts[-1].lower()
                else:
                    schema = "syndicated_intel"
                    table = entry_id.lower()
                if table and table not in _SNOWFLAKE_SCHEMA_MAP:
                    _SNOWFLAKE_TABLES.append(table)
                    _SNOWFLAKE_SCHEMA_MAP[table] = schema
                    _SNOWFLAKE_ENTRY_MAP[table] = entry_id or table
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        logger.warning("Snowflake table discovery error: %s", e)

    if not _SNOWFLAKE_TABLES:
        for t in _DEFAULT_NEXUS_TABLES:
            _SNOWFLAKE_TABLES.append(t)
            _SNOWFLAKE_SCHEMA_MAP[t] = "syndicated_intel"
            _SNOWFLAKE_ENTRY_MAP[t] = t

    _SNOWFLAKE_TABLES.sort()
    logger.info("Discovered %d Snowflake NEXUS tables: %s", len(_SNOWFLAKE_TABLES), _SNOWFLAKE_TABLES)


def _discover_bigquery_tables():
    global _TABLES_BY_TIER, _TABLE_DATASET
    if _TABLES_BY_TIER:
        return
    if not PROJECT_ID:
        return
    try:
        token = _get_token()
        base_url = f"https://dataplex.googleapis.com/v1/projects/{PROJECT_ID}/locations/us/entryGroups/@bigquery/entries"
        tables_by_tier = {'bronze': [], 'silver': [], 'gold': [], 'ref': []}
        table_dataset = {}
        page_token = None
        while True:
            params = {'pageSize': '500'}
            if page_token:
                params['pageToken'] = page_token
            resp = _get_http_session().get(
                base_url, params=params,
                headers={"Authorization": f"Bearer {token}"}, timeout=30,
            )
            if resp.status_code != 200:
                logger.warning("BigQuery table discovery failed: %d %s", resp.status_code, resp.text[:300])
                return
            data = resp.json()
            for entry in data.get("entries", []):
                name = entry.get("name", "")
                match = re.search(r'/datasets/([^/]+)/tables/([^/]+)$', name)
                if not match:
                    continue
                dataset = match.group(1)
                table = match.group(2)
                if dataset not in _RETAIL_DATASETS or table == "nexus_connector_data":
                    continue
                tier = _DATASET_TO_TIER.get(dataset, 'ref')
                tables_by_tier[tier].append(table)
                table_dataset[table] = dataset
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        for tier in tables_by_tier:
            tables_by_tier[tier].sort()
        _TABLES_BY_TIER = tables_by_tier
        _TABLE_DATASET = table_dataset
        ALL_TABLE_NAMES.clear()
        for tier_tables in tables_by_tier.values():
            ALL_TABLE_NAMES.extend(tier_tables)
        logger.info("Discovered %d BigQuery tables: %s",
                     len(ALL_TABLE_NAMES),
                     {k: len(v) for k, v in tables_by_tier.items()})
    except Exception as e:
        logger.warning("BigQuery table discovery error: %s", e)


def _discover_glossary():
    if GLOSSARY_TERM_MAP:
        return
    if not PROJECT_ID:
        return
    try:
        token = _get_token()
        base_url = f"https://dataplex.googleapis.com/v1/projects/{PROJECT_ID}/locations/us/glossaries/{GLOSSARY_ID}/terms"
        terms = {}
        page_token = None
        while True:
            params = {'pageSize': '500'}
            if page_token:
                params['pageToken'] = page_token
            resp = _get_http_session().get(
                base_url, params=params,
                headers={"Authorization": f"Bearer {token}"}, timeout=15,
            )
            if resp.status_code != 200:
                logger.warning("Glossary discovery failed: %d %s", resp.status_code, resp.text[:300])
                return
            data = resp.json()
            for term in data.get("terms", []):
                display_name = term.get("displayName", "")
                if not display_name:
                    continue
                name = term.get("name", "")
                slug = name.rsplit("/", 1)[-1] if "/" in name else ""
                terms[display_name] = slug
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        if terms:
            TERM_SLUG_MAP.clear()
            TERM_SLUG_MAP.update(terms)
            GLOSSARY_TERM_MAP.clear()
            GLOSSARY_TERM_MAP['search_entries'] = []
            for display_name in terms:
                lower = display_name.lower()
                GLOSSARY_TERM_MAP[lower] = [display_name]
                clean = lower.replace('[retail] ', '').strip()
                if clean:
                    GLOSSARY_TERM_MAP[clean] = [display_name]
                    words = clean.split()
                    if len(words) > 1 and len(words[0]) >= 3:
                        existing = GLOSSARY_TERM_MAP.get(words[0], [])
                        if display_name not in existing:
                            GLOSSARY_TERM_MAP[words[0]] = existing + [display_name]
            logger.info("Discovered %d glossary terms: %s", len(terms), list(terms.keys()))
    except Exception as e:
        logger.warning("Glossary discovery error: %s", e)


# Run discovery at import time for production (gunicorn/Cloud Run)
try:
    _discover_bigquery_tables()
    _discover_glossary()
    _discover_snowflake_tables()
except Exception:
    pass


def _get_dataset(table_name):
    if table_name in _TABLE_DATASET:
        return _TABLE_DATASET[table_name]
    if table_name in _SNOWFLAKE_SCHEMA_MAP:
        return 'snowflake'
    for prefix, ds in DATASET_MAP.items():
        if table_name.startswith(prefix):
            return ds
    return 'retail_gold'


def _get_tier(table_name):
    if table_name in _SNOWFLAKE_SCHEMA_MAP:
        return 'snowflake'
    for tier, tables in _TABLES_BY_TIER.items():
        if table_name in tables:
            return tier
    for prefix in ('gold_', 'silver_', 'bronze_', 'ref_', 'staging_', 'snapshot_', 'audit_', 'vw_'):
        if table_name.startswith(prefix):
            return prefix.rstrip('_')
    return 'other'


@app.route("/api/table-info")
@login_required
def table_info():
    table = request.args.get("table", "")
    if not table or not PROJECT_ID:
        return jsonify({"error": "Missing table or project"}), 400

    if table in _table_info_cache:
        return jsonify(_table_info_cache[table])

    dataset = _get_dataset(table)
    tier = _get_tier(table)

    if tier == 'snowflake':
        entry_id = _SNOWFLAKE_ENTRY_MAP.get(table, table)
        entry_path = f"projects/{PROJECT_ID}/locations/us/entryGroups/{_NEXUS_ENTRY_GROUP}/entries/{entry_id}"
        catalog_url = (
            f"https://console.cloud.google.com/dataplex/dp-entries/projects/{PROJECT_ID}/locations/us/"
            f"entryGroups/{_NEXUS_ENTRY_GROUP}/entries/{entry_id}?project={PROJECT_ID}"
        )
        fallback_url = (
            f"https://console.cloud.google.com/dataplex/dp-entries/projects/{PROJECT_ID}/locations/us/"
            f"entryGroups/{_NEXUS_ENTRY_GROUP}?project={PROJECT_ID}"
        )
        try:
            token = _get_token()
            resp = _get_http_session().get(
                f"https://dataplex.googleapis.com/v1/{entry_path}?view=ALL",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code != 200:
                result = {
                    "name": table, "tier": tier, "description": "Metadata not available",
                    "column_count": 0, "columns": [], "catalog_url": fallback_url,
                }
                _table_info_cache[table] = result
                return jsonify(result)

            data = resp.json()
            desc = (data.get("entrySource", {}).get("description", "") or "Metadata not available")[:200]
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
            logger.exception("Snowflake table-info error: %s", e)
            result = {
                "name": table, "tier": tier, "description": "Metadata not available",
                "column_count": 0, "columns": [], "catalog_url": fallback_url,
            }
            return jsonify(result)

    entry_path = (
        f"projects/{PROJECT_ID}/locations/us/entryGroups/@bigquery/entries/"
        f"bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/{dataset}/tables/{table}"
    )
    catalog_url = (
        f"https://console.cloud.google.com/dataplex/dp-entries/projects/{PROJECT_ID}/locations/us/"
        f"entryGroups/@bigquery/entries/"
        f"bigquery.googleapis.com%2Fprojects%2F{PROJECT_ID}%2Fdatasets%2F{dataset}%2Ftables%2F{table}"
        f"?project={PROJECT_ID}"
    )
    bq_url = (
        f"https://console.cloud.google.com/bigquery?referrer=search"
        f"&project={PROJECT_ID}&ws=!1m5!1m4!4m3!1s{PROJECT_ID}!2s{dataset}!3s{table}"
    )

    try:
        token = _get_token()
        resp = _get_http_session().get(
            f"https://dataplex.googleapis.com/v1/{entry_path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Knowledge Catalog lookup failed: status=%d body=%s", resp.status_code, resp.text[:300])
            return jsonify({
                "name": table, "tier": tier, "description": "",
                "column_count": 0, "columns": [], "catalog_url": catalog_url, "bq_url": bq_url,
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
            "catalog_url": catalog_url, "bq_url": bq_url,
        }
        _table_info_cache[table] = result
        return jsonify(result)

    except Exception as e:
        logger.exception("table-info error: %s", e)
        return jsonify({
            "name": table, "tier": tier, "description": "",
            "column_count": 0, "columns": [], "catalog_url": catalog_url, "bq_url": bq_url,
        })




@app.route("/api/term-info")
@login_required
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
        f"https://console.cloud.google.com/dataplex/dp-glossaries/projects/{PROJECT_ID}"
        f"/locations/us/glossaries/{GLOSSARY_ID}/terms/{slug}?project={PROJECT_ID}"
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
        if OAUTH_CLIENT_ID:
            token = request.args.get("token", "")
            user = _verify_id_token(token)
            if not user:
                ws.send(json.dumps({"type": "error", "message": "Authentication required"}))
                return
            user_id = user["email"]
        else:
            user_id = f"ws_user_{id(ws)}"

        while True:
            raw = ws.receive()
            if raw is None:
                break

            msg = json.loads(raw)
            agent_type = msg.get("agent", "basic")
            question = msg.get("question", "")
            category = msg.get("category", "merchandising")
            is_cross_cloud = _is_cross_cloud_category(category)
            scoped_question = _build_scoped_question(agent_type, question, category)
            agent_id = AGENT_IDS.get(agent_type, "")

            if not agent_id:
                ws.send(json.dumps({"type": "error", "message": f"No {agent_type} agent configured"}))
                continue

            start = time.time()
            t0 = time.perf_counter()
            ws.send(json.dumps({"type": "status", "message": "Connecting to agent..."}))

            try:
                t_sess_start = time.perf_counter()
                session_id = _get_or_create_session(agent_id, user_id, category=category)
                session_create_ms = round((time.perf_counter() - t_sess_start) * 1000)
                elapsed_ms = round((time.perf_counter() - t0) * 1000)
                logger.info(
                    "[LATENCY] agent=%s category=%s phase=session_create phase_ms=%d elapsed_ms=%d",
                    agent_type, category, session_create_ms, elapsed_ms,
                )
                if not session_id:
                    ws.send(json.dumps({"type": "error", "message": "Failed to create session"}))
                    continue

                token = _get_token()
                stream_input = {
                    "message": scoped_question,
                    "user_id": user_id,
                    "session_id": session_id,
                }
                if agent_type == "kc":
                    stream_input["run_config"] = {"streaming_mode": "sse"}
                resp = _get_http_session().post(
                    f"{_ae_url(agent_id)}:streamQuery",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "class_method": "async_stream_query",
                        "input": stream_input,
                    },
                    stream=True,
                    timeout=300,
                )

                if resp.status_code != 200:
                    logger.error("streamQuery failed: agent=%s status=%d body=%s", agent_type, resp.status_code, resp.text[:500])
                    ws.send(json.dumps({"type": "error", "message": f"Agent returned {resp.status_code}"}))
                    continue

                all_tables = []
                all_glossary = []
                phase_timings = [{"phase": "session_create", "phase_ms": session_create_ms, "elapsed_ms": elapsed_ms}]
                last_phase_t = time.perf_counter()
                pending_tool_t = {}
                first_token_ms = None
                last_token_ms = None
                sse_mode = (agent_type == "kc")

                for text in _iter_stream_lines(resp):
                    events = _parse_stream_chunk(text, is_cross_cloud=is_cross_cloud, sse_mode=sse_mode)
                    for event in events:
                        now = time.perf_counter()
                        elapsed_ms = round((now - t0) * 1000)
                        event["elapsed_ms"] = elapsed_ms
                        etype = event["type"]

                        if etype == "tool_call":
                            tname = event.get("name", "")
                            step_ms = round((now - last_phase_t) * 1000)
                            pending_tool_t[tname] = now
                            last_phase_t = now
                            phase_timings.append({
                                "phase": f"tool_call:{tname}",
                                "phase_ms": step_ms,
                                "elapsed_ms": elapsed_ms,
                            })
                            logger.info(
                                "[LATENCY] agent=%s category=%s phase=tool_call:%s phase_ms=%d elapsed_ms=%d",
                                agent_type, category, tname, step_ms, elapsed_ms,
                            )
                            all_tables.extend(event.get("tables", []))
                            all_glossary.extend(event.get("glossary_terms", []))

                        elif etype == "tool_response":
                            tname = event.get("name", "")
                            t_call = pending_tool_t.pop(tname, last_phase_t)
                            exec_ms = round((now - t_call) * 1000)
                            last_phase_t = now
                            event["tool_exec_ms"] = exec_ms
                            phase_timings.append({
                                "phase": f"tool_response:{tname}",
                                "phase_ms": exec_ms,
                                "elapsed_ms": elapsed_ms,
                            })
                            logger.info(
                                "[LATENCY] agent=%s category=%s phase=tool_response:%s phase_ms=%d elapsed_ms=%d",
                                agent_type, category, tname, exec_ms, elapsed_ms,
                            )
                            all_tables.extend(event.get("tables", []))
                            all_glossary.extend(event.get("glossary_terms", []))

                        elif etype == "text_chunk":
                            if first_token_ms is None:
                                first_token_ms = elapsed_ms
                                gen_ms = round((now - last_phase_t) * 1000)
                                phase_timings.append({
                                    "phase": "first_token",
                                    "phase_ms": gen_ms,
                                    "elapsed_ms": first_token_ms,
                                })
                                logger.info(
                                    "[LATENCY] agent=%s category=%s phase=first_token phase_ms=%d elapsed_ms=%d",
                                    agent_type, category, gen_ms, first_token_ms,
                                )
                            last_token_ms = elapsed_ms
                            last_phase_t = now

                        ws.send(json.dumps(event))

                if last_token_ms is not None:
                    stream_ms = last_token_ms - (first_token_ms or last_token_ms)
                    phase_timings.append({
                        "phase": "last_token",
                        "phase_ms": stream_ms,
                        "elapsed_ms": last_token_ms,
                    })
                    logger.info(
                        "[LATENCY] agent=%s category=%s phase=last_token phase_ms=%d elapsed_ms=%d",
                        agent_type, category, stream_ms, last_token_ms,
                    )

                latency = time.time() - start
                total_ms = round((time.perf_counter() - t0) * 1000)
                logger.info(
                    "[LATENCY_SUMMARY] agent=%s category=%s total_ms=%d phases=%s",
                    agent_type, category, total_ms, json.dumps(phase_timings),
                )
                ws.send(json.dumps({
                    "type": "done",
                    "latency": round(latency, 1),
                    "total_ms": total_ms,
                    "phase_timings": phase_timings,
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
    _discover_bigquery_tables()
    _discover_glossary()
    _discover_snowflake_tables()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
