# Snowflake NEXUS Integration

Optional module that adds a 4th source system — **NEXUS**, an external market data provider — in Snowflake. Demonstrates Knowledge Catalog discovering and governing data across BigQuery and Snowflake.

## Prerequisites

- Snowflake account ([free trial](https://signup.snowflake.com/) works)
- Python 3.12+ with `snowflake-connector-python`
- GCP project with the main demo already deployed

## Snowflake User Setup

Log into Snowflake as `ACCOUNTADMIN` to create the required roles and users. ACCOUNTADMIN is only used for user/role management — the scripts and agent never run as ACCOUNTADMIN.

### Step 1: Create the setup user

```sql
CREATE ROLE IF NOT EXISTS FSI_KC_SETUP_ROLE;
GRANT CREATE DATABASE ON ACCOUNT TO ROLE FSI_KC_SETUP_ROLE;
GRANT CREATE WAREHOUSE ON ACCOUNT TO ROLE FSI_KC_SETUP_ROLE;
GRANT APPLY TAG ON ACCOUNT TO ROLE FSI_KC_SETUP_ROLE;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE FSI_KC_SETUP_ROLE;

CREATE USER IF NOT EXISTS FSI_KC_SETUP
  PASSWORD = '<choose-a-password>'
  DEFAULT_ROLE = FSI_KC_SETUP_ROLE
  MUST_CHANGE_PASSWORD = FALSE;
GRANT ROLE FSI_KC_SETUP_ROLE TO USER FSI_KC_SETUP;
```

### Step 2: Run the setup scripts

```bash
export SNOWFLAKE_ACCOUNT=your-account-id
export SNOWFLAKE_USER=FSI_KC_SETUP
export SNOWFLAKE_PASSWORD=your-setup-password
bash snowflake/deploy.sh
```

### Step 3: Create the agent user

After the setup scripts complete (the database and warehouse now exist):

```sql
CREATE ROLE IF NOT EXISTS FSI_KC_AGENT_ROLE;
GRANT USAGE ON WAREHOUSE NEXUS_WH TO ROLE FSI_KC_AGENT_ROLE;
GRANT USAGE ON DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;
GRANT SELECT ON FUTURE TABLES IN DATABASE NEXUS_MARKET_DATA TO ROLE FSI_KC_AGENT_ROLE;

CREATE USER IF NOT EXISTS FSI_KC_AGENT
  PASSWORD = '<choose-a-password>'
  DEFAULT_ROLE = FSI_KC_AGENT_ROLE
  DEFAULT_WAREHOUSE = NEXUS_WH
  MUST_CHANGE_PASSWORD = FALSE;
GRANT ROLE FSI_KC_AGENT_ROLE TO USER FSI_KC_AGENT;
```

### Step 4: Set agent environment variables

```bash
export SNOWFLAKE_AGENT_USER=FSI_KC_AGENT
export SNOWFLAKE_AGENT_PASSWORD=your-agent-password
```

Then deploy the agents as normal — the deploy script will detect Snowflake configuration and add the `query_snowflake` tool to the KC agent.

## Environment Variables

| Variable | Required For | Description |
|---|---|---|
| `SNOWFLAKE_ACCOUNT` | Setup + Agent | Account identifier (e.g., `xy12345.us-east-1`) |
| `SNOWFLAKE_USER` | Setup | Setup user (FSI_KC_SETUP) |
| `SNOWFLAKE_PASSWORD` | Setup | Setup user password |
| `SNOWFLAKE_AGENT_USER` | Agent | Read-only agent user (FSI_KC_AGENT) |
| `SNOWFLAKE_AGENT_PASSWORD` | Agent | Agent user password |
| `SNOWFLAKE_WAREHOUSE` | Both | Warehouse name (default: `NEXUS_WH`) |
| `SNOWFLAKE_DATABASE` | Both | Database name (default: `NEXUS_MARKET_DATA`) |

## Production Credential Management

Environment variables are appropriate for this demo. For production deployments:

- **Google Cloud Secret Manager:** The upstream [Snowflake Horizon connector](https://github.com/GoogleCloudPlatform/cloud-dataplex/tree/main/managed-connectivity/community-contributed-connectors/snowflake-horizon-connector) natively supports Secret Manager for credential storage. Adapt the connection helper in `common_snowflake.py` to read from `secretmanager.googleapis.com` instead of env vars.
- **Snowflake key-pair authentication:** Replace password auth with RSA key-pair auth for service accounts. Store the private key in Secret Manager and reference it in the connection config.

## What It Creates

| Component | Details |
|---|---|
| Snowflake warehouse | `NEXUS_WH` (X-Small, auto-suspend 60s) |
| Snowflake database | `NEXUS_MARKET_DATA` with 4 schemas, 10 tables |
| Synthetic data | ~50K rows of market data aligned to BQ CUSIPs |
| Horizon tags | 5 governance tags applied to all tables |
| Dataplex entries | Account, database, schema, table, tag, tag-ref entries |
| Glossary links | CUSIP, ISIN, NIM, Risk Rating linked to Snowflake columns |
| Custom aspects | Classification, retention, compliance, lineage, access control |
| Data lineage | NEXUS -> Snowflake feed (10 links) |
