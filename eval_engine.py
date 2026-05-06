"""Eval engine — single shared abstraction for all comparison modes.

A Variant is the spine of the project. Prompt-vs-Prompt, Model-vs-Model, and
Custom Variant Comparison all build two Variants and call run_eval(). There
is no parallel implementation per mode.

Variant = {
    "label": "A" or "B",
    "source_type": "manual_output" | "uploaded_output" | "local_stub",
    "model_name": str,
    "prompt": str,
    "outputs": list[{"case_id": str, "output": str, "latency_ms": float | None}],
}
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scorers import score_output


# Categories where a regression should weigh heavily on the recommendation.
HIGH_RISK_CATEGORIES = {
    "refund_request",
    "billing_issue",
    "policy_edge",
    "escalation",
}

HIGH_RISK_DELTA_THRESHOLD = -0.5


def _index_outputs(outputs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {row["case_id"]: row for row in outputs if "case_id" in row}


def _evaluate_variant(
    dataset: List[Dict[str, Any]],
    variant: Dict[str, Any],
) -> List[Dict[str, Any]]:
    output_index = _index_outputs(variant.get("outputs", []))
    rows: List[Dict[str, Any]] = []
    for case in dataset:
        case_id = case["id"]
        out_row = output_index.get(case_id)
        output_text = out_row["output"] if out_row else ""
        latency = out_row.get("latency_ms") if out_row else None
        method = case.get("scoring_method", "rubric")
        if out_row is None:
            score_data = {
                "score": 1,
                "reasoning": "No output found for this case.",
                "breakdown": {
                    "expected_coverage": False,
                    "empathy": False,
                    "next_action": False,
                    "policy_safe": True,
                    "unsupported_promise": False,
                },
            }
        else:
            score_data = score_output(output_text, case["expected"], method)
        rows.append({
            "case_id": case_id,
            "category": case.get("category", "uncategorized"),
            "input": case["input"],
            "expected": case["expected"],
            "variant_label": variant["label"],
            "variant_name": variant.get("model_name") or variant["label"],
            "source_type": variant.get("source_type", "uploaded_output"),
            "prompt": variant.get("prompt", ""),
            "output": output_text,
            "quality_score": score_data["score"],
            "rubric_breakdown": score_data["breakdown"],
            "judge_reasoning": score_data["reasoning"],
            "latency_ms": latency,
            "scoring_method": method,
            "has_output": out_row is not None,
        })
    return rows


def run_eval(
    dataset: List[Dict[str, Any]],
    variant_a: Dict[str, Any],
    variant_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Run evaluation across both variants on the same dataset."""
    started = time.time()
    rows_a = _evaluate_variant(dataset, variant_a)
    rows_b = _evaluate_variant(dataset, variant_b)

    by_case: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for r in rows_a:
        by_case.setdefault(r["case_id"], {})["A"] = r
    for r in rows_b:
        by_case.setdefault(r["case_id"], {})["B"] = r

    paired: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
    for case_id, sides in by_case.items():
        if "A" in sides and "B" in sides:
            paired.append((case_id, sides["A"], sides["B"]))

    wins_b = sum(1 for _, a, b in paired if b["quality_score"] > a["quality_score"])
    regressions_b = sum(1 for _, a, b in paired if b["quality_score"] < a["quality_score"])
    ties = sum(1 for _, a, b in paired if b["quality_score"] == a["quality_score"])

    avg_a = sum(r["quality_score"] for r in rows_a) / len(rows_a) if rows_a else 0.0
    avg_b = sum(r["quality_score"] for r in rows_b) / len(rows_b) if rows_b else 0.0

    cat_scores: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: {"A": [], "B": []})
    for r in rows_a:
        cat_scores[r["category"]]["A"].append(r["quality_score"])
    for r in rows_b:
        cat_scores[r["category"]]["B"].append(r["quality_score"])

    category_breakdown: List[Dict[str, Any]] = []
    high_risk_regressions: List[Tuple[str, float]] = []
    for cat, sides in sorted(cat_scores.items()):
        a_scores = sides["A"]
        b_scores = sides["B"]
        a_avg = sum(a_scores) / len(a_scores) if a_scores else 0.0
        b_avg = sum(b_scores) / len(b_scores) if b_scores else 0.0
        delta = b_avg - a_avg
        category_breakdown.append({
            "category": cat,
            "avg_a": round(a_avg, 2),
            "avg_b": round(b_avg, 2),
            "delta": round(delta, 2),
            "n": len(a_scores),
            "high_risk": cat in HIGH_RISK_CATEGORIES,
        })
        if cat in HIGH_RISK_CATEGORIES and delta < HIGH_RISK_DELTA_THRESHOLD:
            high_risk_regressions.append((cat, round(delta, 2)))

    a_lat = [r["latency_ms"] for r in rows_a if r["latency_ms"] is not None]
    b_lat = [r["latency_ms"] for r in rows_b if r["latency_ms"] is not None]
    avg_lat_a = round(sum(a_lat) / len(a_lat), 1) if a_lat else None
    avg_lat_b = round(sum(b_lat) / len(b_lat), 1) if b_lat else None

    summary: Dict[str, Any] = {
        "n_cases": len(paired),
        "avg_quality_a": round(avg_a, 2),
        "avg_quality_b": round(avg_b, 2),
        "wins_b": wins_b,
        "regressions_b": regressions_b,
        "ties": ties,
        "avg_latency_ms_a": avg_lat_a,
        "avg_latency_ms_b": avg_lat_b,
        "category_breakdown": category_breakdown,
        "high_risk_regressions": high_risk_regressions,
        "variant_a_name": variant_a.get("model_name") or "Variant A",
        "variant_b_name": variant_b.get("model_name") or "Variant B",
        "duration_seconds": round(time.time() - started, 2),
    }
    summary["recommendation"] = generate_recommendation(summary)
    summary["decision_memo"] = build_decision_memo(summary, paired)

    return {
        "rows_a": rows_a,
        "rows_b": rows_b,
        "paired": paired,
        "summary": summary,
    }


