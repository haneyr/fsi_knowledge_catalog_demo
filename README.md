# FSI Knowledge Catalog Demo

End-to-end Knowledge Catalog and data governance demo for a financial services institution, built on Google Cloud. Demonstrates how Knowledge Catalog solves the **agent scale problem** — enabling AI agents to navigate 128+ tables across multiple source systems.

## The Demo Narrative

| Agent | Tables | Knowledge Catalog | Result |
|---|---|---|---|
| **Basic Agent** | 5 gold tables | No | Works for simple questions |
| **Scaled Agent** | 128 tables | No | Fails on ambiguous/cross-domain questions |
| **KC-Guided Agent** | 128+ tables | Yes (MCP) | Succeeds at scale with metadata-grounded answers |

## What It Creates

| Component | Count | Details |
|---|---|---|
| **BigQuery Datasets** | 10 | fsi_bronze, fsi_silver, fsi_gold, fsi_reference, fsi_dashboards, fsi_staging, fsi_snapshots, fsi_audit, fsi_scan_results |
| **BigQuery Tables** | 128 | 40 bronze + 40 silver + 20 gold + 8 views + 10 reference + 5 staging + 3 snapshots + 2 audit |
| **Source Systems** | 3 | ATLAS (IBM DB2), FORTUNA (Temenos T24), ARGUS (SAP S/4HANA) |
| **Business Glossary** | 1 | 80+ terms, 10 categories, 20 sub-categories, overviews, contacts |
| **Data Scans** | 300+ | Profile + Quality + Insights for 100 tables |
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

### Region model

Knowledge Catalog resources span three locations, kept consistent via `scripts/config.json`:

| Location | Applies to |
|---|---|
| `multi_region` (`us`) | BigQuery datasets, glossary, **user entry groups**, source entries |
| `global` | entry types, aspect types |
| `region` (`us-central1`) | Vertex AI / Agent Engine |

User entry groups and entries live in the multi-region so that entry-to-glossary-term links
resolve. Entry/aspect **types** live in `global`: Knowledge Catalog requires an entry's type to be in
the entry's own region, a corresponding multi-region, or `global`, so a regional type is not
usable by a `us` multi-region entry. The decision is centralized in `scripts/common.py`
(`entry_group_location` → `us`, `entry_type_location` → `global`).

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

### One-Command Deploy (recommended)

```bash
gcloud auth login
gcloud auth application-default login
pip install google-adk google-cloud-aiplatform google-cloud-bigquery google-auth requests

# New project:
export ORG_ID=your-org-id
export BILLING_ACCOUNT=your-billing-account-id
bash deploy-full.sh

# Or existing project:
export GOOGLE_CLOUD_PROJECT=your-project-id
bash deploy-full.sh
```

To grant a demo presenter console access (BigQuery, Knowledge Catalog,
Agent Engine), pass `--demo-user`:

```bash
bash deploy-full.sh --demo-user=presenter@example.com
```

This grants the user viewer/editor roles so they can browse tables, catalog
entries, and agents in the Google Cloud Console during a demo. End users who
only access the website do not need this — the website handles auth via OAuth.

This single script handles everything: project creation, API enablement,
128 BigQuery tables, all Knowledge Catalog resources (glossary, scans, aspects,
lineage, data products, rule library, insights), and deploying 3 agents to
Vertex AI Agent Engine with BigQuery Agent Analytics.

### Manual Step-by-Step Deploy

#### Step 1: Create the GCP Project

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
# Choose an environment (dev or prod) and fill in its project ID:
#   edit env/dev.tfvars  (or env/prod.tfvars)
# Then deploy (defaults to dev):
export ENVIRONMENT=dev
bash deploy.sh        # runs bootstrap.sh (state bucket + secrets), then terragrunt
```

> **Note:** `deploy.sh` already generates `scripts/config.json` and runs `post_deploy.sh`
> at the end, so if you used this path you can skip Step 3 below. Step 3 is only needed
> for the `bq` CLI path (Option A), which does not run post-deploy automatically.

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
   - `roles/dataplex.viewer` — access Knowledge Catalog entries (Dataplex API)
   - `roles/dataplex.catalogEditor` — search Knowledge Catalog entries
   - `roles/datalineage.viewer` — read data lineage
2. Creates `.env` files with your project config
3. Deploys each agent via `adk deploy agent_engine`
4. Prints the Agent Engine console URL

## Cloud Build CI/CD (Optional)

For automated deployments, set up a Cloud Build CI pipeline that runs Terraform
plan on PRs and apply on merge to main. This is **optional** — the manual deploy
paths above work without Cloud Build.

See `docs/ci-setup.md` (local, not committed) for the full setup runbook:
1. Create a CI hub project with two env-scoped service accounts
2. Connect GitHub via OAuth (one-time, in the Cloud Console)
3. Create triggers that use `cloudbuild.yaml`

Once configured:
- **PR to main** (changing `stacks/`, `modules/`, or `env/`): runs `terragrunt plan`
  and posts the diff as a PR comment
- **Push to main**: auto-applies infrastructure changes to dev

### Tag-based promotion to prod

```bash
# After verifying on dev, promote to prod:
git tag v1.0.0
git push origin v1.0.0
# → cloudbuild-release.yaml fires: ancestor check → infra → agents → website
```

The release pipeline verifies the tagged commit is on `main` before deploying.
Rollback by re-running an earlier tag.

### `--with-ci` bootstrap

```bash
# After a manual deploy, optionally bootstrap for CI:
bash deploy-full.sh --with-ci
# → runs the normal deploy, then creates the state bucket + secrets
# → prints instructions for completing the CI hub setup
```

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
- All 128 table names listed in the system prompt
- Same `run_sql` tool
- Struggles with table selection, cross-domain queries, and ambiguity

### KC-Guided Agent (`agents/agent_kc/`)
- No hardcoded table list — discovers tables dynamically
- Uses Knowledge Catalog MCP tools: `search_entries`, `lookup_context`, `lookup_entry`
- `run_sql` for BigQuery after discovering the right tables
- Cites glossary terms, data quality scores, and lineage in answers
- Uses native Knowledge Catalog REST API calls (no external MCP Toolbox binary needed)

## Website Authentication (Optional)

The demo website supports Google Sign-In via OAuth 2.0. Without it, the site
is open to anyone who has the URL. With it, users must sign in with a Google
account before they can interact with the agents.

### Creating an OAuth Client ID

1. Open the [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials) page for your project.

2. If you haven't configured the **OAuth consent screen** yet:
   - Click **OAuth consent screen** in the left nav.
   - Choose **Internal** (restricts to your Google Workspace org) or **External** (allows any Google account).
   - Fill in the required fields: **App name**, **User support email**, and **Developer contact email**.
   - Click **Save and Continue** through the remaining steps (Scopes, Test Users). No scopes need to be added — the app only uses the ID token for identity.

3. Go back to **Credentials** and click **+ Create Credentials → OAuth client ID**.
   - Application type: **Web application**
   - Name: `FSI KC Demo` (or any name you prefer)
   - **Authorized JavaScript origins**: Add the Cloud Run URL from your deployment output (e.g. `https://fsi-kc-demo-ui-live-xxxxx-uc.a.run.app`). If running locally, also add `http://localhost:8080`.
   - Leave **Authorized redirect URIs** empty — the app uses Google Identity Services (popup/one-tap), not a server-side redirect flow.
   - Click **Create**.

