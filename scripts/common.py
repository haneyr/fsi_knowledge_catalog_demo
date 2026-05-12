####################################################################################
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
####################################################################################
"""Shared utilities for FSI data governance post-deploy scripts."""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import google.auth
import google.auth.transport.requests
import requests as http_requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATAPLEX_URL = "https://dataplex.googleapis.com/v1"
BQ_URL = "https://bigquery.googleapis.com/bigquery/v2"
LINEAGE_URL = "https://datalineage.googleapis.com/v1"

TOKEN_REFRESH_SECONDS = 250
_creds_cache: List[Any] = [None, 0]

GLOSSARY_ID = "meridian-national-bank-glossary-us"

# ---------------------------------------------------------------------------
# All FSI medallion tables
# ---------------------------------------------------------------------------

ATLAS_BRONZE: List[Tuple[str, str]] = [
    ("fsi_bronze", "bronze_customers"),
    ("fsi_bronze", "bronze_accounts"),
    ("fsi_bronze", "bronze_transactions"),
    ("fsi_bronze", "bronze_loans"),
    ("fsi_bronze", "bronze_loan_payments"),
    ("fsi_bronze", "bronze_credit_cards"),
    ("fsi_bronze", "bronze_card_transactions"),
    ("fsi_bronze", "bronze_fraud_alerts"),
    ("fsi_bronze", "bronze_kyc_records"),
    ("fsi_bronze", "bronze_branches"),
    ("fsi_bronze", "bronze_employees"),
    ("fsi_bronze", "bronze_wire_transfers"),
    ("fsi_bronze", "bronze_ach_transfers"),
    ("fsi_bronze", "bronze_atm_transactions"),
]

FORTUNA_BRONZE: List[Tuple[str, str]] = [
    ("fsi_bronze", "bronze_wm_clients"),
    ("fsi_bronze", "bronze_portfolios"),
    ("fsi_bronze", "bronze_holdings"),
    ("fsi_bronze", "bronze_trades"),
    ("fsi_bronze", "bronze_securities"),
    ("fsi_bronze", "bronze_advisors"),
    ("fsi_bronze", "bronze_performance"),
    ("fsi_bronze", "bronze_fee_schedules"),
    ("fsi_bronze", "bronze_benchmarks"),
    ("fsi_bronze", "bronze_client_goals"),
    ("fsi_bronze", "bronze_risk_profiles"),
    ("fsi_bronze", "bronze_distributions"),
    ("fsi_bronze", "bronze_custodian_feeds"),
]

ARGUS_BRONZE: List[Tuple[str, str]] = [
    ("fsi_bronze", "bronze_gl_entries"),
    ("fsi_bronze", "bronze_gl_accounts"),
    ("fsi_bronze", "bronze_cost_centers"),
    ("fsi_bronze", "bronze_regulatory_capital"),
    ("fsi_bronze", "bronze_risk_exposures"),
    ("fsi_bronze", "bronze_counterparties"),
    ("fsi_bronze", "bronze_market_data"),
    ("fsi_bronze", "bronze_stress_tests"),
    ("fsi_bronze", "bronze_audit_events"),
    ("fsi_bronze", "bronze_regulatory_filings"),
    ("fsi_bronze", "bronze_interest_rates"),
    ("fsi_bronze", "bronze_fx_rates"),
    ("fsi_bronze", "bronze_compliance_cases"),
]

BRONZE_TABLES = ATLAS_BRONZE + FORTUNA_BRONZE + ARGUS_BRONZE

SILVER_TABLES: List[Tuple[str, str]] = [
    ("fsi_silver", t.replace("bronze_", "silver_")) for _, t in BRONZE_TABLES
]

