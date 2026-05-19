#!/usr/bin/env python3
"""FSI Knowledge Catalog Agent Evaluation Runner.

Runs test cases against all 3 agents, scores results with custom metrics,
and generates comparison reports.

Usage:
    python eval/run_eval.py                          # Run all cases
    python eval/run_eval.py --case top_customers     # Single case
    python eval/run_eval.py --filter audience=wealth_management
    python eval/run_eval.py --agents basic,kc        # Specific agents only
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import google.auth
import google.auth.transport.requests
import requests as http_requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from metrics import score_all

AE_BASE = "https://{location}-aiplatform.googleapis.com/v1"

_BASE_SUFFIXES = [
    "customers", "accounts", "transactions", "loans", "loan_payments", "credit_cards",
    "card_transactions", "fraud_alerts", "kyc_records", "branches", "employees",
    "wire_transfers", "ach_transfers", "atm_transactions", "wm_clients", "portfolios",
    "holdings", "trades", "securities", "advisors", "performance", "fee_schedules",
    "benchmarks", "client_goals", "risk_profiles", "distributions", "custodian_feeds",
    "gl_entries", "gl_accounts", "cost_centers", "regulatory_capital", "risk_exposures",
    "counterparties", "market_data", "stress_tests", "audit_events", "regulatory_filings",
    "interest_rates", "fx_rates", "compliance_cases",
]
ALL_TABLE_NAMES = (
    [f"bronze_{s}" for s in _BASE_SUFFIXES]
    + [f"silver_{s}" for s in _BASE_SUFFIXES]
    + [
        "gold_customer_360", "gold_account_summary", "gold_transaction_patterns",
        "gold_loan_portfolio_summary", "gold_delinquency_analysis", "gold_fraud_analytics",
        "gold_aml_risk_scoring", "gold_branch_performance", "gold_portfolio_performance",
        "gold_client_revenue", "gold_asset_allocation", "gold_advisor_scorecard",
        "gold_fee_revenue", "gold_net_interest_margin", "gold_capital_adequacy",
        "gold_liquidity_coverage", "gold_market_risk_var", "gold_operational_risk",
        "gold_regulatory_dashboard", "gold_balance_sheet_summary",
        "vw_dq_scorecard", "vw_dq_by_dimension", "vw_dq_failed_rules", "vw_dq_rule_detail",
        "vw_profile_summary", "vw_customer_total_relationship", "vw_branch_retail_wealth",
        "vw_regulatory_summary",
        "ref_naics_codes", "ref_country_codes", "ref_currency_codes", "ref_cusip_master",
        "ref_isin_mapping", "ref_lei_registry", "ref_fed_district_codes", "ref_product_catalog",
        "staging_call_report_rc", "staging_call_report_ri", "staging_fr_y9c",
        "snapshot_monthly_balances", "snapshot_quarterly_positions", "audit_data_access_log",
    ]
)


@dataclass
class AgentResult:
    agent: str
    tool_calls: list[str] = field(default_factory=list)
    tables_queried: list[str] = field(default_factory=list)
    response_text: str = ""
    latency: float = 0.0
    error: str = ""


_token_cache = {"token": None, "expires": 0}


def _get_token():
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires"]:
        return _token_cache["token"]
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    _token_cache["token"] = creds.token
    _token_cache["expires"] = now + 250
    return creds.token


def _get_project_number(project_id):
    try:
        result = subprocess.run(
            ["gcloud", "projects", "describe", project_id, "--format=value(projectNumber)"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _extract_tables(text):
    return list({t for t in ALL_TABLE_NAMES if t in text.lower()})


def query_agent(agent_id: str, question: str, project_number: str,
                location: str) -> AgentResult:
    base = AE_BASE.format(location=location)
    url_base = f"{base}/projects/{project_number}/locations/{location}/reasoningEngines/{agent_id}"
    result = AgentResult(agent=agent_id)
    start = time.time()

    try:
        token = _get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Create session
        resp = http_requests.post(
            f"{url_base}:query",
            headers=headers,
            json={"class_method": "create_session", "input": {"user_id": "eval_runner"}},
            timeout=30,
        )
        if resp.status_code != 200:
            result.error = f"Session creation failed: {resp.status_code}"
            result.latency = time.time() - start
            return result

        output = resp.json().get("output", {})
        session_id = output.get("id", "") if isinstance(output, dict) else str(output)

        # Stream query
        resp = http_requests.post(
            f"{url_base}:streamQuery",
            headers=headers,
            json={"input": {"message": question, "user_id": "eval_runner", "session_id": session_id}},
            stream=True, timeout=120,
        )
        if resp.status_code != 200:
            result.error = f"Query failed: {resp.status_code}"
            result.latency = time.time() - start
            return result

        all_tables = []
        for line in resp.iter_lines():
            if not line:
                continue
            text = line.decode("utf-8").strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue

            for part in data.get("content", {}).get("parts", []):
                if "function_call" in part:
                    fc = part["function_call"]
                    result.tool_calls.append(fc.get("name", ""))
                    all_tables.extend(_extract_tables(str(fc.get("args", {}))))
                elif "function_response" in part:
                    fr = part["function_response"]
                    resp_data = fr.get("response", {})
                    result_text = resp_data.get("result", str(resp_data))
                    all_tables.extend(_extract_tables(result_text))
                elif "text" in part:
                    result.response_text += part["text"]

        result.tables_queried = list(set(all_tables))
        result.latency = time.time() - start

    except Exception as e:
        result.error = str(e)
        result.latency = time.time() - start

    return result


def load_config(yaml_path: str) -> dict:
    with open(yaml_path) as f:
        raw = f.read()

    for var in re.findall(r"\$\{(\w+)\}", raw):
        val = os.environ.get(var, "")
        raw = raw.replace(f"${{{var}}}", val)

    return yaml.safe_load(raw)


def run_evaluation(args):
    config = load_config(args.config)
    project_id = config["config"]["project_id"]
    location = config["config"]["location"]
    agent_ids = config["config"]["agents"]
    project_number = _get_project_number(project_id)

    if not project_number:
        print(f"ERROR: Could not resolve project number for {project_id}")
        sys.exit(1)

    if args.basic_id:
        agent_ids["basic"] = args.basic_id
    if args.scaled_id:
        agent_ids["scaled"] = args.scaled_id
    if args.kc_id:
        agent_ids["kc"] = args.kc_id

    agents_to_run = args.agents.split(",") if args.agents else ["basic", "scaled", "kc"]

    cases = config["cases"]
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"ERROR: No case found with id '{args.case}'")
            sys.exit(1)

    if args.filter:
        for f in args.filter.split(","):
            if "=" not in f:
                continue
            dim, vals = f.split("=", 1)
            val_set = set(vals.split("|"))
            cases = [c for c in cases if c.get("tags", {}).get(dim) in val_set]
        if not cases:
            print(f"ERROR: No cases match filter '{args.filter}'")
            sys.exit(1)

    total_runs = len(cases) * len(agents_to_run)
    print(f"\n{'=' * 60}")
    print(f"  FSI Knowledge Catalog Agent Evaluation")
    print(f"  {len(cases)} cases x {len(agents_to_run)} agents = {total_runs} runs")
    print(f"  Project: {project_id}")
    print(f"{'=' * 60}\n")

    all_results = []
    for i, case in enumerate(cases):
        case_id = case["id"]
        question = case["question"]
        tags = case.get("tags", {})
        print(f"[{i+1}/{len(cases)}] {case_id}: {question[:60]}...")

        case_results = {"case": case, "agents": {}}

        for agent_type in agents_to_run:
            aid = agent_ids.get(agent_type, "")
            if not aid:
                print(f"  {agent_type}: SKIPPED (no agent ID)")
                continue

            print(f"  {agent_type}: querying...", end="", flush=True)
            result = query_agent(aid, question, project_number, location)
            expected = case.get("expected", {}).get(agent_type, {})
            scores = score_all(
                result.response_text, result.tool_calls,
                result.tables_queried, expected, agent_type,
            )

            outcome_score = scores["outcome"]
            symbol = "+" if outcome_score.value >= 0.8 else "~" if outcome_score.value >= 0.4 else "-"
            print(f" [{symbol}] {outcome_score.value:.1f} ({outcome_score.reason}) [{result.latency:.1f}s]")

            case_results["agents"][agent_type] = {
                "result": result,
                "scores": scores,
            }

        all_results.append(case_results)
        print()

    # Vertex AI LLM-judged evaluation
    if args.use_vertex_eval:
        print(f"\n{'=' * 60}")
        print(f"  Vertex AI LLM-Judged Evaluation")
        print(f"{'=' * 60}\n")
        from vertex_eval import run_vertex_eval
        run_vertex_eval(all_results, agents_to_run, project_id, location)

    # Generate reports
    from report import print_terminal_report, generate_html_report

    print_terminal_report(all_results, agents_to_run)

    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    html_path = report_dir / f"eval_{ts}.html"
    generate_html_report(all_results, agents_to_run, str(html_path))
    print(f"\nHTML report: {html_path}")

    # Save raw results as JSON
    json_path = report_dir / f"eval_{ts}.json"
    json_results = []
    for cr in all_results:
        entry = {
            "case_id": cr["case"]["id"],
            "question": cr["case"]["question"],
            "tags": cr["case"].get("tags", {}),
            "agents": {},
        }
        for agent_type, data in cr["agents"].items():
            r = data["result"]
            entry["agents"][agent_type] = {
                "tool_calls": r.tool_calls,
                "tables_queried": r.tables_queried,
                "response_length": len(r.response_text),
                "latency": round(r.latency, 1),
                "error": r.error,
                "scores": {k: {"value": s.value, "reason": s.reason} for k, s in data["scores"].items()},
            }
        json_results.append(entry)

    with open(json_path, "w") as f:
        json.dump(json_results, f, indent=2)
    print(f"JSON results: {json_path}")


def main():
    parser = argparse.ArgumentParser(description="FSI KC Agent Evaluation Runner")
    parser.add_argument("--config", default=str(Path(__file__).parent / "test_cases.yaml"))
    parser.add_argument("--case", help="Run a single test case by ID")
    parser.add_argument("--filter", help="Filter by dimension, e.g. audience=wealth_management")
    parser.add_argument("--agents", help="Comma-separated agent types to run (default: basic,scaled,kc)")
    parser.add_argument("--basic-id", help="Override basic agent ID")
    parser.add_argument("--scaled-id", help="Override scaled agent ID")
    parser.add_argument("--kc-id", help="Override KC agent ID")
    parser.add_argument("--use-vertex-eval", action="store_true",
                        help="Enable Vertex AI LLM-judged metrics alongside custom metrics")
    args = parser.parse_args()
    run_evaluation(args)


if __name__ == "__main__":
    main()
