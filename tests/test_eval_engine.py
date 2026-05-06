"""Unit tests for eval_engine.py — recommendation logic, run_eval, save_run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_engine import (
    DEFAULT_HIGH_RISK_CATEGORIES,
    RECOMMENDATION_EPSILON,
    build_decision_memo,
    generate_recommendation,
    run_eval,
    save_run,
)


def _summary(avg_a, avg_b, regs=0, hi=None):
    return {
        "avg_quality_a": round(avg_a, 2),
        "avg_quality_b": round(avg_b, 2),
        "avg_quality_a_raw": avg_a,
        "avg_quality_b_raw": avg_b,
        "regressions_b": regs,
        "high_risk_regressions": hi or [],
    }


# -- generate_recommendation truth table ----------------------------------


@pytest.mark.parametrize("a,b,r,hi,expected", [
    (3.0, 3.5, 0, [], "SHIP"),
    (3.0, 3.5, 2, [], "SHIP WITH CAVEAT"),
    (3.0, 3.5, 4, [], "DO NOT SHIP"),
    (3.5, 3.0, 0, [], "DO NOT SHIP"),
    (3.0, 3.5, 0, [("billing_issue", -0.7)], "DO NOT SHIP"),
    (3.0, 3.0, 0, [], "SHIP"),
    (3.5, 3.5, 1, [], "SHIP WITH CAVEAT"),
])
def test_recommendation_branches(a, b, r, hi, expected):
    assert generate_recommendation(_summary(a, b, r, hi))["label"] == expected


def test_recommendation_does_not_flip_on_rounding_noise():
    # 3.881 rounds to 3.88, 3.879 rounds to 3.88 — both within epsilon, so
    # tiny differences must not flip SHIP -> DO NOT SHIP.
    s = _summary(3.881, 3.879, regs=0)
    assert generate_recommendation(s)["label"] == "SHIP"


def test_recommendation_does_flip_when_b_clearly_worse():
    s = _summary(3.5, 3.5 - RECOMMENDATION_EPSILON - 0.05, regs=0)
    assert generate_recommendation(s)["label"] == "DO NOT SHIP"


def test_recommendation_explanation_mentions_high_risk_categories():
    s = _summary(3.0, 3.5, hi=[("refund_request", -0.8)])
    rec = generate_recommendation(s)
    assert rec["label"] == "DO NOT SHIP"
    assert "refund_request" in rec["explanation"]


# -- build_decision_memo --------------------------------------------------


def _row(score, category="support_complaint", case_id="c", judge="r"):
    return {
        "case_id": case_id,
        "category": category,
        "input": "in",
        "expected": "exp",
        "quality_score": score,
        "judge_reasoning": judge,
        "rubric_breakdown": {},
        "output": "o",
        "variant_label": "X",
        "variant_name": "n",
    }


def test_decision_memo_top_failed_cases_sorted_by_delta():
    paired = [
        ("c1", _row(5, case_id="c1"), _row(3, case_id="c1")),  # delta -2
        ("c2", _row(3, case_id="c2"), _row(2, case_id="c2")),  # delta -1
        ("c3", _row(4, case_id="c3"), _row(1, case_id="c3")),  # delta -3
        ("c4", _row(3, case_id="c4"), _row(3, case_id="c4")),  # tie
    ]
    s = _summary(3.5, 2.5, regs=3)
    s["recommendation"] = generate_recommendation(s)
    memo = build_decision_memo(s, paired)
    ids = [c["case_id"] for c in memo["top_failed_cases"]]
    assert ids == ["c3", "c1", "c2"]  # most-negative delta first


def test_decision_memo_default_risks_when_no_regressions():
    paired = []
    s = _summary(3.0, 3.5, regs=0)
    s["recommendation"] = generate_recommendation(s)
    memo = build_decision_memo(s, paired)
    assert len(memo["top_risks"]) == 3
    assert memo["next_action"].startswith("Run the same eval")


# -- run_eval (small synthetic) ------------------------------------------


def _ds(*ids):
    return [{
        "id": i,
        "input": f"input {i}",
        "expected": "Empathetic apology, ask for order number.",
        "category": "support_complaint",
        "scoring_method": "rubric",
    } for i in ids]


def _va(outputs, label="A", name="a"):
    return {
        "label": label,
        "source_type": "uploaded_output",
        "model_name": name,
        "prompt": "",
        "outputs": outputs,
    }


def test_run_eval_tracks_missing_outputs():
    # The engine still scores every dataset case (missing outputs become
    # score-1 rows with missing_output=True), but missing_outputs_a/b in the
    # summary should accurately count the gaps.
    ds = _ds("c1", "c2", "c3")
    a = [{"case_id": "c1", "output": "I'm sorry. I will help. Could you share your order number?"}]
    b = [{"case_id": "c1", "output": "Sorry. I can help. Please share your order number."},
         {"case_id": "c2", "output": "Sorry. I can help. Please share your order number."}]
    r = run_eval(ds, _va(a), _va(b, label="B", name="b"))
    s = r["summary"]
    assert s["dataset_n"] == 3
    assert s["paired_n"] == 3  # every dataset case yields A and B rows
    assert s["missing_outputs_a"] == 2  # c2, c3 missing on A
    assert s["missing_outputs_b"] == 1  # c3 missing on B
    # Missing-output rows are flagged so the UI can display the gap.
    rows_a_by_id = {r["case_id"]: r for r in r["rows_a"]}
    assert rows_a_by_id["c2"]["missing_output"] is True
    assert rows_a_by_id["c1"]["missing_output"] is False


def test_run_eval_dataset_missing_id_raises():
    bad_ds = [{"input": "x", "expected": "y", "category": "z", "scoring_method": "rubric"}]
    with pytest.raises(ValueError):
        run_eval(bad_ds, _va([]), _va([], "B", "b"))


def test_run_eval_dataset_missing_expected_raises():
    bad_ds = [{"id": "x", "input": "x", "category": "z", "scoring_method": "rubric"}]
    with pytest.raises(ValueError):
        run_eval(bad_ds, _va([]), _va([], "B", "b"))


def test_run_eval_high_risk_categories_override():
    # Make support_complaint (A=5, B=1) trigger high-risk regression by overriding the set.
    ds = _ds("c1")
    a = [{"case_id": "c1", "output": "I am sorry. I will help. Could you share your order number?"}]  # 5
    b = [{"case_id": "c1", "output": ""}]  # 1
    r = run_eval(ds, _va(a), _va(b, "B", "b"), high_risk_categories={"support_complaint"})
    # delta = 1 - 5 = -4, which is < -0.5
    assert r["summary"]["high_risk_regressions"] == [("support_complaint", -4.0)]
    assert r["summary"]["recommendation"]["label"] == "DO NOT SHIP"


def test_run_eval_default_high_risk_set_unchanged():
    assert "refund_request" in DEFAULT_HIGH_RISK_CATEGORIES
    assert "support_complaint" not in DEFAULT_HIGH_RISK_CATEGORIES


def test_run_eval_latency_unavailable_when_absent():
    ds = _ds("c1")
    a = [{"case_id": "c1", "output": "Sorry. I can help."}]
    b = [{"case_id": "c1", "output": "Sorry. I can help."}]
    r = run_eval(ds, _va(a), _va(b, "B", "b"))
    assert r["summary"]["avg_latency_ms_a"] is None
    assert r["summary"]["avg_latency_ms_b"] is None


def test_run_eval_latency_averaged_when_present():
    ds = _ds("c1", "c2")
    a = [
        {"case_id": "c1", "output": "Sorry. I can help.", "latency_ms": 100},
        {"case_id": "c2", "output": "Sorry. I can help.", "latency_ms": 200},
    ]
    b = [
        {"case_id": "c1", "output": "Sorry. I can help."},
        {"case_id": "c2", "output": "Sorry. I can help."},
    ]
    r = run_eval(ds, _va(a), _va(b, "B", "b"))
    assert r["summary"]["avg_latency_ms_a"] == 150.0
    assert r["summary"]["avg_latency_ms_b"] is None


# -- save_run -------------------------------------------------------------


def _minimal_result():
    return {
        "rows_a": [],
        "rows_b": [],
        "summary": {
            "n_cases": 0, "dataset_n": 0, "paired_n": 0,
            "missing_outputs_a": 0, "missing_outputs_b": 0,
            "avg_quality_a": 0, "avg_quality_b": 0,
            "avg_quality_a_raw": 0.0, "avg_quality_b_raw": 0.0,
            "wins_b": 0, "regressions_b": 0, "ties": 0,
            "avg_latency_ms_a": None, "avg_latency_ms_b": None,
            "category_breakdown": [], "high_risk_regressions": [],
            "high_risk_categories": [],
            "variant_a_name": "a", "variant_b_name": "b",
            "duration_seconds": 0.0,
            "recommendation": {"label": "SHIP", "explanation": ""},
            "decision_memo": {"top_failed_cases": [], "top_risks": [], "next_action": ""},
        },
    }


def test_save_run_unique_filenames(tmp_path):
    r = _minimal_result()
    p1 = save_run(r, tmp_path)
    p2 = save_run(r, tmp_path)
    assert p1 != p2  # uuid suffix prevents same-second collision
    assert p1.exists() and p2.exists()


def test_save_run_writes_summary_first_line(tmp_path):
    r = _minimal_result()
    p = save_run(r, tmp_path)
    first = p.read_text().splitlines()[0]
    obj = json.loads(first)
    assert obj["type"] == "summary"
    assert obj["recommendation"]["label"] == "SHIP"
