#!/usr/bin/env python3
"""Iterative prompt improvement loop for FSI KC agents.

Analyzes eval failures, generates targeted prompt improvements via Gemini,
and optionally applies them for re-evaluation.

Usage:
    python eval/improve.py                                  # Diagnose latest eval
    python eval/improve.py --apply                          # Apply suggestions + re-run failures
    python eval/improve.py --results eval_20260605.json     # Analyze specific run
    python eval/improve.py --agent kc                       # Focus on one agent
    python eval/improve.py --dry-run                        # Show suggestions, don't apply
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from google import genai

AGENT_FILES = {
    "basic": Path(__file__).parent.parent / "agents" / "agent_basic" / "agent.py",
    "scaled": Path(__file__).parent.parent / "agents" / "agent_scaled" / "agent.py",
    "kc": Path(__file__).parent.parent / "agents" / "agent_kc" / "agent.py",
}
REPORT_DIR = Path(__file__).parent / "reports"
MODEL = os.environ.get("IMPROVE_MODEL", "gemini-3.1-pro-preview")


@dataclass
class Failure:
    case_id: str
    question: str
    failure_type: str
    detail: str
    expected: dict = field(default_factory=dict)
    actual: dict = field(default_factory=dict)


@dataclass
class Suggestion:
    target_text: str
    replacement: str
    rationale: str
    fixes_cases: list[str] = field(default_factory=list)


def load_eval_results(path: str | None) -> list[dict]:
    if path:
        p = Path(path)
        if not p.exists():
            p = REPORT_DIR / path
    else:
        jsons = sorted(REPORT_DIR.glob("eval_*.json"))
        if not jsons:
            print("ERROR: No eval results found in eval/reports/")
            sys.exit(1)
        p = jsons[-1]
        print(f"Using latest eval: {p.name}")

    with open(p) as f:
        return json.load(f)


def diagnose_failures(results: list[dict], agent: str, threshold: float = 0.8) -> list[Failure]:
    failures = []
    for r in results:
        agent_data = r.get("agents", {}).get(agent)
        if not agent_data:
            continue

        scores = agent_data.get("scores", {})
        outcome = scores.get("outcome", {})

        if outcome.get("value", 1.0) >= threshold:
            continue

        table_sel = scores.get("table_selection", {})
        data_resp = scores.get("data_in_response", {})
        glossary = scores.get("glossary_citation", {})
        structure = scores.get("response_structure", {})
        graceful = scores.get("graceful_failure", {})

        if table_sel.get("value", 1.0) < 0.8:
            failures.append(Failure(
                case_id=r["case_id"],
                question=r["question"],
                failure_type="wrong_table",
                detail=table_sel.get("reason", ""),
                expected={"tables": r.get("tags", {})},
                actual={
                    "tables_queried": agent_data.get("tables_queried", []),
                    "tool_calls": agent_data.get("tool_calls", []),
                    "table_selection_reason": table_sel.get("reason", ""),
                },
            ))
        elif data_resp.get("value", 1.0) < 0.5:
            failures.append(Failure(
                case_id=r["case_id"],
                question=r["question"],
                failure_type="no_data",
                detail=data_resp.get("reason", ""),
            ))
        elif glossary.get("value", 1.0) < 0.8 and agent == "kc":
            failures.append(Failure(
                case_id=r["case_id"],
                question=r["question"],
                failure_type="missed_glossary",
                detail=glossary.get("reason", ""),
            ))
        elif graceful and graceful.get("value", 1.0) == 0.0:
            failures.append(Failure(
                case_id=r["case_id"],
                question=r["question"],
                failure_type="no_graceful_fail",
                detail="Agent did not acknowledge limitation",
            ))
        else:
            failures.append(Failure(
                case_id=r["case_id"],
                question=r["question"],
                failure_type="low_outcome",
                detail=outcome.get("reason", ""),
            ))

    return failures


def extract_system_instruction(agent_file: Path) -> str:
    content = agent_file.read_text()
    match = re.search(
        r'SYSTEM_INSTRUCTION\s*=\s*f?"""(.*?)"""',
        content,
        re.DOTALL,
    )
    if not match:
        match = re.search(
            r"SYSTEM_INSTRUCTION\s*=\s*f?'''(.*?)'''",
            content,
            re.DOTALL,
        )
    if match:
        return match.group(1)
    return ""


def generate_suggestions(
    failures: list[Failure],
    current_prompt: str,
    agent: str,
) -> list[Suggestion]:
    failure_text = ""
    for f in failures:
        failure_text += f"\n### Case: {f.case_id}\n"
        failure_text += f"Question: {f.question}\n"
        failure_text += f"Failure type: {f.failure_type}\n"
        failure_text += f"Detail: {f.detail}\n"
        if f.actual:
            failure_text += f"Actual behavior: {json.dumps(f.actual, indent=2)}\n"

    meta_prompt = f"""You are a prompt engineering assistant specializing in data analytics agents.

