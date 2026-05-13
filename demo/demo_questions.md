# FSI Knowledge Catalog Demo — Scenario Playbook

Run the same question against all three agents and observe the divergence.
Each scenario targets a specific failure mode that Knowledge Catalog solves.

---

## Category 1: Baseline (all 3 agents succeed)

Establishes credibility — proves all agents work when the task is simple.

### Scenario 1.1
> "What are our top 5 customers by total relationship value?"

- All succeed: `gold_customer_360` is known to all agents, simple aggregation
- **Demo point:** "All three agents work when the task is simple."

### Scenario 1.2
> "Show me our loan portfolio by product type and risk rating"

- All succeed: `gold_loan_portfolio_summary` is well-known, single table
- **Demo point:** "This isn't a model intelligence issue — it's a data discovery issue."

---

## Category 2: Table Disambiguation (Scaled agent picks wrong table)

The scaled agent sees 150+ table names but can't tell which one to use.

### Scenario 2.1 — Suspicious Activity
> "Show me suspicious activity trends over the past year"

- **Scaled failure:** Sees `bronze_fraud_alerts`, `silver_fraud_alerts`, `gold_fraud_analytics`, `silver_compliance_cases`, `gold_aml_risk_scoring` — picks one arbitrarily or hallucinates a `suspicious_activity` table
- **KC advantage:** Searches "suspicious activity" → discovers `gold_fraud_analytics` for fraud trends AND `gold_aml_risk_scoring` for BSA/AML → reads metadata to understand which is the monthly trend table → queries the right one → cites the BSA glossary term and data classification
- **Key talking point:** *"150 tables means 150 chances to pick the wrong one. The KC agent doesn't guess — it searches semantically and reads metadata to understand what each table actually contains."*

### Scenario 2.2 — Interest Rate Risk
> "What's our interest rate exposure?"

- **Scaled failure:** Sees `bronze_interest_rates`, `silver_interest_rates`, `gold_net_interest_margin`, `gold_market_risk_var`, `gold_capital_adequacy` — confused about which dimension of "interest rate" to answer
- **KC advantage:** Searches "interest rate risk" → finds `gold_net_interest_margin` for NIM analysis and `gold_market_risk_var` for VaR → reads glossary definitions of NIM and VaR → presents both dimensions with proper business context
- **Key talking point:** *"Interest rate exposure means different things to a treasurer vs. a risk officer. Knowledge Catalog's glossary gives the agent the business context to answer comprehensively."*

---

## Category 3: Cross-Domain Discovery (Scaled agent misses entire domains)

Questions that span ATLAS (retail) and FORTUNA (wealth) — two separate source systems.

### Scenario 3.1 — HNW Total Exposure
> "For our high-net-worth clients, what's their total exposure including deposits, loans, and investments?"

- **Scaled failure:** Queries only `silver_wm_clients` (wealth) OR `silver_customers` (retail), misses the pre-built `gold_customer_360` that joins both source systems
- **KC advantage:** Searches "high net worth total relationship" → discovers `gold_customer_360` which joins ATLAS + FORTUNA → reads lineage showing it aggregates across both source systems → filters to Premier/Private Banking segments → presents unified view
- **Key talking point:** *"A real bank has retail customers in one system and wealth clients in another. The KC agent discovers the gold table that already joins them — the scaled agent doesn't even know it exists."*

### Scenario 3.2 — Branch Revenue (Retail + Wealth)
> "Which branches generate the most revenue when you include both retail banking and wealth management?"

- **Scaled failure:** Finds `gold_branch_performance` but it only covers retail. Misses that wealth revenue needs to come from `gold_fee_revenue` or `gold_client_revenue`
- **KC advantage:** Searches "branch revenue" → finds both `gold_branch_performance` AND `gold_fee_revenue` → reads aspects showing different source systems → constructs a join → explains the cross-domain data lineage
- **Key talking point:** *"No branch manager sees their full P&L because the data lives in two separate systems. The KC agent discovers both and combines them."*

---

## Category 4: Regulatory & Compliance (KC agent cites governance metadata)

Questions where the answer requires not just data but regulatory context.

### Scenario 4.1 — Basel III Capital
> "Are we meeting our Basel III capital requirements? What's our buffer above the minimum?"

- **Scaled failure:** Might find `gold_capital_adequacy` but doesn't understand CET1 minimums, conservation buffers, or countercyclical buffers — presents raw numbers without regulatory context
- **KC advantage:** Searches "Basel III capital" → finds `gold_capital_adequacy` → reads glossary definitions of CET1, Basel III, risk-weighted assets → reads regulatory reporting aspect (Call Report Schedule RC-R) → presents ratios WITH regulatory context and buffer calculations → cites glossary definitions
- **Key talking point:** *"The KC agent reads the glossary to understand that CET1 minimum is 4.5% plus a 2.5% conservation buffer. That business knowledge comes from Knowledge Catalog, not the model's training data."*

