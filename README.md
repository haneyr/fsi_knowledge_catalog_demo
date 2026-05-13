# FSI Knowledge Catalog Demo

End-to-end Knowledge Catalog and data governance demo for a financial services institution, built on Google Cloud. Demonstrates how Knowledge Catalog solves the **agent scale problem** — enabling AI agents to navigate 150+ tables across multiple source systems.

## The Demo Narrative

| Agent | Tables | Knowledge Catalog | Result |
|---|---|---|---|
| **Basic Agent** | 5 gold tables | No | Works for simple questions |
| **Scaled Agent** | 150+ tables | No | Fails on ambiguous/cross-domain questions |
| **KC-Guided Agent** | 150+ tables | Yes (MCP) | Succeeds at scale with metadata-grounded answers |

## What It Creates

| Component | Count | Details |
|---|---|---|
| **BigQuery Datasets** | 10 | fsi_bronze, fsi_silver, fsi_gold, fsi_reference, fsi_dashboards, fsi_staging, fsi_snapshots, fsi_audit, fsi_scan_results |
| **BigQuery Tables** | 150+ | 40 bronze + 40 silver + 20 gold + 8 views + 10 reference + 5 staging + 3 snapshots + 2 audit |
| **Source Systems** | 3 | ATLAS (IBM DB2), FORTUNA (Temenos T24), ARGUS (SAP S/4HANA) |
| **Business Glossary** | 1 | 80+ terms, 10 categories, 20 sub-categories, overviews, contacts |
| **Dataplex Scans** | 300+ | Profile + Quality + Insights for 100 tables |
| **Data Products** | 5 | Customer 360, Lending & Credit Risk, Wealth Management, Regulatory, Financial Performance |
| **Custom Aspects** | 7 types | Data Classification, Retention, Compliance, Lineage, Access Control, Risk, Regulatory Reporting |
| **Data Lineage** | 80+ links | 3 source systems → Bronze → Silver → Gold (5 processes) |
| **Rule Library** | 10 templates | CUSIP, ISIN, SSN masking, FICO range, balance checks, date ordering, FK validation |
| **Agents** | 3 | Basic, Scaled, KC-Guided — deployed to Vertex AI Agent Engine |

## Architecture

```
ATLAS (IBM DB2 Mainframe)          FORTUNA (Temenos T24)         ARGUS (SAP S/4HANA)
 Retail Banking: 14 tables          Wealth Mgmt: 13 tables       Finance & Risk: 13 tables
         │ IBM CDC                         │ Extract API                  │ SAP SLT
         ▼                                 ▼                              ▼
fsi_bronze (40 raw tables, ~500K rows total)
         │ Cleanse, Dedupe, Mask PII, Standardize
         ▼
fsi_silver (40 conformed tables, PK/FK constraints)
         │ Aggregate, Join, Compute Metrics
         ▼
fsi_gold (20 analytics tables)
         │
         ├── Data Products (5)
         ├── Business Glossary (80+ terms linked to columns)
         ├── Data Quality (150+ rules)
         ├── Data Profiles + Insights
         ├── Custom Aspects (classification, risk, compliance)
         └── Knowledge Catalog Context API + MCP Server
                    │
                    ▼
              AI Agents (ADK + Gemini + BigQuery)
              Deployed to Vertex AI Agent Engine
```

## Prerequisites

- Google Cloud SDK (`gcloud`)
- Python 3.12+
- `google-adk` >= 1.33.0
- `google-cloud-aiplatform` >= 1.60
- `google-cloud-bigquery` >= 3.0

Optional (for Terraform-based deploy):
- Terraform >= 1.5
- Terragrunt >= 0.50

## Deploy

### Step 1: Create the GCP Project

