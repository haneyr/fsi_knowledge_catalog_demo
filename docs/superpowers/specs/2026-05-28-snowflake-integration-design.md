# Snowflake Integration Design — NEXUS Market Data Provider

**Date:** 2026-05-28
**Status:** Draft
**Approach:** Integrated Optional Module (Approach 1)

---

## Overview

Add an optional Snowflake integration module to the FSI Knowledge Catalog demo. A 4th source system — **NEXUS**, an external market data provider — lives in Snowflake on AWS. Its metadata is ingested into Knowledge Catalog via the Horizon connector pattern, enriched with glossary terms and custom aspects, and made queryable by the KC agent through a new `query_snowflake` tool.

The integration is fully opt-in: controlled by `SNOWFLAKE_ACCOUNT` environment variable. When absent, no Snowflake code runs, no dependencies are imported, and all existing functionality is unchanged.

## Goals

- Demonstrate Knowledge Catalog's multi-cloud metadata management — discovering and governing data across BigQuery and Snowflake
- Show the KC agent querying both platforms in a single response, joining results across clouds
- Preserve Snowflake Horizon governance context (tags, classifications) through KC
- Keep the Snowflake module fully isolated so 99% of users without Snowflake are unaffected

## Non-Goals

- Production-grade Snowflake connector (we adapt the Horizon connector pattern, not vendor the full repo)
- Snowflake table differentiation in the frontend visualization (deferred to GitHub issue)
- Supporting connectors for other platforms (Databricks, etc.) — no plugin architecture

---

## 1. NEXUS Source System & Data Model

### Narrative

NEXUS is an external market data vendor (analogous to Bloomberg or Refinitiv). It supplies data the bank's internal systems don't have: real-time security pricing, benchmark indices, economic indicators, and risk analytics. This creates natural cross-platform queries — the bank's internal data lives in BigQuery (ATLAS/FORTUNA/ARGUS), but market data comes from NEXUS via Snowflake.

### Snowflake Database Structure

```
NEXUS_MARKET_DATA (database)
├── SECURITIES (schema)
│   ├── security_prices        — Daily closing prices by CUSIP/ISIN
│   ├── security_fundamentals  — P/E, EPS, market cap, dividend yield
│   └── corporate_actions      — Splits, dividends, mergers
├── INDICES (schema)
│   ├── benchmark_returns      — Daily/monthly returns for S&P 500, Russell, etc.
│   └── index_constituents     — Which securities are in which index
├── ECONOMICS (schema)
│   ├── interest_rate_curves   — SOFR, Fed Funds Effective, Treasury yields (2Y/5Y/10Y/30Y)
│   ├── economic_indicators    — GDP, CPI, unemployment, housing starts
│   └── fx_spot_rates          — Real-time FX rates (complements bronze_fx_rates)
└── RISK_ANALYTICS (schema)
    ├── credit_spreads         — Corporate bond spreads by rating/sector
    └── volatility_surfaces    — Implied vol for options pricing
```

~10 tables, ~50K synthetic rows total.

### Cross-Platform Join Points

| Snowflake Table | BQ Table | Join Key | Cross-Platform Question |
|---|---|---|---|
| `security_prices` | `silver_holdings` | CUSIP | "What's the current market value of our portfolios?" |
| `benchmark_returns` | `gold_portfolio_performance` | benchmark name | "How do our portfolios compare to their benchmarks?" |
| `interest_rate_curves` | `gold_net_interest_margin` | date | "What's our NIM sensitivity to the current yield curve?" |
| `credit_spreads` | `gold_market_risk_var` | rating/sector | "What's our credit spread exposure?" |

### Synthetic Data Requirements

- CUSIPs and ISINs must match the values used in `ref_cusip_master` and `ref_isin_mapping` in BigQuery
- Benchmark names must match those in `gold_portfolio_performance`
- Date ranges must overlap with existing BQ data, aligned to **US business days only** (no weekends, no NYSE holidays). Timestamps standardized to Eastern time market close (16:00 ET) to avoid missing join keys when crossing platforms
- Interest rate curves must include standard benchmarks that banking audiences expect: SOFR (Secured Overnight Financing Rate), Fed Funds Effective Rate, and Treasury yields (2Y, 5Y, 10Y, 30Y). These make cross-platform NIM sensitivity questions realistic
- All data generated deterministically (seeded random) for reproducibility

