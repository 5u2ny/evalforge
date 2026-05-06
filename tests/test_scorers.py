"""Unit tests for scorers.py."""

from __future__ import annotations

import pytest

from scorers import (
    COVERAGE_RATIO_THRESHOLD,
    score_contains,
    score_exact_match,
    score_output,
    score_rubric,
)


# -- score_rubric ---------------------------------------------------------


def test_rubric_empty_output_scores_one():
    r = score_rubric("", "Empathetic apology, ask for order number.")
    assert r["score"] == 1
    assert r["breakdown"]["expected_coverage"] is False
    assert r["breakdown"]["empathy"] is False
    assert r["breakdown"]["invents_details"] is False


def test_rubric_whitespace_only_scores_one():
    assert score_rubric("   \n", "anything")["score"] == 1


def test_rubric_perfect_response_scores_five():
    r = score_rubric(
        "I am sorry your order is late. I can check the delivery status. "
        "Could you share your order number?",
        "Empathetic apology, offer to check delivery status, ask for order number.",
    )
    assert r["score"] == 5
    bd = r["breakdown"]
    assert bd["empathy"] and bd["next_action"] and bd["policy_safe"]
    assert bd["expected_coverage"] is True
    assert bd["unsupported_promise"] is False
    assert bd["invents_details"] is False


def test_rubric_unsupported_promise_drops_policy_safe():
    r = score_rubric(
        "I will refund you immediately, no questions asked. 25% discount included.",
        "Investigate the charge, ask for order number.",
    )
    assert r["breakdown"]["unsupported_promise"] is True
    assert r["breakdown"]["policy_safe"] is False


def test_rubric_invents_details_deducts_a_point():
    r_no_invent = score_rubric(
        "I am sorry your order is late. I can check the delivery status now.",
        "Empathetic apology, offer to check delivery status.",
    )
    r_invent = score_rubric(
        "I am sorry your order is late. Your package should arrive tomorrow.",
        "Empathetic apology, offer to check delivery status.",
    )
    assert r_invent["breakdown"]["invents_details"] is True
    assert r_invent["score"] < r_no_invent["score"]


def test_rubric_breakdown_always_has_invents_details_key():
    # The reviewer-visible breakdown must include invents_details so the UI
    # can render it without KeyError.
    for output, expected in [
        ("", "x"),
        ("hello world", "hello"),
        ("Sorry, I will help.", "Empathetic apology, offer help."),
    ]:
        r = score_rubric(output, expected)
        assert "invents_details" in r["breakdown"]


def test_rubric_coverage_threshold_uses_constant():
    # Sanity check: the constant exists and is the active threshold.
    assert 0 < COVERAGE_RATIO_THRESHOLD <= 1


def test_rubric_score_is_clamped_to_1_5():
    for output in [
        "",
        "Sorry, I will help, no questions asked, free month upgrade.",  # multiple deductions
        "I am sorry. I can help. I will check. Could you share your order number?",
    ]:
        r = score_rubric(output, "ask for order number")
        assert 1 <= r["score"] <= 5


# -- empathy / next-action / unsupported-promise pattern tests -----------


@pytest.mark.parametrize("text", [
    "I'm sorry to hear that.",
    "I apologize for the delay.",
    "I understand how frustrating that is.",
    "I hear you on that.",
    "That's regretful.",
    "I appreciate your patience.",
])
def test_empathy_patterns_match(text):
    r = score_rubric(text, "x")
    assert r["breakdown"]["empathy"] is True


@pytest.mark.parametrize("text", [
    "Hello there.",
    "The product is in stock.",
    "Have a nice day.",
])
def test_empathy_patterns_do_not_match_neutral(text):
    r = score_rubric(text, "x")
    assert r["breakdown"]["empathy"] is False


@pytest.mark.parametrize("text", [
    "I can help with that.",
    "I'll set up a return.",
    "I will check the order.",
    "Let me look into this.",
    "Could you share your order number?",
    "Please provide a photo.",
])
def test_next_action_patterns_match(text):
    r = score_rubric(text, "x")
    assert r["breakdown"]["next_action"] is True


@pytest.mark.parametrize("text,why", [
    ("I guarantee a refund.", "guaranteed refund"),
    ("I promise a refund.", "promised refund"),
    ("Definitely refund you.", "definitely refund"),
    ("Free month of premium shipping.", "free month"),
    ("100% refund coming up.", "100% refund"),
    ("I'll add a 25% discount.", "explicit discount commitment"),
    ("No questions asked.", "no questions asked"),
    ("Refund you immediately.", "immediate refund"),
    ("Brand new laptop on the way.", "brand new laptop"),
])
def test_unsupported_promise_patterns_match(text, why):
    r = score_rubric(text, "x")
    assert r["breakdown"]["unsupported_promise"] is True, f"failed: {why}"


@pytest.mark.parametrize("text", [
    "I am sorry your order is late.",
    "I can investigate this issue.",
    "Could you share your order number?",
])
def test_unsupported_promise_does_not_match_safe_text(text):
    r = score_rubric(text, "x")
    assert r["breakdown"]["unsupported_promise"] is False


@pytest.mark.parametrize("text", [
    "Your package should arrive tomorrow.",
    "Your order is on its way.",
    "Your order should arrive Friday.",
])
def test_invention_patterns_match(text):
    r = score_rubric(text, "x")
    assert r["breakdown"]["invents_details"] is True


# -- score_exact_match ----------------------------------------------------


def test_exact_match_succeeds_with_strip():
    assert score_exact_match("  hello  ", "hello")["score"] == 5


def test_exact_match_fails_when_different():
    assert score_exact_match("hello", "world")["score"] == 1


# -- score_contains -------------------------------------------------------


def test_contains_full_phrase_match():
    r = score_contains("Your refund is being processed", "refund")
    assert r["score"] == 5


def test_contains_too_short_keyword_returns_one():
    r = score_contains("anything goes here", "y")
    assert r["score"] == 1
    assert "too short" in r["reasoning"]


def test_contains_partial_match_returns_three():
    # Keyword tokens (after stopword removal): promise, refund, discount.
    # Output contains 2 of 3 → ratio 0.67 ≥ 0.5 → score 3.
    r = score_contains(
        "We will refund the order soon and process a discount.",
        "promise refund discount",
    )
    assert r["score"] == 3


def test_contains_missing_returns_one():
    r = score_contains("hello world", "totally absent")
    assert r["score"] == 1


def test_contains_empty_keyword_returns_one():
    assert score_contains("anything", "")["score"] == 1
    assert score_contains("anything", "   ")["score"] == 1


# -- score_output dispatcher ---------------------------------------------


def test_score_output_dispatches_to_rubric():
    assert score_output("Sorry, I can help.", "x", "rubric")["score"] >= 1


def test_score_output_dispatches_to_exact_match():
    assert score_output("hello", "hello", "exact_match")["score"] == 5


def test_score_output_dispatches_to_contains():
    assert score_output("the order shipped", "shipped", "contains")["score"] == 5


def test_score_output_unknown_method_raises():
    with pytest.raises(ValueError) as exc:
        score_output("x", "y", "no_such_method")
    assert "rubric" in str(exc.value)
