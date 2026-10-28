#!/usr/bin/env python3
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
"""Shared utilities for Retail data governance post-deploy scripts."""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE", "false")

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

GLOSSARY_ID = "retail-northwind-glossary-us"

# ---------------------------------------------------------------------------
# All Retail medallion tables
# ---------------------------------------------------------------------------

ORION_BRONZE: List[Tuple[str, str]] = [
    ("retail_bronze", "bronze_customers"),
    ("retail_bronze", "bronze_loyalty_accounts"),
    ("retail_bronze", "bronze_pos_transactions"),
    ("retail_bronze", "bronze_bnpl_plans"),
    ("retail_bronze", "bronze_bnpl_payments"),
    ("retail_bronze", "bronze_store_cards"),
    ("retail_bronze", "bronze_payment_tenders"),
    ("retail_bronze", "bronze_fraud_alerts"),
    ("retail_bronze", "bronze_privacy_consents"),
    ("retail_bronze", "bronze_stores"),
    ("retail_bronze", "bronze_store_associates"),
    ("retail_bronze", "bronze_high_value_refunds"),
    ("retail_bronze", "bronze_vendor_settlements"),
    ("retail_bronze", "bronze_kiosk_transactions"),
]

LUMEN_BRONZE: List[Tuple[str, str]] = [
    ("retail_bronze", "bronze_vip_members"),
    ("retail_bronze", "bronze_merch_assortments"),
    ("retail_bronze", "bronze_inventory_positions"),
    ("retail_bronze", "bronze_ecom_orders"),
    ("retail_bronze", "bronze_product_skus"),
    ("retail_bronze", "bronze_category_managers"),
    ("retail_bronze", "bronze_assortment_performance"),
    ("retail_bronze", "bronze_promo_rules"),
    ("retail_bronze", "bronze_category_benchmarks"),
    ("retail_bronze", "bronze_customer_preferences"),
    ("retail_bronze", "bronze_return_risk_profiles"),
    ("retail_bronze", "bronze_reward_redemptions"),
    ("retail_bronze", "bronze_carrier_feeds"),
]

HELIOS_BRONZE: List[Tuple[str, str]] = [
    ("retail_bronze", "bronze_gl_entries"),
    ("retail_bronze", "bronze_gl_accounts"),
    ("retail_bronze", "bronze_cost_centers"),
    ("retail_bronze", "bronze_working_capital"),
    ("retail_bronze", "bronze_shrinkage_exposures"),
    ("retail_bronze", "bronze_suppliers"),
    ("retail_bronze", "bronze_competitor_pricing"),
    ("retail_bronze", "bronze_demand_scenarios"),
    ("retail_bronze", "bronze_audit_events"),
    ("retail_bronze", "bronze_compliance_attestations"),
    ("retail_bronze", "bronze_markdown_rates"),
    ("retail_bronze", "bronze_fx_rates"),
    ("retail_bronze", "bronze_promo_abuse_cases"),
]

BRONZE_TABLES = ORION_BRONZE + LUMEN_BRONZE + HELIOS_BRONZE

SILVER_TABLES: List[Tuple[str, str]] = [
    ("retail_silver", t.replace("bronze_", "silver_")) for _, t in BRONZE_TABLES
]

GOLD_TABLES: List[Tuple[str, str]] = [
    ("retail_gold", "gold_customer_360"),
    ("retail_gold", "gold_loyalty_account_summary"),
    ("retail_gold", "gold_order_patterns"),
    ("retail_gold", "gold_bnpl_plan_summary"),
    ("retail_gold", "gold_bnpl_delinquency_analysis"),
    ("retail_gold", "gold_return_fraud_analytics"),
    ("retail_gold", "gold_promo_fraud_scoring"),
    ("retail_gold", "gold_store_performance"),
    ("retail_gold", "gold_assortment_performance"),
    ("retail_gold", "gold_vip_member_revenue"),
    ("retail_gold", "gold_inventory_allocation"),
    ("retail_gold", "gold_category_manager_scorecard"),
    ("retail_gold", "gold_promo_margin_impact"),
    ("retail_gold", "gold_gross_margin_analysis"),
    ("retail_gold", "gold_working_capital_adequacy"),
    ("retail_gold", "gold_inventory_turnover_coverage"),
    ("retail_gold", "gold_markdown_risk_var"),
    ("retail_gold", "gold_shrinkage_operational_risk"),
    ("retail_gold", "gold_compliance_dashboard"),
    ("retail_gold", "gold_financial_summary"),
]