### Horizon Governance Tags

| Tag | Values | Applied To |
|---|---|---|
| `DATA_CLASSIFICATION` | `PUBLIC`, `INTERNAL`, `CONFIDENTIAL` | All tables |
| `DATA_DOMAIN` | `MARKET_DATA`, `RISK`, `ECONOMICS` | All tables |
| `DATA_FRESHNESS` | `REAL_TIME`, `DAILY`, `MONTHLY` | Per table |
| `PII_FLAG` | `FALSE` | All tables |
| `SOURCE_VENDOR` | `NEXUS_DATA_SERVICES` | All tables |

---

## 2. Snowflake User Setup

Two Snowflake users with separate roles, following least-privilege principles. Both users and roles are created by ACCOUNTADMIN in the Snowflake console. ACCOUNTADMIN is only used for user/role management — the scripts and agent never run as ACCOUNTADMIN.

### Step 1: Create the setup user (run as ACCOUNTADMIN)

Run this before any setup scripts:

```sql
-- Create a role for demo setup (needs full DDL privileges)
CREATE ROLE IF NOT EXISTS FSI_KC_SETUP_ROLE;
GRANT CREATE DATABASE ON ACCOUNT TO ROLE FSI_KC_SETUP_ROLE;
GRANT CREATE WAREHOUSE ON ACCOUNT TO ROLE FSI_KC_SETUP_ROLE;
GRANT APPLY TAG ON ACCOUNT TO ROLE FSI_KC_SETUP_ROLE;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE FSI_KC_SETUP_ROLE;

-- Create the setup user
CREATE USER IF NOT EXISTS FSI_KC_SETUP
  PASSWORD = '<choose-a-password>'
  DEFAULT_ROLE = FSI_KC_SETUP_ROLE
  MUST_CHANGE_PASSWORD = FALSE;
GRANT ROLE FSI_KC_SETUP_ROLE TO USER FSI_KC_SETUP;
```

`IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE` is required for the Horizon connector to read `SNOWFLAKE.ACCOUNT_USAGE` views during metadata extraction.

### Step 2: Run setup scripts

Run `snowflake/00_setup_nexus_data.py` using the setup user credentials. This creates the database, warehouse, schemas, and tables. The agent user grants below reference these objects, so they must exist first.

### Step 3: Create the agent user (run as ACCOUNTADMIN)

After the setup scripts have created the database and warehouse:

```sql
-- Create a read-only role for the agent
CREATE ROLE IF NOT EXISTS FSI_KC_AGENT_ROLE;
GRANT USAGE ON WAREHOUSE NEXUS_WH TO ROLE FSI_KC_AGENT_ROLE;
GRANT USAGE ON DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;
GRANT SELECT ON FUTURE TABLES IN DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;

-- Create the agent user
CREATE USER IF NOT EXISTS FSI_KC_AGENT
  PASSWORD = '<choose-a-password>'
  DEFAULT_ROLE = FSI_KC_AGENT_ROLE
  DEFAULT_WAREHOUSE = NEXUS_WH
  MUST_CHANGE_PASSWORD = FALSE;
GRANT ROLE FSI_KC_AGENT_ROLE TO USER FSI_KC_AGENT;
```

### Environment Variables

```bash
# For setup scripts (setup user)
export SNOWFLAKE_ACCOUNT=your-account-id       # e.g., xy12345.us-east-1
export SNOWFLAKE_USER=FSI_KC_SETUP
export SNOWFLAKE_PASSWORD=your-setup-password

# For agent queries (agent user)
export SNOWFLAKE_AGENT_USER=FSI_KC_AGENT
export SNOWFLAKE_AGENT_PASSWORD=your-agent-password
export SNOWFLAKE_WAREHOUSE=NEXUS_WH
export SNOWFLAKE_DATABASE=NEXUS_MARKET_DATA
```

**Production note:** Environment variables are appropriate for this demo environment. For production deployments, credentials should be stored in Google Cloud Secret Manager (which the Horizon connector natively supports) or Snowflake key-pair authentication. The `snowflake/README.md` will include a section on adapting the credential flow for enterprise use, referencing the Secret Manager integration pattern from the upstream Horizon connector.