Below is the current system instruction for the "{agent}" agent, followed by a list of
specific evaluation failures. Your job is to suggest minimal, targeted edits to the
system instruction that would fix these failures without breaking other cases.

## Current System Instruction

```
{current_prompt}
```

## Failures to Fix

{failure_text}

## Instructions

For each suggested change, output a JSON object with these fields:
- "target_text": the exact substring in the current prompt to find (must match exactly)
- "replacement": the replacement text
- "rationale": why this change fixes the failures
- "fixes_cases": list of case_id values this change addresses

Output a JSON array of suggestion objects. If no changes are needed, output an empty array.

## Constraints

- Keep changes minimal — edit existing lines, don't rewrite whole sections
- Focus on search strategy guidance and table preference hints
- Don't change the response format (Data Discovery / Analysis / etc.)
- Each suggestion must be independently applicable (no dependencies between suggestions)
- Prefer adding hints to existing bullet points over creating new sections
- The prompt uses an f-string, so preserve any {{PROJECT_ID}} references exactly

Output ONLY the JSON array, no markdown fencing or explanation."""

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "fsi-kc-demo-dev")
    client = genai.Client(vertexai=True, project=project, location="global")

    print(f"  Calling {MODEL} for suggestions...")
    response = client.models.generate_content(
        model=MODEL,
        contents=meta_prompt,
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        suggestions_data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  WARNING: Could not parse Gemini response as JSON")
        print(f"  Raw response: {raw[:500]}")
        return []

    suggestions = []
    for s in suggestions_data:
        suggestions.append(Suggestion(
            target_text=s.get("target_text", ""),
            replacement=s.get("replacement", ""),
            rationale=s.get("rationale", ""),
            fixes_cases=s.get("fixes_cases", []),
        ))

    return suggestions


def apply_suggestions(suggestions: list[Suggestion], agent_file: Path) -> int:
    content = agent_file.read_text()
    applied = 0

    for s in suggestions:
        if not s.target_text or not s.replacement:
            continue
        if s.target_text not in content:
            print(f"  SKIP: target text not found: {s.target_text[:60]}...")
            continue
        if s.target_text == s.replacement:
            continue

        content = content.replace(s.target_text, s.replacement, 1)
        applied += 1
        print(f"  APPLIED: {s.rationale[:80]}")

    if applied:
        agent_file.write_text(content)

    return applied


def verify_improvements(failing_case_ids: list[str], agent: str) -> dict:
    results = {}
    for case_id in failing_case_ids:
        print(f"  Re-running {case_id}...", end="", flush=True)
        cmd = [
            sys.executable, str(Path(__file__).parent / "run_eval.py"),
            "--case", case_id,
            "--agents", agent,
        ]
        env = os.environ.copy()
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)

        score_match = re.search(r"\[([+~-])\]\s+([\d.]+)\s+\(([^)]+)\)", result.stdout)
        if score_match:
            symbol, value, reason = score_match.groups()
            results[case_id] = {"value": float(value), "reason": reason, "symbol": symbol}
            print(f" [{symbol}] {value} ({reason})")
        else:
            results[case_id] = {"value": 0.0, "reason": "parse error", "symbol": "?"}
            print(f" [?] Could not parse result")

    return results


def print_diagnosis(failures: list[Failure], agent: str):
    print(f"\n{'=' * 60}")
    print(f"  Diagnosis for {agent} agent: {len(failures)} failures")
    print(f"{'=' * 60}\n")

    by_type = {}
    for f in failures:
        by_type.setdefault(f.failure_type, []).append(f)

    for ftype, items in sorted(by_type.items()):
        print(f"  {ftype} ({len(items)} cases):")
        for f in items:
            print(f"    - {f.case_id}: {f.detail[:80]}")
        print()


def print_suggestions(suggestions: list[Suggestion]):
    print(f"\n{'=' * 60}")
    print(f"  {len(suggestions)} suggested prompt changes")
    print(f"{'=' * 60}\n")

    for i, s in enumerate(suggestions, 1):
        print(f"  [{i}] {s.rationale}")
        print(f"      Fixes: {', '.join(s.fixes_cases)}")
        print(f"      Target:  {s.target_text[:80]}...")
        print(f"      Replace: {s.replacement[:80]}...")
        print()


def main():
    parser = argparse.ArgumentParser(description="Iterative prompt improvement loop")
    parser.add_argument("--results", help="Path to eval JSON results file (default: latest)")
    parser.add_argument("--agent", default="kc", help="Agent to improve (default: kc)")
    parser.add_argument("--apply", action="store_true", help="Apply suggestions and re-run failures")
    parser.add_argument("--dry-run", action="store_true", help="Show suggestions without applying")
    parser.add_argument("--threshold", type=float, default=0.8, help="Outcome threshold for failure (default: 0.8)")
    args = parser.parse_args()

    if args.agent not in AGENT_FILES:
        print(f"ERROR: Unknown agent '{args.agent}'. Choose from: {', '.join(AGENT_FILES)}")
        sys.exit(1)

    results = load_eval_results(args.results)
    failures = diagnose_failures(results, args.agent, args.threshold)

    if not failures:
        print(f"\nNo failures found for {args.agent} agent (threshold={args.threshold})")
        return

    print_diagnosis(failures, args.agent)

    agent_file = AGENT_FILES[args.agent]
    current_prompt = extract_system_instruction(agent_file)
    if not current_prompt:
        print(f"ERROR: Could not extract SYSTEM_INSTRUCTION from {agent_file}")
        sys.exit(1)

    suggestions = generate_suggestions(failures, current_prompt, args.agent)

    if not suggestions:
        print("\nNo suggestions generated.")
        return

    print_suggestions(suggestions)

    if args.dry_run:
        print("(dry-run mode — no changes applied)")
        return

    if not args.apply:
        print("Run with --apply to apply these suggestions, or --dry-run to preview only.")
        return

    print(f"\n{'=' * 60}")
    print(f"  Applying suggestions to {agent_file.name}")
    print(f"{'=' * 60}\n")

    applied = apply_suggestions(suggestions, agent_file)
    print(f"\n  {applied} of {len(suggestions)} suggestions applied.")

    if applied == 0:
        return

    failing_ids = [f.case_id for f in failures]
    print(f"\n{'=' * 60}")
    print(f"  Verifying improvements ({len(failing_ids)} cases)")
    print(f"{'=' * 60}\n")

    before_scores = {f.case_id: f.detail for f in failures}
    after_scores = verify_improvements(failing_ids, args.agent)

    print(f"\n{'=' * 60}")
    print(f"  Before / After Comparison")
    print(f"{'=' * 60}\n")

    improved = 0
    regressed = 0
    for case_id in failing_ids:
        after = after_scores.get(case_id, {})
        after_val = after.get("value", 0.0)
        status = "IMPROVED" if after_val >= args.threshold else "still failing"
        if after_val >= args.threshold:
            improved += 1
        print(f"  {case_id:35s} → {after_val:.1f} [{after.get('symbol', '?')}] {status}")

    print(f"\n  Summary: {improved}/{len(failing_ids)} cases improved to threshold")


if __name__ == "__main__":
    main()
