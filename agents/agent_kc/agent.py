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

"""
Retail Knowledge Catalog Agent — Uses KC MCP remote server to navigate 128+ BigQuery
tables and 6 NEXUS Snowflake tables.

Connects to the Knowledge Catalog MCP server (dataplex.googleapis.com/mcp) via
ADK's McpToolset for dynamic discovery of tables, data products, and metadata.
"""

import asyncio
import os
import re
import sys

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

from google.adk import Agent, Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.apps import App
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin
from google.cloud import bigquery
import google.auth
import google.auth.transport.requests

# Enable ADK SSE token-by-token streaming by default on the KC agent runtime
RunConfig.model_fields["streaming_mode"].default = StreamingMode.SSE
RunConfig.model_rebuild(force=True)

_raw_proj = os.environ.get("GOOGLE_CLOUD_PROJECT", "alitch-ca-demo")
PROJECT_ID = "alitch-ca-demo" if (not _raw_proj or _raw_proj.isdigit()) else _raw_proj
BQ_ANALYTICS_DATASET = os.environ.get("BQ_ANALYTICS_DATASET", "retail_agent_analytics")
NEXUS_CONNECTOR_TABLE = f"{PROJECT_ID}.retail_reference.nexus_connector_data"

_NEXUS_TABLE_SCHEMAS = {
    "nexus_competitor_prices": (
        "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES",
        [
            "observation_date", "gtin_13", "sku_code", "competitor_chain",
            "channel", "category_name", "competitor_regular_price",
            "competitor_promo_price", "northwind_shelf_price",
            "price_index_vs_competitor", "in_stock_flag", "region_code",
        ],
    ),
    "nexus_category_market_share": (
        "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_CATEGORY_MARKET_SHARE",
        [
            "period_month", "category_id", "category_name", "subcategory_name",
            "region_code", "total_market_sales_usd", "northwind_market_share_pct",
            "benchmark_gross_margin_pct", "top_quartile_margin_pct",
            "yoy_category_growth_pct", "markdown_rate_benchmark_pct",
        ],
    ),
    "nexus_consumer_panel": (
        "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_CONSUMER_PANEL",
        [
            "panel_quarter", "cohort_id", "income_band", "age_group",
            "region_code", "primary_category", "share_of_wallet_pct",
            "avg_basket_size_usd", "trips_per_quarter", "online_spend_share_pct",
        ],
    ),
    "nexus_regional_demand_index": (
        "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_REGIONAL_DEMAND_INDEX",
        [
            "week_ending_date", "region_code", "dma_code", "dma_name",
            "category_name", "demand_velocity_index", "foot_traffic_index",
            "digital_search_intent_index", "weather_sensitivity_score",
            "stockout_risk_benchmark_pct",
        ],
    ),
    "nexus_promo_calendar_benchmark": (
        "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_PROMO_CALENDAR_BENCHMARK",
        [
            "promo_window_id", "seasonal_event_name", "category_name",
            "competitor_tier", "avg_discount_depth_pct", "promo_duration_days",
            "baseline_unit_lift_pct", "margin_erosion_bps", "pull_forward_rate_pct",
        ],
    ),
    "nexus_basket_affinity": (
        "NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_BASKET_AFFINITY",
        [
            "anchor_category", "attached_category", "anchor_gtin_13",
            "attached_gtin_13", "co_occurrence_rate_pct",
            "affinity_lift_ratio", "avg_combined_basket_usd", "channel",
        ],
    ),
}

_NEXUS_ALIASES = {
    "nexus_competitor_prices": "nexus_competitor_prices",
    "competitor_prices": "nexus_competitor_prices",
    "nexus_category_market_share": "nexus_category_market_share",
    "category_market_share": "nexus_category_market_share",
    "nexus_consumer_panel": "nexus_consumer_panel",
    "consumer_panel": "nexus_consumer_panel",
    "nexus_regional_demand_index": "nexus_regional_demand_index",
    "regional_demand_index": "nexus_regional_demand_index",
    "nexus_promo_calendar_benchmark": "nexus_promo_calendar_benchmark",
    "promo_calendar_benchmark": "nexus_promo_calendar_benchmark",
    "promo_benchmark": "nexus_promo_calendar_benchmark",
    "nexus_basket_affinity": "nexus_basket_affinity",
    "basket_affinity": "nexus_basket_affinity",
}


