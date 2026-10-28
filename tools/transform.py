#!/usr/bin/env python3
"""Mechanical domain transformation tool driven by tools/retail_mapping.json.

Usage:
  python3 tools/transform.py --dry-run
  python3 tools/transform.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAPPING_PATH = REPO_ROOT / "tools" / "retail_mapping.json"

EXCLUDE_DIRS = {
    ".git",
    "logs",
    "node_modules",
    "tools",
    ".venv",
    "__pycache__",
    ".terraform",
    ".terragrunt-cache",
}

EXCLUDE_FILES = {
    "RECON.md",
    "RETAIL_REFACTOR_PLAN.md",
    "RETAIL_MAPPING.md",
    "STATE.md",
    "AGENTS.md",
    "LICENSE",
    "uv.lock",
}

BINARY_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".pyc",
}

SQL_DIRS = [
    REPO_ROOT / "modules" / "bigquery-medallion" / "sql",
    REPO_ROOT / "modules" / "bigquery-reference" / "sql",
    REPO_ROOT / "modules" / "bigquery-dashboards" / "sql",
]


def load_mapping() -> dict:
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_replacements(mapping: dict) -> tuple[list[tuple[str, str]], list[tuple[re.Pattern, str]]]:
    """Build ordered exact-substring replacements and regex word-boundary replacements."""
    exact_map: dict[str, str] = {}

    # 1. Datasets
    for old_ds, new_ds in mapping.get("datasets", {}).items():
        if old_ds != new_ds:
            exact_map[old_ds] = new_ds

    # 2. Tables
    for old_tbl, new_tbl in mapping.get("tables", {}).items():
        if old_tbl != new_tbl:
            exact_map[old_tbl] = new_tbl
            # Also handle schema JSON filename references if any
            exact_map[f"{old_tbl}.sql"] = f"{new_tbl}.sql"
            exact_map[f"{old_tbl}.json"] = f"{new_tbl}.json"

    # 3. Aspect types
    for old_at, info in mapping.get("aspect_types", {}).items():
        new_at = info["new_id"]
        if old_at != new_at:
            exact_map[old_at] = new_at

    # 4. Rule templates
    for old_rt, info in mapping.get("rule_templates", {}).items():
        new_rt = info["new_id"]
        if old_rt != new_rt:
            exact_map[old_rt] = new_rt

    # 5. Phrase replacements
    for old_p, new_p in mapping.get("phrase_replacements", {}).items():
        if old_p != new_p:
            exact_map[old_p] = new_p

    # Sort exact replacements by length descending so longer phrases match first
    sorted_exact = sorted(exact_map.items(), key=lambda kv: len(kv[0]), reverse=True)

    # Word-boundary regex replacements (columns + token_replacements)
    word_map: dict[str, str] = {}
    for old_col, new_col in mapping.get("columns", {}).items():
        if old_col != new_col:
            word_map[old_col] = new_col

    for old_tok, new_tok in mapping.get("token_replacements", {}).items():
        if old_tok != new_tok:
            word_map[old_tok] = new_tok

    sorted_words = sorted(word_map.items(), key=lambda kv: len(kv[0]), reverse=True)
    regex_list: list[tuple[re.Pattern, str]] = []
    for old_w, new_w in sorted_words:
        pattern = re.compile(rf"\b{re.escape(old_w)}\b")
        regex_list.append((pattern, new_w))

    return sorted_exact, regex_list


def transform_sql_descriptions(content: str) -> tuple[str, int]:
    """Ensure SQL table OPTIONS(description = '...') starts with [Retail] ."""
    count = 0

    def repl(match: re.Match) -> str:
        nonlocal count
        prefix = match.group(1)
        desc = match.group(2)
        suffix = match.group(3)
        if not desc.startswith("[Retail] "):
            count += 1
            return f'{prefix}[Retail] {desc}{suffix}'
        return match.group(0)

    # Match table-level OPTIONS ( description = "..." )
    pattern = re.compile(r'(OPTIONS\s*\(\s*description\s*=\s*")([^"]+)(")', re.MULTILINE)
    new_content = pattern.sub(repl, content)
    return new_content, count


def transform_text(
    content: str,
    rel_path: str,
    sorted_exact: list[tuple[str, str]],
    regex_list: list[tuple[re.Pattern, str]],
) -> tuple[str, int]:
    """Apply all replacements to file content and return (new_content, replacement_count)."""
    total_changes = 0

    # Protect upstream repo URL in README.md if present
    protected_placeholder = "__PROTECTED_UPSTREAM_REPO_URL__"
    has_protected = False
    if rel_path == "README.md" and "haneyr/fsi_knowledge_catalog_demo" in content:
        content = content.replace("haneyr/fsi_knowledge_catalog_demo", protected_placeholder)
        has_protected = True

    for old_s, new_s in sorted_exact:
        if old_s in content:
            occurrences = content.count(old_s)
            content = content.replace(old_s, new_s)
            total_changes += occurrences

    for pattern, new_w in regex_list:
        content, n = pattern.subn(new_w, content)
        total_changes += n

    if rel_path.endswith(".sql"):
        content, n_desc = transform_sql_descriptions(content)
        total_changes += n_desc

    if has_protected:
        content = content.replace(protected_placeholder, "haneyr/fsi_knowledge_catalog_demo")

    return content, total_changes


def collect_sql_renames(mapping: dict) -> list[tuple[Path, Path]]:
    """Find SQL files that should be renamed based on tables map."""
    renames: list[tuple[Path, Path]] = []
    tables_map = mapping.get("tables", {})
    for sql_dir in SQL_DIRS:
        if not sql_dir.exists():
            continue
        for old_tbl, new_tbl in tables_map.items():
            if old_tbl == new_tbl:
                continue
            old_path = sql_dir / f"{old_tbl}.sql"
            new_path = sql_dir / f"{new_tbl}.sql"
            if old_path.exists():
                renames.append((old_path, new_path))
    return sorted(renames, key=lambda x: str(x[0]))


def iter_repo_files() -> list[Path]:
    files: list[Path] = []
    for root, dirs, filenames in os.walk(REPO_ROOT):
        dirs[:] = [d for d in sorted(dirs) if d not in EXCLUDE_DIRS]
        for fname in sorted(filenames):
            if fname in EXCLUDE_FILES:
                continue
            fpath = Path(root) / fname
            if fpath.suffix.lower() in BINARY_EXTS:
                continue
            files.append(fpath)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform FSI repo to Retail domain.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Report change counts without modifying files.")
    group.add_argument("--apply", action="store_true", help="Apply file renames and content transformations.")
    args = parser.parse_args()

    mapping = load_mapping()
    sorted_exact, regex_list = build_replacements(mapping)

    renames = collect_sql_renames(mapping)
    if args.apply:
        for old_p, new_p in renames:
            shutil.move(str(old_p), str(new_p))

    modified_files: list[tuple[str, int]] = []
    total_replacements = 0

    for fpath in iter_repo_files():
        rel_path = str(fpath.relative_to(REPO_ROOT))
        try:
            original = fpath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        updated, count = transform_text(original, rel_path, sorted_exact, regex_list)
        if count > 0 and updated != original:
            modified_files.append((rel_path, count))
            total_replacements += count
            if args.apply:
                fpath.write_text(updated, encoding="utf-8")

    mode_str = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"=== {mode_str} SUMMARY ===")
    print(f"SQL files to rename : {len(renames)}")
    print(f"Files with changes  : {len(modified_files)}")
    print(f"Total replacements  : {total_replacements}")
    print("\nTop 35 modified files by replacement count:")
    for rel_path, cnt in sorted(modified_files, key=lambda x: x[1], reverse=True)[:35]:
        print(f"  {cnt:5d}  {rel_path}")


if __name__ == "__main__":
    main()