DASHBOARD_VIEWS: List[Tuple[str, str]] = [
    ("retail_dashboards", "vw_dq_scorecard"),
    ("retail_dashboards", "vw_dq_by_dimension"),
    ("retail_dashboards", "vw_dq_failed_rules"),
    ("retail_dashboards", "vw_dq_rule_detail"),
    ("retail_dashboards", "vw_profile_summary"),
    ("retail_dashboards", "vw_customer_lifetime_value"),
    ("retail_dashboards", "vw_store_omnichannel_performance"),
    ("retail_dashboards", "vw_compliance_summary"),
]

REFERENCE_TABLES: List[Tuple[str, str]] = [
    ("retail_reference", "ref_merch_category_codes"),
    ("retail_reference", "ref_country_codes"),
    ("retail_reference", "ref_currency_codes"),
    ("retail_reference", "ref_gtin_master"),
    ("retail_reference", "ref_sku_gtin_mapping"),
    ("retail_reference", "ref_supplier_registry"),
    ("retail_reference", "ref_sales_region_codes"),
    ("retail_reference", "ref_product_catalog"),
    ("retail_reference", "ref_loyalty_tiers"),
    ("retail_reference", "ref_gl_account_hierarchy"),
]

STAGING_TABLES: List[Tuple[str, str]] = [
    ("retail_staging", "staging_pci_aoc_summary"),
    ("retail_staging", "staging_channel_revenue_recon"),
    ("retail_staging", "staging_supplier_audit_schedule"),
    ("retail_staging", "staging_ccpa_dsar_log"),
    ("retail_staging", "staging_annual_omniretail_filing"),
]

SNAPSHOT_TABLES: List[Tuple[str, str]] = [
    ("retail_snapshots", "snapshot_monthly_loyalty_balances"),
    ("retail_snapshots", "snapshot_quarterly_inventory_positions"),
    ("retail_snapshots", "snapshot_daily_competitor_pricing"),
]

AUDIT_TABLES: List[Tuple[str, str]] = [
    ("retail_audit", "audit_data_access_log"),
    ("retail_audit", "audit_model_decisions"),
]

ALL_TABLES: List[Tuple[str, str]] = (
    BRONZE_TABLES + SILVER_TABLES + GOLD_TABLES
    + DASHBOARD_VIEWS + REFERENCE_TABLES
    + STAGING_TABLES + SNAPSHOT_TABLES + AUDIT_TABLES
)

SCAN_TABLES: List[Tuple[str, str]] = BRONZE_TABLES + SILVER_TABLES + GOLD_TABLES

SCAN_DATASETS: List[str] = [
    "retail_bronze", "retail_silver", "retail_gold", "retail_reference",
    "retail_staging", "retail_snapshots", "retail_dashboards", "retail_audit",
]


def scan_id(dataset: str, table: str, scan_type: str) -> str:
    layer = dataset.replace("retail_", "")
    tname = (table.replace(f"{layer}_", "")
             .replace("bronze_", "")
             .replace("silver_", "")
             .replace("gold_", "")
             .replace("snapshot_", ""))
    return f"retail-{layer}-{tname}-{scan_type}".replace("_", "-")[:63].rstrip("-")


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
        if type(val) is dict and "value" in val:
            cfg[key] = val["value"]
        else:
            cfg[key] = val
    if "location" not in cfg:
        cfg["location"] = cfg.get("region", "us-central1")
    if "multi_region" not in cfg:
        cfg["multi_region"] = "us"
    return cfg


def entry_group_location(cfg: Dict[str, str]) -> str:
    """Location for user-created entry groups and source entries (issue #20).

    These must live in the same region as the glossary and BigQuery entries
    (the multi-region, e.g. ``us``) so that entry-to-glossary-term links and
    other cross-resource references resolve. This is the single source of
    truth for that decision.
    """
    return cfg["multi_region"]


def entry_type_location(cfg: Dict[str, str]) -> str:
    """Location for entry types and aspect types (issue #20).

    Types live in ``global``. Knowledge Catalog requires an entry's entry type to be in
    the same region as the entry, in a corresponding multi-region, or in
    ``global`` -- a regional type (e.g. ``us-central1``) is NOT usable by an
    entry in the ``us`` multi-region. ``global`` types are usable from any
    region, which is the proven pattern already used by the Snowflake
    integration. This is the single source of truth for that decision.
    """
    return "global"


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