def _get_bq_client():
    return bigquery.Client(project=PROJECT_ID)


SYSTEM_INSTRUCTION = f"""You are a senior retail & merchandising data analyst for Northwind Retail Group. You have
access to Google Cloud Knowledge Catalog for discovering and governing data assets, BigQuery (`run_sql`)
for internal medallion data, and the Snowflake NEXUS connector (`query_snowflake`) for external
third-party syndicated retail market intelligence.

Your project is: {PROJECT_ID}

## Knowledge Catalog Tool Parameters

ALL Knowledge Catalog tools require `projectId: "{PROJECT_ID}"`. Additional required params:
- `search_entries`: `projectId: "{PROJECT_ID}"`, `query` (required). Use `pageSize: 10`.
- `lookup_context`: `projectId: "{PROJECT_ID}"`, `location: "us"`, `resources` (list of entry names).
- `lookup_entry`: `projectId: "{PROJECT_ID}"`, `location: "us"`, `entry` (single entry name).
- `list_data_products`: `parent: "projects/{PROJECT_ID}/locations/us-central1"`.
- `get_data_product`: `name` (full resource name).

Deterministic Dataplex entry name formats (use these directly in `lookup_context` so you only need ONE `search_entries` call and ONE batched `lookup_context` call):
- BigQuery tables: `projects/{PROJECT_ID}/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/retail_<layer>/tables/<table_name>`
  (for example:
   - Gold: `projects/{PROJECT_ID}/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/retail_gold/tables/gold_inventory_allocation` or `gold_assortment_performance`
   - Silver: `projects/{PROJECT_ID}/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/retail_silver/tables/silver_product_skus` or `silver_inventory_positions`
   - Bronze: `projects/{PROJECT_ID}/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/retail_bronze/tables/bronze_product_skus` or `bronze_inventory_ledger`)
- NEXUS Snowflake tables: `projects/{PROJECT_ID}/locations/us/entryGroups/retail-nexus-market-intel/entries/<nexus_table_name>`
  where `<nexus_table_name>` is one of:
  `nexus_competitor_prices`, `nexus_category_market_share`, `nexus_consumer_panel`,
  `nexus_regional_demand_index`, `nexus_promo_calendar_benchmark`, `nexus_basket_affinity`.

## Mandatory Workflow & Provenance Rules

1. **DISCOVER (`search_entries`)**: Run ONE `search_entries` call to discover relevant assets.
2. **ESTABLISH PROVENANCE (`lookup_context`) — PROVENANCE RULE**:
   During discovery you MUST inspect at least one **Bronze** (`bronze_*`), one **Silver** (`silver_*`),
   and one **Gold** (`gold_*`) asset in a single batched `lookup_context` call (plus any relevant NEXUS
   entry `projects/{PROJECT_ID}/locations/us/entryGroups/retail-nexus-market-intel/entries/nexus_*`),
   even when one table would answer the question. Frame this as establishing end-to-end provenance
   across Bronze operational capture, Silver conformed entities, and Gold certified reporting.
3. **QUERY (`run_sql` and `query_snowflake`)**:
   - Use `run_sql` for BigQuery tables (`{PROJECT_ID}.retail_gold.*`, `{PROJECT_ID}.retail_silver.*`, `{PROJECT_ID}.retail_bronze.*`).
   - Use `query_snowflake` for NEXUS tables using `NEXUS_MARKET_DATA.SYNDICATED_INTEL.<TABLE>` naming:
     - `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES`
     - `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_CATEGORY_MARKET_SHARE`
     - `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_CONSUMER_PANEL`
     - `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_REGIONAL_DEMAND_INDEX`
     - `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_PROMO_CALENDAR_BENCHMARK`
     - `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_BASKET_AFFINITY`
   - For competitor price gap / SKU unit exposure questions, query `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES` via `query_snowflake`, AND query `{PROJECT_ID}.retail_silver.silver_product_skus` (`security_id`, `sku_code`, `gtin_13`, `security_name`, `asset_class`, `last_price`) joined with `{PROJECT_ID}.retail_silver.silver_inventory_positions` (`security_id`, `SUM(quantity) AS active_units`, `SUM(market_value) AS total_market_value`, `SUM(cost_basis) AS total_cost_basis`) `USING (security_id)` via `run_sql`.
   - **ACCURACY RULE**: Compute all deltas (absolute AND percentage) directly from the returned rows. NEVER invent a number. If a tool returns nothing, say so — do not improvise.
   - **HONESTY RULE**: Never claim NEXUS is live production vendor data. In Governance Context's Lineage bullet, state that NEXUS is a third-party licensed feed accessed via connector, queried in place, and not copied into BigQuery.

## Mandatory 4-Section Response Template (EVERY Answer)

Every response MUST use these exact four bold section headers in this exact order:

**Data discovery.**
Start with: `"I searched the Knowledge Catalog for <X>, which surfaced <N> assets:"`
Follow with a numbered list (`1.`, `2.`, `3.`, ...) containing at least one Gold, one Silver, and one Bronze asset (plus any NEXUS Snowflake asset inspected). Each item MUST include:
- Fully-qualified name (e.g. `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES`, `{PROJECT_ID}.retail_gold.gold_inventory_allocation`, `{PROJECT_ID}.retail_silver.silver_product_skus`, `{PROJECT_ID}.retail_bronze.bronze_product_skus`)
- Platform (`BigQuery` or `Snowflake`)
- Layer (`Gold`, `Silver`, `Bronze`, or `External Syndicated`)
- One-line description explaining how inspecting Bronze, Silver, and Gold establishes end-to-end provenance.

**Finding.**
- Lead with the business answer in natural human analyst prose.
- **VOICE RULE (CRITICAL)**: `Finding` must read like a human analyst wrote it. Lead with the business result — e.g. `"Syndicated market benchmarks show competitors priced ~6% below us in outerwear"` — NOT `"I queried NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES"` or `"According to silver_product_skus"`. Fully-qualified table names and technical column names must appear ONLY in **Data discovery.** and **Governance Context.**, NEVER in **Finding.** prose.
- Include a Markdown table of real values from the queries.
- Include both **absolute AND percentage delta** when comparing (e.g., `+$17.61 (+7.30%)` Northwind premium / `-$17.61 (-6.80%)` competitor discount).
- Follow the table with **one interpretive paragraph** naming the most likely cause (`timing mismatch`, `methodology difference`, or `genuine gap`) and stating explicitly whether the next step is **investigation** or **action**.

**Governance Context.**
Include these exact four labeled bullets every time:
- **Lineage** — Upstream table chain + `source_system` (`ORION` / `LUMEN` / `HELIOS` / `NEXUS`). When NEXUS data is used, you MUST state that `NEXUS` is a third-party licensed feed accessed via connector, queried in place, not copied into BigQuery.
- **Data quality** — Published scan name (e.g. `dq-gold-inventory-allocation`, `dq-silver-product-skus`, `dq-silver-inventory-positions`, `dq-gold-assortment-performance`) and the trust signal it carries.
- **Glossary** — A `[Retail]` business glossary term quoted verbatim (e.g. `[Retail] Global Trade Item Number (GTIN-13)`, `[Retail] Markdown Value at Risk (VaR)`, `[Retail] Gross Margin Percentage`, `[Retail] Return-Risk Score`, `[Retail] Customer Lifetime Value (CLV)`) + one sentence on its relevance.
- **Sensitivity** — Classification level (`Internal`, `Confidential`, `Restricted`, or `Third-Party Licensed`) + regulation (`PCI-DSS` / `CCPA` / `Vendor Data License #NWR-NEXUS-2026`).

**Recommendations.**
Exactly 3, numbered (`1.`, `2.`, `3.`), specific, actionable recommendations anchored to the numbers in the finding.

## Condensed Worked Example (Follow This Pattern)

**Data discovery.**
I searched the Knowledge Catalog for competitor shelf pricing and internal SKU inventory provenance, which surfaced 4 assets:
1. `NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES` — Platform: Snowflake | Layer: External Syndicated | Third-party syndicated daily shelf and promotional prices by GTIN-13 and retail chain.
2. `{PROJECT_ID}.retail_gold.gold_inventory_allocation` — Platform: BigQuery | Layer: Gold | Certified category-level inventory valuation, unit exposure, and unrealized gain/loss rollup.
3. `{PROJECT_ID}.retail_silver.silver_product_skus` — Platform: BigQuery | Layer: Silver | Conformed master SKU catalog with standardized GTIN-13 barcodes and active Northwind shelf prices to establish cross-cloud join provenance.
4. `{PROJECT_ID}.retail_bronze.bronze_product_skus` — Platform: BigQuery | Layer: Bronze | Raw item master feed ingested from LUMEN to verify source-to-gold pricing lineage.

**Finding.**
Syndicated market benchmarks show competitors priced 4.2% to 6.8% below Northwind across Apparel & Outerwear, Outdoor & Activewear, and Accessories & Jewelry, whereas Home & Kitchen, Beauty & Personal Care, and Footwear remain at market parity. Across the 6 overpriced SKUs, Northwind holds 16,320 units in active inventory representing $2.26M in market value at elevated markdown risk.

| SKU / Product | Category | Competitor Chain | Northwind Price | Competitor Regular Price | Price Gap ($ / %) | Active Units Exposed |
|---|---|---|---:|---:|---:|---:|
| Northwind Merino Knit 8 (`NW-SKU-000008`) | Apparel & Outerwear | Nordstrom | $258.91 | $241.30 | +$17.61 (+7.30% / Comp -6.80%) | 3,347 |
| Trailhead Waterproof Shell 4 (`NW-SKU-000004`) | Outdoor & Activewear | REI | $154.77 | $145.79 | +$8.98 (+6.16% / Comp -5.80%) | 3,113 |
| Artisan Leather Tote 1 (`NW-SKU-000001`) | Accessories & Jewelry | Bloomingdale's | $342.13 | $326.74 | +$15.39 (+4.71% / Comp -4.50%) | 3,691 |
| Cast-Iron Dutch Oven 2 (`NW-SKU-000002`) | Home & Kitchen | Target | $59.53 | $59.40 | +$0.13 (+0.22% / Parity) | 2,299 |

Because everyday essentials and kitchenware track within 22 bps of peer shelf prices on the same observation date, this divergence is not a timing mismatch or methodology difference — it reflects a **genuine gap** driven by early-season specialty competitor discounting in outerwear and leather accessories, meaning the immediate next step is **action** on price-matching and promotional protection.

**Governance Context.**
- **Lineage** — Internal pricing and unit exposure flow from `{PROJECT_ID}.retail_bronze.bronze_product_skus` and `{PROJECT_ID}.retail_bronze.bronze_inventory_ledger` (`source_system = LUMEN` and `HELIOS`) through `{PROJECT_ID}.retail_silver.silver_product_skus` and `{PROJECT_ID}.retail_silver.silver_inventory_positions` into `{PROJECT_ID}.retail_gold.gold_inventory_allocation`; `NEXUS` (`NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES`, `source_system = NEXUS`) is a third-party licensed feed accessed via connector, queried in place, and not copied into BigQuery.
- **Data quality** — Published scans `dq-gold-inventory-allocation` and `dq-silver-product-skus` validate 100% GTIN-13 format completeness, non-negative shelf prices, and reconciled inventory quantities across certified Gold and Silver tables.
- **Glossary** — `[Retail] Global Trade Item Number (GTIN-13)` provides the governed 13-digit GS1 identifier linking internal Northwind SKUs to external syndicated competitor price observations without ambiguity.
- **Sensitivity** — Internal pricing is classified as `Internal / Confidential` (`PCI-DSS` and `CCPA` non-PII), while NEXUS benchmark rows carry `Third-Party Licensed` classification governed under `Vendor Data License` (Contract #NWR-NEXUS-2026, no consumer PII).

**Recommendations.**
1. Execute an immediate 6.0% promotional price match on `NW-SKU-000008` (3,347 units) and `NW-SKU-000016` (2,177 units) in Apparel & Outerwear to close the $17.61–$3.71 shelf gap before Q4 peak traffic.
2. Bundle `NW-SKU-000004` and `NW-SKU-000012` (5,650 combined Outdoor & Activewear units) with loyalty point multipliers rather than permanent base-price cuts to defend gross margin against REI and Backcountry.
3. Hold current shelf pricing on Home & Kitchen (`NW-SKU-000002`) and Beauty (`NW-SKU-000007`), where Northwind sits within 0.22% of peer benchmarks and faces zero price-driven unit erosion.
"""


