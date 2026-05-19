"""Vertex AI LLM-judged evaluation for FSI KC agent evaluation.

Uses vertexai.evaluation.EvalTask with PointwiseMetric to run
LLM-judged scoring on agent responses. Called when --use-vertex-eval
flag is passed to run_eval.py.
"""

import sys
from pathlib import Path

import pandas as pd
import vertexai
from vertexai.evaluation import EvalTask, PointwiseMetric, PointwiseMetricPromptTemplate

sys.path.insert(0, str(Path(__file__).parent))
from metrics import Score

VERTEX_METRICS = [
    "vertex_response_quality",
    "vertex_tool_use_quality",
    "vertex_hallucination",
    "vertex_task_success",
]


def _response_quality_metric() -> PointwiseMetric:
    return PointwiseMetric(
        metric="response_quality",
        metric_prompt_template=PointwiseMetricPromptTemplate(
            metric_definition=(
                "Evaluates the overall quality of an FSI data agent's response, "
                "including factual accuracy, data completeness, and relevance to the question."
            ),
            criteria={
                "1": "Incorrect, empty, or completely irrelevant response",
                "2": "Partially relevant but missing critical financial data or metrics",
                "3": "Adequate response with basic data but lacking depth",
                "4": "Good response with comprehensive financial data and context",
                "5": "Excellent response with complete, accurate data and expert-level FSI insight",
            },
            rating_rubric={
                "1": "Response fails to address the question, contains no relevant data, or has major factual errors",
                "2": "Response mentions the topic but omits key metrics, dollar amounts, or percentages that were requested",
                "3": "Response includes some relevant data (numbers, tables) but misses important aspects of the question",
                "4": "Response provides thorough financial data with proper context, covering most aspects of the question",
                "5": "Response fully addresses the question with precise financial data, proper context, and actionable insights",
            },
            input_variables=["instruction", "response"],
        ),
    )


def _tool_use_quality_metric() -> PointwiseMetric:
    return PointwiseMetric(
        metric="tool_use_quality",
        metric_prompt_template=PointwiseMetricPromptTemplate(
            metric_definition=(
                "Evaluates whether the agent selected appropriate tools and data tables "
                "to answer an FSI question. The 'context' field lists the tools called and "
                "tables queried by the agent."
            ),
            criteria={
                "1": "No tools used or completely wrong tool/table selection",
                "2": "Used some tools but selected wrong or low-quality tables",
                "3": "Acceptable tool usage but not optimal table selection",
                "4": "Good tool strategy with appropriate table selection",
                "5": "Optimal tool usage — correct gold/silver tables for the domain",
            },
            rating_rubric={
                "1": "Agent did not call any tools, or used tools that are irrelevant to the question",
                "2": "Agent used tools but queried bronze tables when gold/silver were available, or wrong domain tables",
                "3": "Agent queried relevant tables but missed the most appropriate one for the question",
                "4": "Agent selected high-quality tables (gold/silver) that align well with the question's domain",
                "5": "Agent selected the optimal set of gold tables with efficient tool usage and correct domain coverage",
            },
            input_variables=["instruction", "response", "context"],
        ),
    )


def _hallucination_metric() -> PointwiseMetric:
    return PointwiseMetric(
        metric="hallucination",
        metric_prompt_template=PointwiseMetricPromptTemplate(
            metric_definition=(
                "Evaluates whether the agent's response contains fabricated or unsupported "
                "financial data, metrics, or claims. The 'context' field shows what tools and "
                "tables the agent actually queried."
            ),
            criteria={
                "1": "Severe hallucination — fabricated financial data or metrics",
                "2": "Contains claims not supported by the queried data sources",
                "3": "Mostly grounded but includes minor unsupported details",
                "4": "Well-grounded response with only minor interpretive liberties",
                "5": "Fully grounded — all data and claims traceable to queried sources",
            },
            rating_rubric={
                "1": "Response invents specific dollar amounts, percentages, or metrics that could not come from the listed data sources",
                "2": "Response makes quantitative claims or references tables/data not listed in the context",
                "3": "Response is mostly factual but includes some details that seem added beyond what the sources would provide",
                "4": "Response stays close to what the queried sources would contain, with only reasonable inferences",
                "5": "All specific numbers, metrics, and facts in the response are consistent with the data sources queried",
            },
            input_variables=["instruction", "response", "context"],
        ),
    )


