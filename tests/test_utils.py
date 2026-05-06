"""Unit tests for utils.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from utils import (
    load_jsonl,
    parse_jsonl_text,
    validate_dataset,
    validate_outputs,
)


def _good_case(case_id="case_1"):
    return {
        "id": case_id,
        "input": "in",
        "expected": "out",
        "category": "support_complaint",
        "scoring_method": "rubric",
    }


# -- parse_jsonl_text -----------------------------------------------------


def test_parse_jsonl_text_skips_blank_lines():
    text = '\n{"a":1}\n\n{"b":2}\n'
    rows = parse_jsonl_text(text)
    assert rows == [{"a": 1}, {"b": 2}]


def test_parse_jsonl_text_raises_with_line_preview():
    with pytest.raises(ValueError) as exc:
        parse_jsonl_text('{"ok": 1}\n{not json}')
    msg = str(exc.value)
    assert "line 2" in msg
    assert "not json" in msg


# -- load_jsonl -----------------------------------------------------------


def test_load_jsonl_round_trip(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text('{"a":1}\n{"b":2}\n', encoding="utf-8")
    assert load_jsonl(p) == [{"a": 1}, {"b": 2}]


def test_load_jsonl_bad_json_raises(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text('{"a":1}\n{bad}\n', encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        load_jsonl(p)
    assert "line 2" in str(exc.value)


# -- validate_dataset -----------------------------------------------------


def test_validate_dataset_happy_path():
    ok, errors = validate_dataset([_good_case("a"), _good_case("b")])
    assert ok and errors == []


def test_validate_dataset_empty():
    ok, errors = validate_dataset([])
    assert not ok
    assert errors == ["Dataset is empty."]


def test_validate_dataset_missing_field():
    bad = _good_case()
    del bad["expected"]
    ok, errors = validate_dataset([bad])
    assert not ok
    assert any("missing fields" in e for e in errors)


def test_validate_dataset_duplicate_id():
    ok, errors = validate_dataset([_good_case("dup"), _good_case("dup")])
    assert not ok
    assert any("duplicate id" in e for e in errors)


def test_validate_dataset_bad_scoring_method():
    bad = _good_case()
    bad["scoring_method"] = "vibes"
    ok, errors = validate_dataset([bad])
    assert not ok
    assert any("scoring_method" in e for e in errors)


def test_validate_dataset_non_dict_row():
    ok, errors = validate_dataset(["not a dict"])
    assert not ok
    assert any("not a JSON object" in e for e in errors)


def test_validate_dataset_empty_id():
    bad = _good_case()
    bad["id"] = ""
    ok, errors = validate_dataset([bad])
    assert not ok
    assert any("non-empty string" in e for e in errors)


# -- validate_outputs -----------------------------------------------------


def test_validate_outputs_happy_path():
    rows = [{"case_id": "a", "output": "x"}, {"case_id": "b", "output": "y"}]
    errors, warnings = validate_outputs(rows, {"a", "b"})
    assert errors == [] and warnings == []


def test_validate_outputs_missing_case_is_blocking():
    rows = [{"case_id": "a", "output": "x"}]
    errors, warnings = validate_outputs(rows, {"a", "b"})
    assert any("Missing outputs" in e for e in errors)
    assert warnings == []


def test_validate_outputs_extra_case_is_warning_not_error():
    rows = [
        {"case_id": "a", "output": "x"},
        {"case_id": "b", "output": "y"},
        {"case_id": "stranger", "output": "z"},
    ]
    errors, warnings = validate_outputs(rows, {"a", "b"})
    assert errors == []
    assert any("not in dataset" in w for w in warnings)


def test_validate_outputs_duplicate_case_id_is_blocking():
    rows = [{"case_id": "a", "output": "x"}, {"case_id": "a", "output": "y"}]
    errors, warnings = validate_outputs(rows, {"a"})
    assert any("duplicate case_id" in e for e in errors)


def test_validate_outputs_missing_required_field():
    rows = [{"case_id": "a"}]  # no "output"
    errors, warnings = validate_outputs(rows, {"a"})
    assert any("missing fields" in e for e in errors)
