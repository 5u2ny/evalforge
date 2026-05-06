"""Local deterministic and rubric-based scorers.

No LLM calls. No paid APIs. All logic is pure Python heuristics so the rubric
is inspectable, reproducible, and free to run.

Assumption: ``output`` is the agent's reply text only. If you score a turn that
includes the customer's quoted message, the regex patterns may match the
customer's words and produce misleading results. Strip quoted user content
before scoring.
"""

from __future__ import annotations

import re
import string
from typing import Any, Dict, List, Pattern


COVERAGE_RATIO_THRESHOLD = 0.30


_STOPWORDS = {
    "a", "an", "and", "or", "but", "the", "of", "to", "in", "on", "for",
    "with", "without", "from", "by", "is", "are", "was", "were", "be",
    "been", "being", "as", "at", "if", "than", "then", "this", "that",
    "these", "those", "it", "its", "their", "they", "them", "you", "your",
    "we", "our", "us", "i", "me", "my", "do", "does", "did", "have", "has",
    "had", "will", "would", "should", "could", "may", "might", "can", "no",
    "not", "any", "some", "all", "into", "about", "after", "before", "when",
    "where", "what", "why", "how", "who", "which", "also", "such", "very",
    "just", "so", "too", "more", "most", "less", "few", "many", "much",
    "customer", "order", "please",
}

_EMPATHY_PATTERNS = [
    r"\bsorry\b",
    r"\bapolog(?:y|ize|ies|ise)\b",
    r"\bunderstand\b",
    r"\bhear\s+(?:you|how)\b",
    r"\bfrustrat",
    r"\bregret",
    r"\bappreciate\b",
    r"\bthat'?s\s+(?:tough|frustrating|stressful)\b",
]

_NEXT_ACTION_PATTERNS = [
    r"\bi\s+can\b",
    r"\bi'?ll\b",
    r"\bi\s+will\b",
    r"\blet\s+me\b",
    r"\bcould\s+you\s+(?:share|provide|send|confirm|tell)\b",
    r"\bplease\s+(?:share|provide|send|confirm|tell)\b",
    r"\bcan\s+i\s+(?:get|have|ask)\b",
    r"\bmay\s+i\s+(?:have|ask)\b",
    r"\bnext\s+step\b",
    r"\bset\s+up\b",
    r"\bi\s+can\s+(?:check|look|investigate|escalate|process|reach\s+out)\b",
]

_UNSUPPORTED_PROMISE_PATTERNS = [
    r"\bguarantee[ds]?\s+(?:a\s+)?(?:refund|discount|credit|replacement)\b",
    r"\bpromise\s+(?:a\s+)?(?:refund|discount|credit|free|replacement)\b",
    r"\bdefinitely\s+(?:refund|approve|process|give)\b",
    r"\b(?:free|complimentary)\s+(?:month|upgrade|credit|gift|product|item|shipping|delivery|laptop|tv)\b",
    r"\b100%\s+refund\b",
    r"\bi'?ll\s+(?:add|give|throw\s+in|include|process|issue|send)\s+(?:you\s+)?(?:a\s+)?(?:\$?\d+%?\s*)?(?:discount|credit|coupon|gift\s+card)\b",
    r"\bno\s+questions\s+asked\b",
    r"\b(?:10|15|20|25|30|40|50|75)%\s+(?:discount|off)\b",
    r"\brefund\s+you\s+(?:both\s+)?(?:right\s+away|immediately|now|today)\b",
    r"\brefund\s+(?:right\s+away|immediately)\b",
    r"\bbrand\s+new\s+(?:laptop|tv|phone)\b",
    r"\bfree\s+\$\d+\s+credit\b",
]

_INVENTION_PATTERNS = [
    r"\bshould\s+arrive\s+(?:tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\barrive\s+by\s+(?:tomorrow|today)\b",
    r"\bis\s+on\s+its\s+way\b",
]


