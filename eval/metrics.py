"""Custom scoring functions for FSI KC agent evaluation."""

import re
from dataclasses import dataclass


@dataclass
class Score:
    value: float  # 0.0 - 1.0
    reason: str


GLOSSARY_KEYWORDS = {
    "FICO Score": ["fico", "credit score", "fair isaac"],
    "AUM": ["aum", "assets under management"],
    "SAR": ["sar", "suspicious activity"],
    "CET1 Ratio": ["cet1", "common equity tier", "capital ratio"],
    "Customer ID": ["customer_id", "customer id", "customer identifier"],
    "Delinquency": ["delinquen", "past due", "overdue"],
    "KYC": ["kyc", "know your customer"],
    "VaR": ["var", "value at risk"],
    "CUSIP": ["cusip"],
    "Branch": ["branch"],
    "NIM": ["nim", "net interest margin"],
    "Risk Rating": ["risk rating", "risk_rating", "credit quality"],
}

METADATA_KEYWORDS = {
    "data_quality": ["data quality", "quality score", "quality rule", "dq ", "validation", "trustworth"],
    "lineage": ["lineage", "source system", "atlas", "fortuna", "argus", "db2", "mainframe", "bronze.*silver.*gold", "medallion"],
    "regulatory": ["basel", "regulatory", "compliance", "fdic", "bsa", "aml requirement"],
    "classification": ["classification", "pii", "sensitive", "restricted", "confidential"],
}


def score_table_selection(tables_queried: list[str], expected: dict) -> Score:
    right = set(expected.get("tables", []))
    wrong = set(expected.get("wrong_tables", []))
    queried = set(tables_queried)

    if not right and not wrong:
        return Score(1.0, "no table expectations defined")

    if not queried:
        return Score(0.0, "no tables queried")

    hit_right = right & queried
    hit_wrong = wrong & queried

    if right:
        # At least one expected table must be queried
        coverage = min(1.0, len(hit_right) / max(1, min(len(right), 2)))
    else:
        coverage = 1.0

    penalty = 0.3 * len(hit_wrong) if hit_wrong else 0.0
    value = max(0.0, coverage - penalty)

    parts = []
    if hit_right:
        parts.append(f"correct: {', '.join(sorted(hit_right))}")
    if right - hit_right:
        parts.append(f"missed: {', '.join(sorted(right - hit_right))}")
    if hit_wrong:
        parts.append(f"wrong: {', '.join(sorted(hit_wrong))}")

    return Score(round(value, 2), "; ".join(parts) or "ok")


def score_graceful_failure(response_text: str) -> Score:
    text = response_text.lower()
    failure_markers = [
        "i don't have", "i do not have", "cannot answer", "can't answer",
        "don't have access", "not available", "outside my", "beyond my",
        "unable to", "i lack", "no table", "not in my", "don't have the",
        "insufficient", "would need", "requires access to",
    ]
    if any(m in text for m in failure_markers):
        return Score(1.0, "clearly acknowledges limitation")
    if "error" in text and len(text) < 200:
        return Score(0.3, "returned an error rather than graceful explanation")
    return Score(0.0, "did not acknowledge limitation")


def score_data_in_response(response_text: str) -> Score:
    dollar_amounts = re.findall(r"\$[\d,]+(?:\.\d+)?", response_text)
    percentages = re.findall(r"\d+\.?\d*\s*%", response_text)
    has_table = "|" in response_text and "---" in response_text

    signals = 0
    if dollar_amounts:
        signals += 1
    if percentages:
        signals += 1
    if has_table:
        signals += 1
    if re.search(r"\d{3,}", response_text):
        signals += 1

    value = min(1.0, signals / 2.0)
    parts = []
    if dollar_amounts:
        parts.append(f"{len(dollar_amounts)} dollar amounts")
    if percentages:
        parts.append(f"{len(percentages)} percentages")
    if has_table:
        parts.append("contains data table")
    if not parts:
        parts.append("no quantitative data found")

    return Score(round(value, 2), "; ".join(parts))


def score_glossary_citation(response_text: str, expected_terms: list[str]) -> Score:
    if not expected_terms:
        return Score(1.0, "no glossary expectations")

    text = response_text.lower()
    cited = []
    missed = []

    for term in expected_terms:
        keywords = GLOSSARY_KEYWORDS.get(term, [term.lower()])
        if any(kw in text for kw in keywords):
            cited.append(term)
        else:
            missed.append(term)

    value = len(cited) / len(expected_terms)
    parts = []
    if cited:
        parts.append(f"cited: {', '.join(cited)}")
    if missed:
        parts.append(f"missed: {', '.join(missed)}")

    return Score(round(value, 2), "; ".join(parts))