4. Copy the **Client ID** (looks like `123456789-abcdef.apps.googleusercontent.com`).

### Deploying with OAuth

Pass the client ID as an environment variable when deploying:

```bash
export OAUTH_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
bash website-live/deploy.sh
```

Or as part of the full deploy:

```bash
export OAUTH_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
bash deploy-full.sh
```

After deployment, the deploy script will remind you to add the Cloud Run URL as
an authorized JavaScript origin if you haven't already.

### Updating the Authorized Origin After Deploy

The Cloud Run URL isn't known until after the first deploy. To update it:

1. Go to [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. Click your OAuth client ID.
3. Under **Authorized JavaScript origins**, add the Cloud Run URL printed at the end of the deploy.
4. Click **Save**. Changes take effect within a few minutes.

### Required Org Policies

Cloud Run must accept unauthenticated requests so users can reach the Google
Sign-In page. If your organization enforces restrictive policies, you need to
override two policies at the project level:

```bash
PROJECT_NUMBER=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT --format='value(projectNumber)')

# 1. Allow unauthenticated Cloud Run invocations (the app handles auth via Google Sign-In)
gcloud org-policies set-policy --project=$GOOGLE_CLOUD_PROJECT /dev/stdin <<POLICY
name: projects/${PROJECT_NUMBER}/policies/run.managed.requireInvokerIam
spec:
  rules:
  - enforce: false
POLICY

# 2. Allow allUsers in IAM bindings (required for Cloud Run public access)
gcloud org-policies set-policy --project=$GOOGLE_CLOUD_PROJECT /dev/stdin <<POLICY
name: projects/${PROJECT_NUMBER}/policies/iam.allowedPolicyMemberDomains
spec:
  rules:
  - allowAll: true
POLICY

# 3. Wait ~10 seconds for propagation, then allow public access
sleep 10
gcloud run services add-iam-policy-binding fsi-kc-demo-ui-live \
  --region=$GOOGLE_CLOUD_LOCATION --member=allUsers --role=roles/run.invoker
```

These overrides are safe when OAuth is configured — the app requires Google Sign-In
before granting access to agent functionality. Without these overrides, the site
returns `403 Forbidden` even for authenticated users, because Cloud Run rejects
the request before it reaches the application's own auth layer.

### Running Without OAuth

If `OAUTH_CLIENT_ID` is not set (the default), the website runs without
authentication. All endpoints are publicly accessible to anyone with the URL.

## Snowflake Integration (Optional)

The demo optionally integrates with Snowflake to demonstrate Knowledge Catalog's
multi-cloud data discovery. A 4th source system — NEXUS, an external market data
provider — lives in Snowflake. The KC agent discovers NEXUS data through KC and
queries both BigQuery and Snowflake in a single response.

See `snowflake/README.md` for full setup instructions.

### Quick Start

```bash
# Set Snowflake credentials (setup user)
export SNOWFLAKE_ACCOUNT=your-account-id
export SNOWFLAKE_USER=FSI_KC_SETUP
export SNOWFLAKE_PASSWORD=your-setup-password

# Set agent credentials (read-only user, created after setup)
export SNOWFLAKE_AGENT_USER=FSI_KC_AGENT
export SNOWFLAKE_AGENT_PASSWORD=your-agent-password

# Deploy everything including Snowflake
bash deploy-full.sh
```

Without `SNOWFLAKE_ACCOUNT` set, the Snowflake integration is skipped entirely
and the demo works exactly as before with BigQuery only.

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
