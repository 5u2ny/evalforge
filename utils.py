"""Shared helpers — JSONL load, parse, and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


REQUIRED_DATASET_FIELDS = {"id", "input", "expected", "category", "scoring_method"}
REQUIRED_OUTPUT_FIELDS = {"case_id", "output"}
ALLOWED_SCORING_METHODS = {"rubric", "exact_match", "contains"}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {i} of {path}: {e}") from e
    return rows


def parse_jsonl_text(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON on line {i}: {e}") from e
    return rows


def validate_dataset(rows: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not rows:
        return False, ["Dataset is empty."]
    seen_ids: Set[str] = set()
    for i, row in enumerate(rows, 1):
        missing = REQUIRED_DATASET_FIELDS - set(row.keys())
        if missing:
            errors.append(f"Row {i}: missing fields {sorted(missing)}")
            continue
        if row["id"] in seen_ids:
            errors.append(f"Row {i}: duplicate id '{row['id']}'")
        seen_ids.add(row["id"])
        if row["scoring_method"] not in ALLOWED_SCORING_METHODS:
            errors.append(
                f"Row {i} ({row['id']}): unknown scoring_method "
                f"'{row['scoring_method']}' (allowed: {sorted(ALLOWED_SCORING_METHODS)})"
            )
    return (len(errors) == 0), errors


def validate_outputs(
    rows: List[Dict[str, Any]],
    dataset_ids: Set[str],
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    seen: Set[str] = set()
    for i, row in enumerate(rows, 1):
        missing = REQUIRED_OUTPUT_FIELDS - set(row.keys())
        if missing:
            errors.append(f"Row {i}: missing fields {sorted(missing)}")
            continue
        if row["case_id"] in seen:
            errors.append(f"Row {i}: duplicate case_id '{row['case_id']}'")
        seen.add(row["case_id"])
    missing_cases = dataset_ids - seen
    if missing_cases:
        errors.append(f"Missing outputs for case_ids: {sorted(missing_cases)}")
    extra_cases = seen - dataset_ids
    if extra_cases:
        errors.append(
            f"Outputs include case_ids not in dataset (will be ignored): "
            f"{sorted(extra_cases)}"
        )
    blocking = [e for e in errors if "ignored" not in e]
    return (len(blocking) == 0), errors