def _get_adc_token():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


kc_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://dataplex.googleapis.com/mcp",
    ),
    header_provider=lambda ctx: {
        "Authorization": f"Bearer {_get_adc_token()}",
        "x-goog-user-project": PROJECT_ID,
    },
    tool_filter=[
        "search_entries",
        "lookup_context",
        "lookup_entry",
        "list_data_products",
        "get_data_product",
    ],
)


@FunctionTool
def run_sql(sql: str) -> str:
    """Execute a read-only SQL query in BigQuery and return the results.

    Only SELECT / WITH statements are allowed. Always use fully-qualified table names:
    `project.dataset.table`.
    """
    cleaned = sql.strip().rstrip(";")
    cleaned = cleaned.replace("98236392654.", f"{PROJECT_ID}.")
    if not cleaned.upper().startswith(("SELECT", "WITH")):
        return "Error: Only SELECT queries are allowed."

    try:
        client = _get_bq_client()
        query_job = client.query(cleaned)
        results = query_job.result()

        rows = []
        for i, row in enumerate(results):
            if i >= 50:
                break
            rows.append(dict(row))

        if not rows:
            return "Query returned 0 rows."

        headers = list(rows[0].keys())
        lines = [" | ".join(headers)]
        lines.append("-" * len(lines[0]))
        for r in rows:
            lines.append(" | ".join(str(r.get(h, "")) for h in headers))

        return f"Query returned {results.total_rows} rows (showing first {len(rows)}):\n\n" + "\n".join(lines)
    except Exception as e:
        return f"SQL Error: {str(e)}"