```bash
gcloud auth login
gcloud auth application-default login

# Create project (or use an existing one)
gcloud projects create YOUR-PROJECT-ID --name="FSI KC Demo" --organization=YOUR-ORG-ID
gcloud billing projects link YOUR-PROJECT-ID --billing-account=YOUR-BILLING-ACCOUNT

# Enable required APIs
gcloud services enable bigquery.googleapis.com dataplex.googleapis.com \
  datalineage.googleapis.com aiplatform.googleapis.com \
  cloudresourcemanager.googleapis.com iam.googleapis.com \
  cloudaicompanion.googleapis.com --project=YOUR-PROJECT-ID

gcloud config set project YOUR-PROJECT-ID
gcloud auth application-default set-quota-project YOUR-PROJECT-ID
```

### Step 2: Deploy BigQuery Tables (128 SQL files)

**Option A: Using `bq` CLI (no Terraform needed)**
```bash
# Edit PROJECT_ID in deploy-bq.sh, then:
bash deploy-bq.sh
```

**Option B: Using Terraform/Terragrunt**
```bash
# Edit env/existing-project.tfvars with your project ID
source deploy-existing-project.sh
```

### Step 3: Create Knowledge Catalog Resources

Edit `scripts/config.json` with your project ID and project number, then:
```bash
source post_deploy.sh
```

This runs 10 scripts that create:
1. Business glossary (83 terms, 28 categories)
2. Data quality scans (profile + quality + insights)
3. Source system entries (ATLAS, FORTUNA, ARGUS)
4. Custom aspects on all tables
5. Data products (5 with asset assignments)
6. Glossary-to-column links (77)
7. Data lineage (98 links, 5 processes)
8. Published scan labels
9. Query simulation (24 queries across 5 personas)
10. Reusable rule library (10 templates)

### Step 4: Deploy Agents to Vertex AI Agent Engine

```bash
# Install ADK
pip install google-adk google-cloud-aiplatform google-cloud-bigquery

# Deploy all 3 agents (handles IAM permissions automatically)
bash agents/deploy_agents.sh

# Or deploy individually:
bash agents/deploy_agents.sh basic
bash agents/deploy_agents.sh scaled
bash agents/deploy_agents.sh kc
```

The deploy script automatically:
1. Grants the Agent Engine service account required IAM permissions:
   - `roles/bigquery.jobUser` — run queries
   - `roles/bigquery.dataViewer` — read table data
   - `roles/dataplex.viewer` — access Knowledge Catalog entries
   - `roles/dataplex.catalogEditor` — search catalog entries
   - `roles/datalineage.viewer` — read data lineage
2. Creates `.env` files with your project config
3. Deploys each agent via `adk deploy agent_engine`
4. Prints the Agent Engine console URL

## Running Agents Locally (for development)

```bash
# Basic agent
cd agents/agent_basic
cp .env.example .env  # Edit with your project ID
pip install -r requirements.txt
python3 agent.py

# Scaled agent
cd agents/agent_scaled
cp .env.example .env
python3 agent.py

# KC agent
cd agents/agent_kc
cp .env.example .env
python3 agent.py
```

## Agent Architecture

### Basic Agent (`agents/agent_basic/`)
- 5 hardcoded gold tables in the system prompt
- `run_sql` tool for BigQuery
- Works well within its narrow scope

### Scaled Agent (`agents/agent_scaled/`)
- All 150+ table names listed in the system prompt
- Same `run_sql` tool
- Struggles with table selection, cross-domain queries, and ambiguity

### KC-Guided Agent (`agents/agent_kc/`)
- No hardcoded table list — discovers tables dynamically
- Uses Knowledge Catalog MCP tools: `search_entries`, `lookup_context`, `lookup_entry`
- `run_sql` for BigQuery after discovering the right tables
- Cites glossary terms, data quality scores, and lineage in answers
- Uses native Dataplex REST API calls (no external MCP Toolbox binary needed)

## Demo Questions

See `demo/demo_questions.md` for 15 curated questions across 3 tiers:
- **Tier 1** (Simple): All agents succeed
- **Tier 2** (Ambiguous): Scaled agent fails
- **Tier 3** (Cross-domain): Only KC agent succeeds

## Clean Up

```bash
source clean_up.sh
# Or delete the entire project:
gcloud projects delete YOUR-PROJECT-ID
```