GOLD_TABLES: List[Tuple[str, str]] = [
    ("fsi_gold", "gold_customer_360"),
    ("fsi_gold", "gold_account_summary"),
    ("fsi_gold", "gold_transaction_patterns"),
    ("fsi_gold", "gold_loan_portfolio_summary"),
    ("fsi_gold", "gold_delinquency_analysis"),
    ("fsi_gold", "gold_fraud_analytics"),
    ("fsi_gold", "gold_aml_risk_scoring"),
    ("fsi_gold", "gold_branch_performance"),
    ("fsi_gold", "gold_portfolio_performance"),
    ("fsi_gold", "gold_client_revenue"),
    ("fsi_gold", "gold_asset_allocation"),
    ("fsi_gold", "gold_advisor_scorecard"),
    ("fsi_gold", "gold_fee_revenue"),
    ("fsi_gold", "gold_net_interest_margin"),
    ("fsi_gold", "gold_capital_adequacy"),
    ("fsi_gold", "gold_liquidity_coverage"),
    ("fsi_gold", "gold_market_risk_var"),
    ("fsi_gold", "gold_operational_risk"),
    ("fsi_gold", "gold_regulatory_dashboard"),
    ("fsi_gold", "gold_balance_sheet_summary"),
]

DASHBOARD_VIEWS: List[Tuple[str, str]] = [
    ("fsi_dashboards", "vw_dq_scorecard"),
    ("fsi_dashboards", "vw_dq_by_dimension"),
    ("fsi_dashboards", "vw_dq_failed_rules"),
    ("fsi_dashboards", "vw_dq_rule_detail"),
    ("fsi_dashboards", "vw_profile_summary"),
    ("fsi_dashboards", "vw_customer_total_relationship"),
    ("fsi_dashboards", "vw_branch_retail_wealth"),
    ("fsi_dashboards", "vw_regulatory_summary"),
]

REFERENCE_TABLES: List[Tuple[str, str]] = [
    ("fsi_reference", "ref_naics_codes"),
    ("fsi_reference", "ref_country_codes"),
    ("fsi_reference", "ref_currency_codes"),
    ("fsi_reference", "ref_cusip_master"),
    ("fsi_reference", "ref_isin_mapping"),
    ("fsi_reference", "ref_lei_registry"),
    ("fsi_reference", "ref_fed_district_codes"),
    ("fsi_reference", "ref_product_catalog"),
    ("fsi_reference", "ref_fee_tiers"),
    ("fsi_reference", "ref_gl_account_hierarchy"),
]

STAGING_TABLES: List[Tuple[str, str]] = [
    ("fsi_staging", "staging_call_report_rc"),
    ("fsi_staging", "staging_call_report_ri"),
    ("fsi_staging", "staging_call_report_rc_r"),
    ("fsi_staging", "staging_call_report_rc_c"),
    ("fsi_staging", "staging_fr_y9c"),
]

SNAPSHOT_TABLES: List[Tuple[str, str]] = [
    ("fsi_snapshots", "snapshot_monthly_balances"),
    ("fsi_snapshots", "snapshot_quarterly_positions"),
    ("fsi_snapshots", "snapshot_daily_market_data"),
]

AUDIT_TABLES: List[Tuple[str, str]] = [
    ("fsi_audit", "audit_data_access_log"),
    ("fsi_audit", "audit_model_decisions"),
]

ALL_TABLES: List[Tuple[str, str]] = (
    BRONZE_TABLES + SILVER_TABLES + GOLD_TABLES
    + DASHBOARD_VIEWS + REFERENCE_TABLES
    + STAGING_TABLES + SNAPSHOT_TABLES + AUDIT_TABLES
)

SCAN_TABLES: List[Tuple[str, str]] = BRONZE_TABLES + SILVER_TABLES + GOLD_TABLES


def scan_id(dataset: str, table: str, scan_type: str) -> str:
    layer = dataset.replace("fsi_", "")
    tname = (table.replace(f"{layer}_", "")
             .replace("bronze_", "")
             .replace("silver_", "")
             .replace("gold_", ""))
    return f"fsi-{layer}-{tname}-{scan_type}".replace("_", "-")


def get_access_token() -> str:
    now = time.time()
    if _creds_cache[0] is None or now - _creds_cache[1] > TOKEN_REFRESH_SECONDS:
        creds, _ = google.auth.default()
        creds.refresh(google.auth.transport.requests.Request())
        _creds_cache[0] = creds.token
        _creds_cache[1] = now
    return _creds_cache[0]