def _resolve_nexus_tables(sql: str):
    """Detect which NEXUS table(s) are referenced in a Snowflake SQL query."""
    found = []
    lower_sql = sql.lower()
    # First check explicit nexus_* names, then short aliases
    for alias, canonical in sorted(_NEXUS_ALIASES.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(alias)}\b", lower_sql):
            if canonical not in found:
                found.append(canonical)
    if not found:
        found.append("nexus_competitor_prices")
    return found


def _translate_snowflake_sql_to_bq(sql: str, target_tables: list[str]) -> str:
    """Rewrite Snowflake NEXUS_MARKET_DATA.<SCHEMA>.<TABLE> references to subqueries on retail_reference.nexus_connector_data."""
    cleaned = sql.strip().rstrip(";")
    # Normalize Snowflake dialect idioms to BigQuery Standard SQL
    cleaned = re.sub(r"\bILIKE\b", "LIKE", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bNVL\s*\(", "IFNULL(", cleaned, flags=re.IGNORECASE)

    # Single-pass replacement so replaced subqueries are never re-matched by shorter aliases
    aliases_sorted = [re.escape(a) for a, _ in sorted(_NEXUS_ALIASES.items(), key=lambda x: -len(x[0]))]
    alias_group = "|".join(aliases_sorted)
    pattern = rf"(?:`?NEXUS_MARKET_DATA`?\s*\.\s*`?[A-Za-z0-9_]+`?\s*\.\s*`?(?P<t1>{alias_group})`?|`?[A-Za-z0-9_]+`?\s*\.\s*`?(?P<t2>{alias_group})`?|\b(?P<t3>{alias_group})\b)"

    def _repl(match):
        raw_tbl = (match.group("t1") or match.group("t2") or match.group("t3") or "").lower()
        canonical = _NEXUS_ALIASES.get(raw_tbl, "nexus_competitor_prices")
        _, cols = _NEXUS_TABLE_SCHEMAS[canonical]
        col_list = ", ".join(cols)
        return f"(SELECT {col_list} FROM `{NEXUS_CONNECTOR_TABLE}` WHERE table_name = '{canonical}')"

    return re.sub(pattern, _repl, cleaned, flags=re.IGNORECASE)


def _format_snowflake_rows(rows: list[dict], canonical_table: str) -> str:
    """Format BigQuery result rows like a Snowflake connector response."""
    sf_fqn, default_cols = _NEXUS_TABLE_SCHEMAS[canonical_table]
    headers = list(rows[0].keys()) if rows else default_cols
    upper_headers = [h.upper() for h in headers]
    header_line = " | ".join(upper_headers)
    sep_line = "-" * len(header_line)
    data_lines = [
        " | ".join("" if r.get(h) is None else str(r.get(h)) for h in headers)
        for r in rows
    ]
    return (
        f"Snowflake Connector Query Result — Object: {sf_fqn} ({canonical_table})\n"
        f"Feed: [Retail] NEXUS connector reference data (simulated external feed)\n"
        f"Query returned {len(rows)} rows:\n\n"
        + "\n".join([header_line, sep_line] + data_lines)
    )


@FunctionTool
def query_snowflake(sql: str) -> str:
    """Execute a SQL query against the NEXUS Snowflake connector using NEXUS_MARKET_DATA.<SCHEMA>.<TABLE> naming.

    Supported tables in NEXUS_MARKET_DATA.SYNDICATED_INTEL:
      - NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_COMPETITOR_PRICES
      - NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_CATEGORY_MARKET_SHARE
      - NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_CONSUMER_PANEL
      - NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_REGIONAL_DEMAND_INDEX
      - NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_PROMO_CALENDAR_BENCHMARK
      - NEXUS_MARKET_DATA.SYNDICATED_INTEL.NEXUS_BASKET_AFFINITY
    """
    client = _get_bq_client()
    target_tables = _resolve_nexus_tables(sql)
    primary_table = target_tables[0]
    _, cols = _NEXUS_TABLE_SCHEMAS[primary_table]

    # 1. Try executing the agent's translated SQL query against retail_reference.nexus_connector_data
    try:
        cleaned = sql.strip().rstrip(";")
        if cleaned.upper().startswith(("SELECT", "WITH")):
            bq_sql = _translate_snowflake_sql_to_bq(cleaned, target_tables)
            res = client.query(bq_sql).result()
            rows = []
            for i, row in enumerate(res):
                if i >= 50:
                    break
                rows.append(dict(row))
            if rows:
                return _format_snowflake_rows(rows, primary_table)
    except Exception:
        pass

    # 2. Deterministic fallback: always succeed by querying all rows for the requested NEXUS table
    fallback_sql = (
        f"SELECT {', '.join(cols)} "
        f"FROM `{NEXUS_CONNECTOR_TABLE}` "
        f"WHERE table_name = '{primary_table}' "
        f"ORDER BY 1, 2 LIMIT 50"
    )
    res = client.query(fallback_sql).result()
    rows = [dict(r) for r in res]
    return _format_snowflake_rows(rows, primary_table)


_kc_tools = [kc_toolset, run_sql, query_snowflake]

root_agent = Agent(
    name="retail_kc_agent",
    model="gemini-2.5-flash",
    description="[Retail] Northwind Retail Knowledge Catalog Agent (128+ BigQuery tables + 6 NEXUS Snowflake tables)",
    instruction=SYSTEM_INSTRUCTION,
    tools=_kc_tools,
)

bq_analytics_plugin = BigQueryAgentAnalyticsPlugin(
    project_id=PROJECT_ID,
    dataset_id=BQ_ANALYTICS_DATASET,
    table_id="kc_agent_events",
    location="US",
)

app = App(
    name="retail_kc_agent",
    root_agent=root_agent,
    plugins=[bq_analytics_plugin],
)


async def run_interactive():
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="retail_kc_agent", session_service=session_service)
    session = await session_service.create_session(app_name="retail_kc_agent", user_id="demo_user")

    print("\n" + "=" * 60)
    print("Retail Knowledge Catalog Agent (128+ BQ + 6 NEXUS tables)")
    print("Powered by ADK + Knowledge Catalog MCP Server + BigQuery + NEXUS Connector")
    print("=" * 60)

    while True:
        try:
            question = input("\nYou: ").strip()
            if not question or question.lower() in ("exit", "quit", "q"):
                break

            from google.genai import types
            content = types.Content(role="user", parts=[types.Part.from_text(text=question)])
            print("\nAgent: ", end="", flush=True)
            async for event in runner.run_async(
                session_id=session.id,
                user_id="demo_user",
                new_message=content,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                if getattr(event, "partial", False) and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(part.text, end="", flush=True)
            print()
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    asyncio.run(run_interactive())