### Scenario 4.2 — KYC Compliance Gaps
> "Do we have any KYC compliance gaps? Show me overdue reviews and high-risk customers."

- **Scaled failure:** May query `bronze_kyc_records` (raw data with duplicates) or miss `gold_aml_risk_scoring` entirely
- **KC advantage:** Searches "KYC compliance overdue" → discovers `gold_aml_risk_scoring` → reads glossary definitions of KYC, CDD, EDD, PEP → reads data classification (Restricted) → presents with compliance context
- **Key talking point:** *"Compliance data has to be right. The KC agent checks data quality and sensitivity classifications before answering. It tells you the data is Restricted and sourced from the ATLAS core banking system — that's governance context a compliance officer needs."*

---

## Category 5: Data Quality & Trust (KC agent assesses trustworthiness)

Questions where knowing the answer isn't enough — you need to know if you can trust it.

### Scenario 5.1 — FICO Score Trust
> "What's the average FICO score across our loan portfolio, and should we trust this number?"

- **Scaled failure:** Calculates the average but has no way to assess data quality
- **KC advantage:** Searches "FICO score loans" → finds the right tables → reads DQ rules attached to the FICO glossary term ("validated in 300-850 range") → presents the average WITH a data quality assessment
- **Key talking point:** *"Any agent can calculate an average. Only the KC agent can tell you whether to trust it. It reads the data quality rules from Knowledge Catalog and cites them in the answer."*

### Scenario 5.2 — CUSIP Data Quality
> "Show me our CUSIP-level holdings across all portfolios. Are there any data issues?"

- **Scaled failure:** Might query `silver_holdings` but can't assess quality
- **KC advantage:** Searches "CUSIP holdings" → reads CUSIP glossary term with DQ rules ("9-character alphanumeric format") → flags format validation status → presents holdings with governance notes
- **Key talking point:** *"The DQ rule attached to the CUSIP glossary term is centrally governed in Knowledge Catalog. Every agent that touches CUSIP data automatically knows the quality standard."*

---

## Category 6: The "Impossible" Question (Scaled agent completely fails)

Multi-table, multi-domain questions that require discovering relationships between data assets.

### Scenario 6.1 — CRE Stress Test
> "If commercial real estate defaults increased 5%, what would happen to our capital ratios?"

- **Scaled failure:** Has no idea which tables to combine. Requires `gold_loan_portfolio_summary` (CRE exposure) + `gold_capital_adequacy` (current ratios) + `gold_delinquency_analysis` (default rates). Agent likely hallucinates or gives up.
- **KC advantage:** Multiple searches → discovers all three tables → reads lineage to understand relationships → constructs multi-table scenario analysis → cites all sources and glossary terms
- **Key talking point:** *"This is a question a CFO asks every quarter. The scaled agent can't even figure out where to start. The KC agent discovers three tables, understands their relationships through lineage, and constructs the analysis. That's the difference between a toy agent and an enterprise agent."*

### Scenario 6.2 — Cross-Sell Opportunity
> "Which of our wealth management clients should we cross-sell a mortgage to?"

- **Scaled failure:** Requires joining wealth client data (FORTUNA) with lending data (ATLAS). Scaled agent can't reason about cross-system joins.
- **KC advantage:** Discovers `gold_customer_360` bridges both systems → queries HNW clients with high AUM but no active mortgage → presents as a cross-sell opportunity list with relationship context
- **Key talking point:** *"Cross-selling requires data from two completely separate core systems. The KC agent discovers the gold table that bridges them. Without Knowledge Catalog, you'd need a developer to hardcode that join for every use case."*

---

## Recommended Demo Flow (~20 minutes)

| Step | Scenario | What to show | Time |
|---|---|---|---|
| 1 | 1.1 — Top customers | All 3 agents succeed → baseline | 2 min |
| 2 | 1.2 — Loan portfolio | All 3 succeed → "not a model issue" | 1 min |
| 3 | 2.1 — Suspicious activity | Scaled picks wrong table → KC finds right one | 3 min |
| 4 | 3.1 — HNW total exposure | Scaled misses cross-domain → KC discovers gold table | 3 min |
| 5 | 4.1 — Basel III capital | KC cites glossary definitions & regulatory context | 3 min |
| 6 | 5.1 — FICO trust | KC cites data quality rules & trust assessment | 3 min |
| 7 | 6.1 — CRE stress test | Scaled fails completely → KC multi-table reasoning | 3 min |
| 8 | Knowledge Catalog UI | Walk through glossary, lineage, DQ in the console | 2 min |

## After Each KC Agent Answer, Highlight:

1. **"It searched before it queried"** — show the `search_entries` tool call
2. **"It chose the right table and explained why"** — table selection rationale citing metadata
3. **"It cited the glossary"** — business term definitions in the response
4. **"It checked data quality"** — DQ rules and trust assessment
5. **"It traced the lineage"** — source system attribution (ATLAS / FORTUNA / ARGUS)
6. **"It flagged sensitivity"** — data classification level in the response
