"""Shared helpers — JSONL load, parse, and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


REQUIRED_DATASET_FIELDS = {"id", "input", "expected", "category", "scoring_method"}
REQUIRED_OUTPUT_FIELDS = {"case_id", "output"}
ALLOWED_SCORING_METHODS = {"rubric", "exact_match", "contains"}

_LINE_PREVIEW_CHARS = 80


def _preview(line: str) -> str:
    s = line if len(line) <= _LINE_PREVIEW_CHARS else line[:_LINE_PREVIEW_CHARS] + "…"
    return s.replace("\n", " ")


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON on line {i} of {path}: {e}. "
                    f"Line preview: {_preview(stripped)!r}"
                ) from e
    return rows


def parse_jsonl_text(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rows.append(json.loads(stripped))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON on line {i}: {e}. "
                f"Line preview: {_preview(stripped)!r}"
            ) from e
    return rows


def validate_dataset(rows: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Validate a dataset. Returns (ok, errors). All issues are blocking."""
    errors: List[str] = []
    if not rows:
        return False, ["Dataset is empty."]
    seen_ids: Set[str] = set()
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            errors.append(f"Row {i}: not a JSON object")
            continue
        missing = REQUIRED_DATASET_FIELDS - set(row.keys())
        if missing:
            errors.append(f"Row {i}: missing fields {sorted(missing)}")
            continue
        case_id = row["id"]
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"Row {i}: 'id' must be a non-empty string")
            continue
        if case_id in seen_ids:
            errors.append(f"Row {i}: duplicate id '{case_id}'")
        seen_ids.add(case_id)
        if row["scoring_method"] not in ALLOWED_SCORING_METHODS:
            errors.append(
                f"Row {i} ({case_id}): unknown scoring_method "
                f"'{row['scoring_method']}' (allowed: {sorted(ALLOWED_SCORING_METHODS)})"
            )
    return (len(errors) == 0), errors


def validate_outputs(
    rows: List[Dict[str, Any]],
    dataset_ids: Set[str],
) -> Tuple[List[str], List[str]]:
    """Validate output rows against dataset case ids.

    Returns (errors, warnings):
    - errors block the eval (missing required fields, duplicate ids,
      missing case_ids the dataset requires)
    - warnings are informational (extra case_ids that the dataset does not
      contain — they will be ignored)
    """
    errors: List[str] = []
    warnings: List[str] = []
    seen: Set[str] = set()
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            errors.append(f"Row {i}: not a JSON object")
            continue
        missing = REQUIRED_OUTPUT_FIELDS - set(row.keys())
        if missing:
            errors.append(f"Row {i}: missing fields {sorted(missing)}")
            continue
        case_id = row["case_id"]
        if case_id in seen:
            errors.append(f"Row {i}: duplicate case_id '{case_id}'")
        seen.add(case_id)
    missing_cases = dataset_ids - seen
    if missing_cases:
        errors.append(f"Missing outputs for case_ids: {sorted(missing_cases)}")
    extra_cases = seen - dataset_ids
    if extra_cases:
        warnings.append(
            f"Output case_ids not in dataset (will be ignored): {sorted(extra_cases)}"
        )
    return errors, warnings
