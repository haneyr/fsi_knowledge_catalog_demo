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
| **Agents** | 3 | Basic, Scaled, KC-Guided — all deployable to Vertex AI Agent Engine |

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
```

## Prerequisites

- Google Cloud SDK (`gcloud`)
- Terraform >= 1.5
- Terragrunt >= 0.50
- Python 3.x with `google-auth` and `requests`

## Deploy

### Option 1: Existing GCP Project

1. Edit `env/existing-project.tfvars` with your project details
2. Run:
```bash
gcloud auth login
gcloud auth application-default login
source deploy-existing-project.sh
```

### Option 2: New GCP Project

```bash
gcloud auth login
gcloud auth application-default login
source deploy.sh
```

## Running the Agents

```bash
cd agents/agent_basic
pip install -r requirements.txt
export GOOGLE_CLOUD_PROJECT=your-project-id
python3 agent.py
```

For the KC-guided agent, you also need the MCP Toolbox binary:
```bash
cd agents/agent_kc
# Download toolbox binary to this directory
export DATAPLEX_PROJECT=your-project-id
python3 agent.py
```

## Clean Up

```bash
source clean_up.sh
# Or delete the entire project:
gcloud projects delete PROJECT_ID
```