---

## 3. Metadata Ingestion & Enrichment Pipeline

Four scripts in `snowflake/`, following the same numbered-script pattern as `scripts/`.

### 00_setup_nexus_data.py

Creates everything in Snowflake:
1. Warehouse `NEXUS_WH` (X-Small, auto-suspend 60s)
2. Database `NEXUS_MARKET_DATA` with 4 schemas
3. ~10 tables with synthetic data (~50K rows)
4. Horizon governance tags and tag assignments
5. Comments on all tables and columns (these become descriptions in KC)

Uses `snowflake-connector-python` to connect with the setup user credentials.

### 01_create_dataplex_infra.py

Creates Dataplex resources needed before metadata import:
- Entry group: `snowflake-nexus`
- 7 entry types: `snowflake-account`, `snowflake-database`, `snowflake-schema`, `snowflake-table`, `snowflake-view`, `snowflake-tag`, `snowflake-tag-ref`
- 7 corresponding aspect types with structured field templates

Reuses `api_call()` from `scripts/common.py`.

### 02_ingest_metadata.py

Connects to Snowflake with setup user credentials, queries `SNOWFLAKE.ACCOUNT_USAGE` views to extract:
- Database/schema/table structure
- Column names, types, comments
- Horizon tags and tag references

Produces a JSONL metadata import file and calls the Dataplex Import API to load entries into KC.

### 03_enrich_entries.py

After import, applies the same enrichments as existing BQ scripts:
- **Glossary links** — Links Snowflake columns to existing glossary terms (`security_prices.cusip` → CUSIP, `security_prices.isin` → ISIN, `interest_rate_curves.rate` → NIM)
- **Custom aspects** — Applies the same 7 aspect types used on BQ tables with values appropriate for external market data
- **Source system lineage** — Creates lineage entries showing NEXUS as a source feeding into the bank's analytics

Imports `set_entry_aspect()`, `glossary_term_entry()`, `api_call()` from `scripts/common.py`.

### deploy.sh

Orchestrates the above:
```bash
python3 snowflake/00_setup_nexus_data.py
python3 snowflake/01_create_dataplex_infra.py
python3 snowflake/02_ingest_metadata.py
python3 snowflake/03_enrich_entries.py
```

Called from `deploy-full.sh` conditionally:
```bash
if [ -n "${SNOWFLAKE_ACCOUNT:-}" ]; then
    echo "=== Deploying Snowflake (NEXUS) integration ==="
    bash snowflake/deploy.sh
fi
```

---

## 4. KC Agent Integration

### New Tool: query_snowflake

Added to `agents/agent_kc/agent.py`. Mirrors `run_sql` interface:

```python
@FunctionTool
def query_snowflake(sql: str) -> str:
    """Execute a SQL query against Snowflake and return results.
    Use this when Knowledge Catalog search reveals data in Snowflake
    (NEXUS market data). Use fully qualified names: DATABASE.SCHEMA.TABLE."""
```

### Conditional Registration

```python
tools = [search_entries, get_context, run_sql]
if os.environ.get("SNOWFLAKE_ACCOUNT"):
    tools.append(query_snowflake)
```

The `snowflake-connector-python` import is inside the `if` block — no import errors when the package isn't installed.

### System Prompt Extension

When Snowflake is enabled, appended to the existing instruction:

> You also have access to Snowflake for querying external market data from the NEXUS data provider. When Knowledge Catalog search results include Snowflake entries (entry type `snowflake-table`), use `query_snowflake` instead of `run_sql`. Use fully qualified Snowflake table names: `NEXUS_MARKET_DATA.SCHEMA.TABLE`.
>
> For cross-platform questions, you may need to query both BigQuery and Snowflake, then combine the results in your response. For example, portfolio holdings live in BigQuery while current security prices live in Snowflake.

### Connection Management

