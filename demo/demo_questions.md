# FSI Knowledge Catalog Demo — Curated Questions

Use these questions to demonstrate the three-agent progression.
Run the same question against all three agents to show the divergence.

## Tier 1: Simple Questions (Basic Agent succeeds)

These questions map cleanly to the 5 gold tables the basic agent knows about.

1. "What are the top 10 customers by total deposit balance?"
2. "Show me our loan portfolio breakdown by loan type"
3. "What is our total assets, liabilities, and equity?"
4. "Which customer segment has the highest average relationship value?"
5. "How many active checking vs savings accounts do we have?"

## Tier 2: Ambiguous Questions (Scaled Agent struggles)

These questions require understanding which of 150+ tables to use.
The scaled agent will often pick the wrong table or hallucinate columns.

6. "What's our exposure to the technology sector?"
   → Requires checking BOTH lending (loans by NAICS) AND wealth (holdings by sector)
   → Scaled agent typically only checks one

7. "Show me suspicious activity trends"
   → Multiple relevant tables: fraud_alerts, compliance_cases, aml_risk_scoring
   → Scaled agent often picks the wrong one or hallucinates a "suspicious_activity" table

8. "What's our customer attrition rate?"
   → Needs to join accounts (dormancy) + wm_clients (status) + transactions (last activity)
   → Scaled agent struggles to compose the right multi-table query

9. "How are our advisors performing?"
   → advisor_scorecard exists in gold, but also advisors, performance, trades in silver
   → Scaled agent may query raw bronze tables instead of the pre-built scorecard

10. "What's our interest rate risk?"
    → Could be: net_interest_margin, interest_rates, market_risk_var, or capital_adequacy
    → Scaled agent often picks just one dimension

## Tier 3: Cross-Domain Questions (Only KC Agent succeeds)

These questions span multiple source systems and require Knowledge Catalog
to discover the right tables and understand their relationships.

11. "For our high-net-worth clients, what's their total relationship value including both deposits and investments?"
    → Requires: gold_customer_360 (joins retail + wealth) — KC discovers this via semantic search
    → Scaled agent might try to manually join silver_customers + silver_wm_clients and miss the pre-built gold table

12. "Which branches have the highest combined retail AND wealth revenue?"
    → Requires: gold_branch_performance + portfolio data — KC discovers the cross-domain view
    → Scaled agent typically only finds branch_performance (retail only)

13. "Show me the capital impact of our commercial real estate loan concentration"
    → Requires: gold_delinquency_analysis (CRE loans) + gold_capital_adequacy + gold_loan_portfolio_summary
    → KC agent finds all three through semantic search and understands the relationship

14. "Are we compliant with all regulatory requirements? Show me any issues."
    → Requires: gold_regulatory_dashboard (consolidated view) — KC discovers this
    → Scaled agent might query individual tables (kyc_records, regulatory_filings, capital) separately

15. "What would happen to our capital ratios if our CRE loans experienced 5% more defaults?"
    → Requires: stress_tests + capital_adequacy + loan_portfolio_summary
    → KC agent uses lineage to trace the relationship and combines multiple gold tables

## Demo Script Tips

- Run questions 1-2 on all three agents to establish baseline (all succeed)
- Run questions 6-7 to show scaled agent failure (picks wrong tables)
- Run questions 11-12 to show KC agent's discovery advantage
- Highlight the KC agent's metadata citations (glossary terms, DQ scores, lineage)
- Show the Knowledge Catalog UI alongside the agent responses
