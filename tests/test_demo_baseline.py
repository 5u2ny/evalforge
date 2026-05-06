"""Pin the bundled-demo headline numbers.

This is the single highest-leverage test in the project. The README's
benchmark card claims `avg A 2.21 → B 3.88, 3 regressions, SHIP WITH
CAVEAT`. If anyone tweaks a regex in scorers.py or a comparator in
eval_engine.py and the bundled-demo numbers drift, this test fails and
flags the drift before merge.

If you intentionally retune the rubric and the new numbers are correct,
update the asserts below in the same commit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eval_engine import run_eval
from utils import load_jsonl


ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "golden_dataset.jsonl"
OUTPUTS_A = ROOT / "data" / "sample_outputs_a.jsonl"
OUTPUTS_B = ROOT / "data" / "sample_outputs_b.jsonl"


@pytest.fixture(scope="module")
def baseline():
    ds = load_jsonl(DATASET)
    oa = load_jsonl(OUTPUTS_A)
    ob = load_jsonl(OUTPUTS_B)
    va = {"label": "A", "source_type": "uploaded_output",
          "model_name": "prompt_a", "prompt": "", "outputs": oa}
    vb = {"label": "B", "source_type": "uploaded_output",
          "model_name": "prompt_b", "prompt": "", "outputs": ob}
    return run_eval(ds, va, vb)


def test_dataset_size(baseline):
    assert baseline["summary"]["dataset_n"] == 24


def test_paired_size(baseline):
    assert baseline["summary"]["paired_n"] == 24


def test_avg_quality_a(baseline):
    assert baseline["summary"]["avg_quality_a"] == 2.21


def test_avg_quality_b(baseline):
    assert baseline["summary"]["avg_quality_b"] == 3.88


def test_wins_regressions_ties(baseline):
    s = baseline["summary"]
    assert s["wins_b"] == 20
    assert s["regressions_b"] == 3
    assert s["ties"] == 1
    assert s["wins_b"] + s["regressions_b"] + s["ties"] == s["paired_n"]


def test_recommendation_label(baseline):
    assert baseline["summary"]["recommendation"]["label"] == "SHIP WITH CAVEAT"


def test_top_failed_cases_are_known_three(baseline):
    ids = {f["case_id"] for f in baseline["summary"]["decision_memo"]["top_failed_cases"]}
    assert ids == {"case_004", "case_013", "case_018"}


def test_no_high_risk_regressions_in_baseline(baseline):
    # billing_issue and policy_edge each have one regressing case but the
    # category-level delta is still positive, so neither crosses the -0.5
    # high-risk threshold. This is intentional and prevents the baseline
    # from escalating to DO NOT SHIP.
    assert baseline["summary"]["high_risk_regressions"] == []


def test_case_018_b_output_trips_unsupported_promise(baseline):
    # The regression on case_018 is specifically the "guaranteed
    # replacement" slip; this asserts the rubric breakdown caught it so
    # the failed-cases explorer can surface the violation.
    rows_b_by_id = {r["case_id"]: r for r in baseline["rows_b"]}
    bd = rows_b_by_id["case_018"]["rubric_breakdown"]
    assert bd["unsupported_promise"] is True
    assert bd["policy_safe"] is False


def test_breakdown_schema_includes_invents_details(baseline):
    # Every rubric-scored row must expose the invents_details dimension so
    # the UI breakdown JSON is stable across updates.
    for row in baseline["rows_a"] + baseline["rows_b"]:
        if row["scoring_method"] == "rubric_support":
            assert "invents_details" in row["rubric_breakdown"]


def test_dataset_uses_rubric_support_scoring(baseline):
    # The bundled dataset is customer-support specific. The cases must use
    # rubric_support, not the generic rubric, so the demo numbers stay
    # consistent with the README and the failed-cases narrative.
    methods = {row["scoring_method"] for row in baseline["rows_a"]}
    assert methods == {"rubric_support"}