def _task_success_metric() -> PointwiseMetric:
    return PointwiseMetric(
        metric="task_success",
        metric_prompt_template=PointwiseMetricPromptTemplate(
            metric_definition=(
                "Evaluates whether the agent successfully completed the user's requested "
                "task. For FSI data questions, success means providing the requested analysis "
                "or acknowledging inability when data is unavailable."
            ),
            criteria={
                "1": "Complete failure — did not address the question at all",
                "2": "Minimal attempt — acknowledged the question but provided no useful output",
                "3": "Partial success — addressed some aspects but left key parts unanswered",
                "4": "Mostly successful — answered the core question with minor gaps",
                "5": "Full success — completely addressed the question or clearly explained limitations",
            },
            rating_rubric={
                "1": "Response is empty, an error message, or completely off-topic",
                "2": "Response shows awareness of the topic but provides no data or actionable content",
                "3": "Response answers part of the question but omits important requested elements",
                "4": "Response addresses the main question with relevant data, missing only minor details",
                "5": "Response fully satisfies the request with all requested data, or provides a clear, helpful explanation of why the data is unavailable",
            },
            input_variables=["instruction", "response"],
        ),
    )


def _build_eval_dataset(case_results: list[dict]) -> pd.DataFrame:
    rows = []
    for cr in case_results:
        result = cr["result"]
        context_parts = []
        if result.tool_calls:
            context_parts.append(f"Tools called: {', '.join(result.tool_calls)}")
        if result.tables_queried:
            context_parts.append(f"Tables queried: {', '.join(result.tables_queried)}")
        context = "; ".join(context_parts) if context_parts else "No tools were called"

        rows.append({
            "case_id": cr["case_id"],
            "instruction": cr["question"],
            "response": result.response_text or "(empty response)",
            "context": context,
        })
    return pd.DataFrame(rows)


def run_vertex_eval(
    all_results: list[dict],
    agents_to_run: list[str],
    project_id: str,
    location: str,
) -> None:
    """Run Vertex AI evaluation and merge scores into all_results in-place.

    Runs one EvalTask per agent type in BYOR (bring-your-own-response) mode.
    Scores are added as vertex_* keys in each agent's scores dict.
    """
    vertexai.init(project=project_id, location=location)

    metrics = [
        _response_quality_metric(),
        _tool_use_quality_metric(),
        _hallucination_metric(),
        _task_success_metric(),
    ]
    metric_names = ["response_quality", "tool_use_quality", "hallucination", "task_success"]

    for agent_type in agents_to_run:
        agent_cases = []
        for cr in all_results:
            if agent_type not in cr["agents"]:
                continue
            data = cr["agents"][agent_type]
            if data["result"].error:
                continue
            agent_cases.append({
                "case_id": cr["case"]["id"],
                "question": cr["case"]["question"],
                "result": data["result"],
            })

        if not agent_cases:
            continue

        print(f"  {agent_type}: evaluating {len(agent_cases)} cases...", end="", flush=True)

        try:
            df = _build_eval_dataset(agent_cases)
            eval_task = EvalTask(dataset=df, metrics=metrics)
            eval_result = eval_task.evaluate()
            _merge_scores(all_results, agent_type, agent_cases, eval_result, metric_names)
            print(f" done")
        except Exception as e:
            print(f" FAILED: {e}")


def _merge_scores(
    all_results: list[dict],
    agent_type: str,
    agent_cases: list[dict],
    eval_result,
    metric_names: list[str],
) -> None:
    metrics_table = eval_result.metrics_table
    case_id_list = [c["case_id"] for c in agent_cases]
    case_id_to_idx = {cid: i for i, cid in enumerate(case_id_list)}

    results_by_case_id = {}
    for cr in all_results:
        results_by_case_id[cr["case"]["id"]] = cr

    for case_id, row_idx in case_id_to_idx.items():
        if case_id not in results_by_case_id:
            continue
        cr = results_by_case_id[case_id]
        if agent_type not in cr["agents"]:
            continue

        scores = cr["agents"][agent_type]["scores"]
        row = metrics_table.iloc[row_idx]

        for metric_name in metric_names:
            score_col = f"{metric_name}/score"
            expl_col = f"{metric_name}/explanation"

            if score_col not in row.index:
                continue

            raw_score = row[score_col]
            if pd.isna(raw_score):
                continue

            normalized = round((float(raw_score) - 1.0) / 4.0, 2)
            explanation = ""
            if expl_col in row.index and not pd.isna(row[expl_col]):
                explanation = str(row[expl_col])[:200]
            if not explanation:
                explanation = f"LLM score: {raw_score}/5"

            scores[f"vertex_{metric_name}"] = Score(
                value=max(0.0, min(1.0, normalized)),
                reason=explanation,
            )