def api_call(
    url: str,
    method: str,
    body: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_access_token()}",
    }
    for attempt in range(max_retries + 1):
        if method == "GET":
            resp = http_requests.get(url, headers=headers)
        elif method == "POST":
            resp = http_requests.post(url, json=body, headers=headers)
        elif method == "PATCH":
            resp = http_requests.patch(url, json=body, headers=headers)
        elif method == "DELETE":
            resp = http_requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if resp.status_code == 429 and attempt < max_retries:
            wait = 2 ** (attempt + 1)
            logger.warning("Rate limited (429). Retrying in %ds...", wait)
            time.sleep(wait)
            continue
        if resp.status_code == 409:
            return {"_exists": True}
        if resp.status_code in (200, 201):
            return resp.json() if resp.text.strip() else {}
        if resp.status_code == 401 and attempt < max_retries:
            _creds_cache[0] = None
            continue
        raise RuntimeError(
            f"API {method} {url} -> {resp.status_code}: {resp.text[:300]}"
        )
    raise RuntimeError(f"API {method} {url} -> exhausted retries")


def poll_operation(op_name: str, timeout: int = 120) -> Dict[str, Any]:
    url = f"{DATAPLEX_URL}/{op_name}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = api_call(url, "GET")
        if result.get("done"):
            if "error" in result:
                raise RuntimeError(f"Operation failed: {result['error']}")
            return result.get("response", result)
        time.sleep(3)
    raise RuntimeError(f"Operation {op_name} timed out")


def run_bq_query(cfg: Dict[str, str], sql: str, description: str = "") -> Dict[str, Any]:
    url = f"{BQ_URL}/projects/{cfg['project_id']}/jobs"
    body = {"configuration": {"query": {"query": sql, "useLegacySql": False}}}
    result = api_call(url, "POST", body)
    job_id = result.get("jobReference", {}).get("jobId", "")
    if description:
        logger.info("  BQ: %s", description)
    deadline = time.time() + 300
    while time.time() < deadline:
        resp = api_call(f"{BQ_URL}/projects/{cfg['project_id']}/jobs/{job_id}", "GET")
        status = resp.get("status", {})
        if status.get("state") == "DONE":
            if "errorResult" in status:
                raise RuntimeError(f"BQ job failed: {status['errorResult']}")
            return resp
        time.sleep(2)
    raise RuntimeError(f"BQ job {job_id} timed out")


def load_config() -> Dict[str, str]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path) as f:
        raw = json.load(f)
    cfg: Dict[str, str] = {}
    for key, val in raw.items():
        if isinstance(val, dict) and "value" in val:
            cfg[key] = val["value"]
        else:
            cfg[key] = val
    if "location" not in cfg:
        cfg["location"] = cfg.get("region", "us-central1")
    if "multi_region" not in cfg:
        cfg["multi_region"] = "us"
    return cfg


def set_entry_aspect(
    cfg: Dict[str, str],
    entry_path: str,
    aspect_type_id: str,
    data: Dict[str, Any],
    is_system: bool = False,
) -> None:
    if is_system:
        aspect_key = f"dataplex-types.global.{aspect_type_id}"
        aspect_type = f"projects/dataplex-types/locations/global/aspectTypes/{aspect_type_id}"
    else:
        aspect_key = f"{cfg['project_id']}.global.{aspect_type_id}"
        aspect_type = f"projects/{cfg['project_id']}/locations/global/aspectTypes/{aspect_type_id}"

    url = (
        f"{DATAPLEX_URL}/{entry_path}"
        f"?updateMask=aspects&deleteMissingAspects=false&aspect_keys={aspect_key}"
    )
    body = {"aspects": {aspect_key: {"aspectType": aspect_type, "data": data}}}
    api_call(url, "PATCH", body)


def glossary_term_entry(
    cfg: Dict[str, str],
    term_id: str,
    glossary_id: str = GLOSSARY_ID,
) -> str:
    pn = cfg["project_number"]
    loc = cfg["multi_region"]
    return (
        f"projects/{pn}/locations/{loc}/entryGroups/@dataplex/entries/"
        f"projects/{pn}/locations/{loc}/glossaries/{glossary_id}/terms/{term_id}"
    )


def bq_table_entry(cfg: Dict[str, str], dataset: str, table: str) -> str:
    pn = cfg["project_number"]
    loc = cfg["multi_region"]
    pid = cfg["project_id"]
    return (
        f"projects/{pn}/locations/{loc}/entryGroups/@bigquery/entries/"
        f"bigquery.googleapis.com/projects/{pid}/datasets/{dataset}/tables/{table}"
    )