def score_metadata_citation(response_text: str, expected_types: list[str] | None = None) -> Score:
    text = response_text.lower()
    found = []

    for meta_type, keywords in METADATA_KEYWORDS.items():
        for kw in keywords:
            if re.search(kw, text):
                found.append(meta_type)
                break

    if expected_types:
        hit = set(found) & set(expected_types)
        value = len(hit) / len(expected_types)
        reason = f"found {', '.join(sorted(hit))} of expected {', '.join(sorted(expected_types))}"
    else:
        value = min(1.0, len(found) / 2.0)
        reason = f"cited: {', '.join(sorted(found))}" if found else "no metadata cited"

    return Score(round(value, 2), reason)


def score_response_structure(response_text: str, agent_type: str) -> Score:
    if agent_type == "kc":
        sections = {
            "Data Discovery": bool(re.search(r"(?i)\*?\*?data discovery\*?\*?", response_text)),
            "Analysis": bool(re.search(r"(?i)\*?\*?analysis\*?\*?", response_text)),
            "Data Governance": bool(re.search(r"(?i)\*?\*?data governance\*?\*?", response_text)),
            "Recommendations": bool(re.search(r"(?i)\*?\*?recommend", response_text)),
        }
        found = [k for k, v in sections.items() if v]
        value = len(found) / len(sections)
        missing = [k for k, v in sections.items() if not v]
        reason = f"has: {', '.join(found)}" if found else "no sections found"
        if missing:
            reason += f"; missing: {', '.join(missing)}"
        return Score(round(value, 2), reason)
    else:
        has_data = score_data_in_response(response_text).value > 0
        has_substance = len(response_text) > 200
        value = 1.0 if (has_data and has_substance) else 0.5 if has_substance else 0.0
        return Score(value, "has data and substance" if value == 1.0 else "thin response")


def score_outcome(response_text: str, tool_calls: list[str], tables_queried: list[str],
                  expected: dict) -> Score:
    expected_outcome = expected.get("outcome", "success")

    if expected_outcome == "fail_gracefully":
        return score_graceful_failure(response_text)

    if expected_outcome == "partial":
        has_data = score_data_in_response(response_text).value > 0
        table_score = score_table_selection(tables_queried, expected)
        wrong = set(expected.get("wrong_tables", [])) & set(tables_queried)
        if wrong:
            return Score(0.3, f"used wrong tables: {', '.join(sorted(wrong))}")
        if has_data and table_score.value >= 0.5:
            return Score(0.7, "answered with data, reasonable tables")
        if has_data:
            return Score(0.5, "has data but uncertain table selection")
        return Score(0.2, "limited response")

    # success
    has_data = score_data_in_response(response_text).value > 0
    table_score = score_table_selection(tables_queried, expected)

    if has_data and table_score.value >= 0.8:
        return Score(1.0, "correct tables, data in response")
    if has_data and table_score.value >= 0.5:
        return Score(0.8, f"data present, partial table match: {table_score.reason}")
    if has_data:
        return Score(0.5, f"has data but wrong tables: {table_score.reason}")
    return Score(0.2, "expected success but no data in response")


def score_all(response_text: str, tool_calls: list[str], tables_queried: list[str],
              expected: dict, agent_type: str) -> dict[str, Score]:
    scores = {
        "outcome": score_outcome(response_text, tool_calls, tables_queried, expected),
        "table_selection": score_table_selection(tables_queried, expected),
        "data_in_response": score_data_in_response(response_text),
        "response_structure": score_response_structure(response_text, agent_type),
    }

    if expected.get("outcome") == "fail_gracefully":
        scores["graceful_failure"] = score_graceful_failure(response_text)

    if agent_type == "kc":
        glossary = expected.get("glossary", [])
        if glossary:
            scores["glossary_citation"] = score_glossary_citation(response_text, glossary)
        metadata = expected.get("metadata", [])
        if metadata or expected.get("lineage"):
            if expected.get("lineage") and "lineage" not in (metadata or []):
                metadata = list(metadata or []) + ["lineage"]
            scores["metadata_citation"] = score_metadata_citation(response_text, metadata)

    return scores