def generate_recommendation(summary: Dict[str, Any]) -> Dict[str, str]:
    avg_a = summary["avg_quality_a"]
    avg_b = summary["avg_quality_b"]
    regressions = summary["regressions_b"]
    high_risk_regressions = summary["high_risk_regressions"]

    if avg_b < avg_a or regressions > 3 or high_risk_regressions:
        explanation = (
            f"Variant B average quality is {avg_b} vs Variant A {avg_a}, "
            f"with {regressions} regressions. "
        )
        if high_risk_regressions:
            explanation += "High-risk category regressions: " + ", ".join(
                f"{c} ({d:+})" for c, d in high_risk_regressions
            ) + ". "
        explanation += "Investigate before shipping."
        return {"label": "DO NOT SHIP", "explanation": explanation}

    if regressions == 0:
        return {
            "label": "SHIP",
            "explanation": (
                f"Variant B average quality is {avg_b} vs Variant A {avg_a} with no "
                "regressions. Shipping looks safe based on this dataset."
            ),
        }

    return {
        "label": "SHIP WITH CAVEAT",
        "explanation": (
            f"Variant B average quality is {avg_b} vs Variant A {avg_a} with "
            f"{regressions} regression(s). Quality holds or improves overall, but "
            "review the failed cases before shipping."
        ),
    }


def build_decision_memo(
    summary: Dict[str, Any],
    paired: List[Tuple[str, Dict[str, Any], Dict[str, Any]]],
) -> Dict[str, Any]:
    failed: List[Dict[str, Any]] = []
    for case_id, a, b in paired:
        if b["quality_score"] < a["quality_score"]:
            failed.append({
                "case_id": case_id,
                "category": a["category"],
                "delta": b["quality_score"] - a["quality_score"],
                "input": a["input"],
                "b_reasoning": b["judge_reasoning"],
            })
    failed.sort(key=lambda x: x["delta"])
    top_failed = failed[:3]

    risks: List[str] = []
    if summary["high_risk_regressions"]:
        for cat, delta in summary["high_risk_regressions"]:
            risks.append(
                f"High-risk category regression in {cat} (avg score delta {delta:+})."
            )
    if summary["regressions_b"] > 3:
        risks.append(f"{summary['regressions_b']} cases regressed in Variant B.")
    if summary["avg_quality_b"] < summary["avg_quality_a"]:
        risks.append(
            f"Variant B average ({summary['avg_quality_b']}) is below "
            f"Variant A ({summary['avg_quality_a']})."
        )
    if not risks:
        risks.append(
            "Heuristic scorer may miss semantic nuance; spot-check failed cases manually."
        )
        risks.append(
            "Small dataset can produce false confidence; expand the golden set over time."
        )
        risks.append(
            "Average score can hide category-level regressions; review the breakdown table."
        )

    label = summary["recommendation"]["label"]
    if label == "SHIP":
        next_action = (
            "Run the same eval after the next prompt change to confirm the trend holds."
        )
    elif label == "SHIP WITH CAVEAT":
        next_action = (
            "Manually review the top failed cases. If acceptable, ship behind a feature flag."
        )
    else:
        next_action = "Do not ship. Iterate on the variant and re-run before any rollout."

    return {
        "top_failed_cases": top_failed,
        "top_risks": risks[:3],
        "next_action": next_action,
    }


def save_run(result: Dict[str, Any], runs_dir: Path) -> Path:
    """Write a JSONL run file to runs_dir and return the path."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_id = f"run_{stamp}"
    out_path = runs_dir / f"{run_id}.jsonl"
    summary = {k: v for k, v in result["summary"].items()}
    with out_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "summary", "run_id": run_id, **summary}) + "\n")
        for row in result["rows_a"] + result["rows_b"]:
            f.write(json.dumps({"type": "row", "run_id": run_id, **row}) + "\n")
    return out_path