def _compile(patterns: List[str]) -> List[Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_EMPATHY_RX = _compile(_EMPATHY_PATTERNS)
_NEXT_ACTION_RX = _compile(_NEXT_ACTION_PATTERNS)
_UNSUPPORTED_PROMISE_RX = _compile(_UNSUPPORTED_PROMISE_PATTERNS)
_INVENTION_RX = _compile(_INVENTION_PATTERNS)


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return [w for w in text.split() if w]


def _significant_words(text: str) -> set[str]:
    return {w for w in _tokenize(text) if len(w) >= 5 and w not in _STOPWORDS}


def _has_match(text: str, compiled: List[Pattern[str]]) -> bool:
    return any(rx.search(text) for rx in compiled)


def _empty_breakdown(policy_safe: bool = True) -> Dict[str, bool]:
    return {
        "expected_coverage": False,
        "empathy": False,
        "next_action": False,
        "policy_safe": policy_safe,
        "unsupported_promise": False,
        "invents_details": False,
    }


def score_rubric(output: str, expected: str) -> Dict[str, Any]:
    """Score an output 1-5 using deterministic heuristics.

    Rubric dimensions returned in ``breakdown``:
    - expected_coverage: enough significant words from `expected` appear in output
    - empathy: at least one empathy marker present
    - next_action: at least one clear-next-action marker present
    - policy_safe: no unsupported promise pattern detected
    - unsupported_promise: True when an unsupported promise pattern is found
    - invents_details: True when the output fabricates information the user did
      not provide (e.g., a delivery date). Triggers a 1-point deduction.
    """
    if not output or not output.strip():
        return {
            "score": 1,
            "reasoning": "Score 1/5. Output is empty.",
            "breakdown": _empty_breakdown(),
        }

    expected_words = _significant_words(expected)
    output_words = set(_tokenize(output))
    if expected_words:
        overlap = len(expected_words & output_words)
        coverage_ratio = overlap / len(expected_words)
        expected_coverage = coverage_ratio >= COVERAGE_RATIO_THRESHOLD
    else:
        expected_coverage = False

    empathy = _has_match(output, _EMPATHY_RX)
    next_action = _has_match(output, _NEXT_ACTION_RX)
    unsupported_promise = _has_match(output, _UNSUPPORTED_PROMISE_RX)
    invents_details = _has_match(output, _INVENTION_RX)
    policy_safe = not unsupported_promise

    score = 1
    awarded: List[str] = []
    missing: List[str] = []

    if expected_coverage:
        score += 1
        awarded.append("addresses expected behaviors")
    else:
        missing.append("does not cover expected behaviors")

    if empathy:
        score += 1
        awarded.append("empathetic acknowledgement")
    else:
        missing.append("no empathy markers")

    if next_action:
        score += 1
        awarded.append("clear next action")
    else:
        missing.append("no clear next action")

    if policy_safe:
        score += 1
        awarded.append("policy-safe phrasing")
    else:
        missing.append("contains an unsupported promise")

    if invents_details:
        score = max(1, score - 1)
        missing.append("invents details not provided by the customer")

    score = max(1, min(5, score))

    parts = []
    if awarded:
        parts.append("strengths: " + ", ".join(awarded))
    if missing:
        parts.append("gaps: " + ", ".join(missing))
    reasoning = f"Score {score}/5. " + "; ".join(parts) + "."

    return {
        "score": score,
        "reasoning": reasoning,
        "breakdown": {
            "expected_coverage": expected_coverage,
            "empathy": empathy,
            "next_action": next_action,
            "policy_safe": policy_safe,
            "unsupported_promise": unsupported_promise,
            "invents_details": invents_details,
        },
    }


def score_exact_match(output: str, expected: str) -> Dict[str, Any]:
    match = output.strip() == expected.strip()
    score = 5 if match else 1
    breakdown = _empty_breakdown()
    breakdown["expected_coverage"] = match
    return {
        "score": score,
        "reasoning": f"Exact match {'succeeded' if match else 'failed'}.",
        "breakdown": breakdown,
    }


def score_contains(output: str, expected: str) -> Dict[str, Any]:
    out_lower = output.lower()
    exp_lower = expected.lower().strip()
    if len(exp_lower) < 2:
        return {
            "score": 1,
            "reasoning": "Expected keyword is empty or too short (need >= 2 chars).",
            "breakdown": _empty_breakdown(),
        }
    if exp_lower in out_lower:
        breakdown = _empty_breakdown()
        breakdown["expected_coverage"] = True
        return {
            "score": 5,
            "reasoning": "Full keyword phrase found in output.",
            "breakdown": breakdown,
        }
    kw_tokens = [t for t in _tokenize(exp_lower) if t not in _STOPWORDS]
    if kw_tokens:
        hits = sum(1 for t in kw_tokens if t in out_lower)
        ratio = hits / len(kw_tokens)
    else:
        hits, ratio = 0, 0.0
    if ratio >= 0.5:
        return {
            "score": 3,
            "reasoning": f"Partial keyword match ({hits}/{len(kw_tokens)} tokens).",
            "breakdown": _empty_breakdown(),
        }
    return {
        "score": 1,
        "reasoning": "Keyword missing from output.",
        "breakdown": _empty_breakdown(),
    }


SCORERS = {
    "rubric": score_rubric,
    "exact_match": score_exact_match,
    "contains": score_contains,
}


def score_output(output: str, expected: str, method: str) -> Dict[str, Any]:
    fn = SCORERS.get(method)
    if fn is None:
        raise ValueError(
            f"Unknown scoring method: {method!r}. "
            f"Allowed: {sorted(SCORERS.keys())}"
        )
    return fn(output, expected)