Lazy-initialized Snowflake connection cached at module level, using agent user credentials:
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_AGENT_USER` / `SNOWFLAKE_AGENT_PASSWORD`
- `SNOWFLAKE_WAREHOUSE` (defaults to `NEXUS_WH`)
- `SNOWFLAKE_DATABASE` (defaults to `NEXUS_MARKET_DATA`)

### Agent Engine Deployment

`deploy_agents.sh` conditionally:
1. Adds Snowflake env vars to `agent_kc/.env`
2. Adds `snowflake-connector-python` to `agent_kc/requirements.txt`

When Snowflake is not configured, neither file is modified.

### Cross-Platform Query Flow

1. User: "What's the current market value of our top wealth portfolios?"
2. Agent → `search_entries("portfolio holdings securities market value")`
3. KC returns entries from both BQ (`gold_portfolio_performance`) and Snowflake (`security_prices`)
4. Agent → `get_context(...)` — reads schemas, sees CUSIP as join key
5. Agent → `run_sql(...)` — gets portfolio holdings with CUSIPs from BQ
6. Agent → `query_snowflake(...)` — gets current prices from Snowflake
7. Agent combines results in response, citing both source systems and their lineage

**Avoiding CUSIP list explosion:** When a BQ query returns many securities (hundreds of CUSIPs), the agent should NOT pass them all as an IN-list to Snowflake. Instead, the system prompt instructs the agent to query Snowflake with broader filters (date range, asset class) and let the agent join the results logically in its response. For targeted lookups (a specific portfolio or small set of securities), passing CUSIPs directly is fine. The system prompt guidance:

> When querying Snowflake for pricing data, prefer broad filters (date range, asset class) over large IN-lists of identifiers. If a BigQuery result returns more than ~20 securities, query Snowflake for the full pricing universe for that date and match in your analysis rather than passing all CUSIPs into a single WHERE clause.

---

## 5. Demo Narrative & Eval Test Cases

### New Demo Category

**Category 7: Multi-Cloud Discovery** — added to `demo/demo_questions.md`.

| Scenario | Question | What Happens |
|---|---|---|
| 7.1 — Portfolio market value | "What's the current market value of our top wealth portfolios?" | KC finds holdings (BQ) + prices (Snowflake) → queries both → joins on CUSIP |
| 7.2 — Benchmark comparison | "How do our portfolios compare to their benchmark indices this year?" | KC finds `gold_portfolio_performance` (BQ) + `benchmark_returns` (Snowflake) → calculates over/under-performance |
| 7.3 — Yield curve sensitivity | "What's our NIM exposure given the current yield curve?" | KC finds `gold_net_interest_margin` (BQ) + `interest_rate_curves` (Snowflake) → presents NIM with rate context |
| 7.4 — Credit spread risk | "What's our credit spread exposure by sector?" | KC finds `gold_market_risk_var` (BQ) + `credit_spreads` (Snowflake) → combines risk metrics with market spreads |

**Key demo talking point:**

> "The agent didn't know in advance that pricing data lives in Snowflake. It searched Knowledge Catalog, discovered entries from two different platforms, read the metadata to understand both schemas, then queried BigQuery AND Snowflake and combined the results. That's multi-cloud data discovery — no hardcoded connections, no pre-built joins."

### New Eval Test Cases

4 cases added to `eval/test_cases.yaml`, tagged `complexity: multi_cloud`, `kc_feature: cross_platform_discovery`.

Expected outcomes:
- `basic`: `fail_gracefully`
- `scaled`: `fail_gracefully`
- `kc`: `success` with tables spanning both BQ and Snowflake, tool calls including both `run_sql` and `query_snowflake`

`eval/run_eval.py` skips `multi_cloud` cases when `SNOWFLAKE_ACCOUNT` is not set.

---

## 6. File Structure

### New Files

```
snowflake/
├── README.md                        # Snowflake-specific setup, user creation, env vars
├── config.json                      # Generated by deploy.sh
├── deploy.sh                        # Orchestrates all Snowflake setup steps
├── requirements.txt                 # snowflake-connector-python
├── 00_setup_nexus_data.py           # DB, schemas, tables, synthetic data, Horizon tags
├── 01_create_dataplex_infra.py      # Entry types, aspect types in Dataplex
├── 02_ingest_metadata.py            # Horizon metadata → Dataplex Import API
├── 03_enrich_entries.py             # Glossary links, custom aspects, lineage
└── common_snowflake.py              # Snowflake connection helpers
```

### Modified Files

| File | Change |
|---|---|
| `agents/agent_kc/agent.py` | Conditional `query_snowflake` tool + system prompt extension |
| `agents/agent_kc/requirements.txt` | `snowflake-connector-python` added conditionally by deploy script |
| `agents/deploy_agents.sh` | Snowflake env vars to `agent_kc/.env` when enabled |
| `deploy-full.sh` | Conditional `bash snowflake/deploy.sh` step |
| `README.md` | Snowflake section with user setup and env var reference |
| `demo/demo_questions.md` | Category 7: Multi-Cloud Discovery |
| `eval/test_cases.yaml` | 4 multi-cloud test cases |
| `eval/run_eval.py` | Skip multi-cloud cases when Snowflake not configured |
| `pyproject.toml` | Optional `snowflake` dependency group |

### Unchanged

- All scripts in `scripts/`
- `agents/agent_basic/`, `agents/agent_scaled/`
- `website-live/static/` (visualization differentiation deferred)
- `modules/` Terraform
- `clean_up.sh`

---

## 7. Dependency Management

`pyproject.toml` new optional group:
```toml
[project.optional-dependencies]
snowflake = [
    "snowflake-connector-python>=3.0",
]
```

`snowflake/requirements.txt` lists the same for non-uv users.

Agent `requirements.txt` only modified by `deploy_agents.sh` when Snowflake is enabled. Import guard in agent code prevents import errors when the package isn't installed.

---

## 8. Implementation Issues

The implementation breaks into 6 GitHub issues with a natural dependency chain:

### Issue 1: Snowflake data setup scripts
Create `snowflake/00_setup_nexus_data.py` and `snowflake/common_snowflake.py`. Creates the NEXUS database, schemas, ~10 tables, synthetic data, warehouse, and Horizon governance tags in Snowflake. Includes `snowflake/requirements.txt`.

**Depends on:** Nothing (but requires a Snowflake account with users created per README)

### Issue 2: Dataplex infrastructure for Snowflake entries
Create `snowflake/01_create_dataplex_infra.py`. Creates entry group, 7 entry types, and 7 aspect types in Dataplex for Snowflake metadata.

**Depends on:** Nothing (can be done in parallel with Issue 1)

### Issue 3: Horizon metadata ingestion
Create `snowflake/02_ingest_metadata.py`. Extracts metadata from Snowflake ACCOUNT_USAGE views, produces JSONL import file, calls Dataplex Import API.

**Depends on:** Issue 1 (data must exist in Snowflake), Issue 2 (Dataplex types must exist)

### Issue 4: Metadata enrichment — glossary links, aspects, lineage
Create `snowflake/03_enrich_entries.py`. Links Snowflake entries to business glossary terms, applies custom aspects, creates NEXUS source system lineage.

**Depends on:** Issue 3 (entries must exist in KC)

### Issue 5: KC agent Snowflake query tool
Add conditional `query_snowflake` tool to `agents/agent_kc/agent.py`. Extend system prompt, connection management, conditional registration. Update `deploy_agents.sh` for Snowflake env vars.

**Depends on:** Issue 1 (data must exist to query), Issue 4 (metadata must be in KC for agent to discover it)

### Issue 6: Deploy orchestration, docs, demo scenarios, eval cases
Create `snowflake/deploy.sh` and `snowflake/README.md`. Update `deploy-full.sh`, main `README.md`, `demo/demo_questions.md`, `eval/test_cases.yaml`, `eval/run_eval.py`, `pyproject.toml`.

**Depends on:** Issues 1-5 (all components must exist to orchestrate and document)

### Deferred Issue: Snowflake table visualization differentiation
Differentiate Snowflake tables visually in the website-live point cloud visualization (different color/cluster). Not required for initial implementation.

**Depends on:** Issue 5 (agent must be able to surface Snowflake tables)

### Dependency Graph

```
Issue 1 (Snowflake data) ──┐
                            ├──→ Issue 3 (Ingestion) ──→ Issue 4 (Enrichment) ──→ Issue 5 (Agent tool) ──→ Issue 6 (Orchestration & docs)
Issue 2 (Dataplex infra) ──┘
```

Issues 1 and 2 can be implemented in parallel. Issues 3-6 are sequential.
