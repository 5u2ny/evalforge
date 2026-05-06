"""EvalForge — Streamlit UI.

Run: streamlit run app.py
No paid APIs, no API keys, no .env. All scoring is local.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from eval_engine import run_eval, save_run
from utils import load_jsonl, parse_jsonl_text, validate_dataset, validate_outputs


ROOT = Path(__file__).parent
DEFAULT_DATASET = ROOT / "data" / "golden_dataset.jsonl"
DEFAULT_OUTPUTS_A = ROOT / "data" / "sample_outputs_a.jsonl"
DEFAULT_OUTPUTS_B = ROOT / "data" / "sample_outputs_b.jsonl"
DEFAULT_PROMPT_A = ROOT / "prompts" / "support_prompt_a.txt"
DEFAULT_PROMPT_B = ROOT / "prompts" / "support_prompt_b.txt"
RUNS_DIR = ROOT / "data" / "runs"
LOG_PATH = RUNS_DIR / "eval.log"


def _configure_logging() -> None:
    if logging.getLogger("evalforge").handlers:
        return
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


_configure_logging()
log = logging.getLogger("evalforge.app")


@st.cache_data(show_spinner=False)
def _read_text_cached(path_str: str, mtime: float) -> str:
    p = Path(path_str)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return _read_text_cached(str(path), path.stat().st_mtime)


def _load_default_outputs(path: Path) -> Optional[List[Dict[str, Any]]]:
    if not path.exists():
        return None
    return load_jsonl(path)


def section_header() -> None:
    st.title("EvalForge")
    st.caption("Stop shipping prompt changes on vibes.")
    st.write(
        "Compare prompt and model variants across quality, latency, regressions, "
        "and release risk without paid APIs."
    )


def dataset_loader_ui() -> Optional[List[Dict[str, Any]]]:
    st.subheader("1. Dataset")
    use_default = st.checkbox(
        "Use bundled golden dataset",
        value=True,
        key="ds_default",
        help="24 customer-support cases across 9 categories, shipped with the repo.",
    )
    rows: List[Dict[str, Any]] = []
    if use_default:
        if not DEFAULT_DATASET.exists():
            st.error(f"Default dataset not found at {DEFAULT_DATASET}.")
            return None
        rows = load_jsonl(DEFAULT_DATASET)
        st.caption(f"Loaded {len(rows)} cases from `{DEFAULT_DATASET.relative_to(ROOT)}`.")
    else:
        upload = st.file_uploader(
            "Upload golden dataset (JSONL)", type=["jsonl"], key="ds_upload"
        )
        if upload is None:
            st.info("Upload a JSONL dataset or check the box above to use the bundled one.")
            return None
        try:
            rows = parse_jsonl_text(upload.getvalue().decode("utf-8"))
        except ValueError as e:
            st.error(str(e))
            return None
    ok, errors = validate_dataset(rows)
    if not ok:
        st.error("Dataset validation failed:")
        for err in errors:
            st.write(f"- {err}")
        return None
    return rows


def outputs_loader_ui(
    label: str,
    default_path: Path,
    key_prefix: str,
    dataset: List[Dict[str, Any]],
) -> Optional[List[Dict[str, Any]]]:
    use_default = st.checkbox(
        f"Use bundled sample outputs ({default_path.name})",
        value=True,
        key=f"{key_prefix}_default",
        help="Bundled sample outputs are not generated live. They ship with the repo for demonstration.",
    )
    if use_default:
        rows = _load_default_outputs(default_path)
        if rows is None:
            st.error(f"Default outputs missing at {default_path}.")
            return None
        st.caption(
            f"Sample outputs loaded ({len(rows)} rows). Labelled as bundled "
            "sample data, not live generation."
        )
        return rows

    mode = st.radio(
        f"Provide {label} outputs via",
        options=["Upload JSONL", "Paste JSONL", "Manual entry"],
        horizontal=True,
        key=f"{key_prefix}_mode",
    )
    if mode == "Upload JSONL":
        upload = st.file_uploader(
            f"Upload {label} outputs (JSONL)",
            type=["jsonl"],
            key=f"{key_prefix}_upload",
        )
        if upload is None:
            return None
        try:
            return parse_jsonl_text(upload.getvalue().decode("utf-8"))
        except ValueError as e:
            st.error(str(e))
            return None

    if mode == "Paste JSONL":
        text = st.text_area(
            f"Paste {label} JSONL (one object per line)",
            height=160,
            key=f"{key_prefix}_paste",
        )
        if not text.strip():
            return None
        try:
            return parse_jsonl_text(text)
        except ValueError as e:
            st.error(str(e))
            return None

    # Manual entry
    st.caption("Manual entry — type an output for each case in the dataset.")
    rows: List[Dict[str, Any]] = []
    for case in dataset:
        out = st.text_area(
            f"{case['id']} — {case.get('category', '')}",
            key=f"{key_prefix}_manual_{case['id']}",
            height=80,
            help=case["input"],
        )
        if out.strip():
            rows.append({"case_id": case["id"], "output": out})
    return rows if rows else None


def render_leaderboard(summary: Dict[str, Any]) -> None:
    st.subheader("Leaderboard")
    a_name = summary["variant_a_name"]
    b_name = summary["variant_b_name"]

    def winner_label(a: float, b: float, higher_better: bool = True) -> str:
        if a == b:
            return "tie"
        if higher_better:
            return b_name if b > a else a_name
        return b_name if b < a else a_name

    lat_a = summary["avg_latency_ms_a"]
    lat_b = summary["avg_latency_ms_b"]
    lat_a_str = f"{lat_a} ms" if lat_a is not None else "unavailable"
    lat_b_str = f"{lat_b} ms" if lat_b is not None else "unavailable"
    if lat_a is not None and lat_b is not None:
        lat_winner = winner_label(lat_a, lat_b, higher_better=False)
    else:
        lat_winner = "unavailable"

    paired_n = summary.get("paired_n", summary["n_cases"])
    dataset_n = summary.get("dataset_n", paired_n)
    if dataset_n != paired_n:
        st.warning(
            f"Only {paired_n} of {dataset_n} dataset cases were evaluated. "
            f"Variant A missing {summary.get('missing_outputs_a', 0)} outputs; "
            f"Variant B missing {summary.get('missing_outputs_b', 0)}. "
            "The leaderboard reflects the paired subset only."
        )

    rows = [
        {
            "Metric": "Average quality (1-5)",
            a_name: summary["avg_quality_a"],
            b_name: summary["avg_quality_b"],
            "Winner": winner_label(summary["avg_quality_a"], summary["avg_quality_b"]),
        },
        {"Metric": "Wins (B better)", a_name: "—", b_name: summary["wins_b"], "Winner": "—"},
        {"Metric": "Regressions (B worse)", a_name: "—", b_name: summary["regressions_b"], "Winner": "—"},
        {"Metric": "Ties", a_name: summary["ties"], b_name: summary["ties"], "Winner": "—"},
        {"Metric": "Cases evaluated", a_name: paired_n, b_name: paired_n, "Winner": "—"},
        {"Metric": "Average latency", a_name: lat_a_str, b_name: lat_b_str, "Winner": lat_winner},
        {"Metric": "Local evaluation cost", a_name: "$0.00", b_name: "$0.00", "Winner": "—"},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Cost is $0.00 because all scoring is local. No paid API was called.")


def render_category_breakdown(summary: Dict[str, Any]) -> None:
    st.subheader("Category breakdown")
    rows = []
    for c in summary["category_breakdown"]:
        rows.append({
            "Category": c["category"] + (" (high-risk)" if c["high_risk"] else ""),
            "n": c["n"],
            "Avg A": c["avg_a"],
            "Avg B": c["avg_b"],
            "Delta": c["delta"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(
        "Delta = average B minus average A. Negative = regression. High-risk "
        "categories trigger DO NOT SHIP when delta < -0.5."
    )


def render_decision_memo(summary: Dict[str, Any]) -> None:
    st.subheader("Decision memo")
    rec = summary["recommendation"]
    label = rec["label"]
    if label == "SHIP":
        st.success(f"Recommendation: {label}")
    elif label == "SHIP WITH CAVEAT":
        st.warning(f"Recommendation: {label}")
    else:
        st.error(f"Recommendation: {label}")
    st.write(rec["explanation"])

    memo = summary["decision_memo"]
    st.markdown("**Top risks**")
    for r in memo["top_risks"]:
        st.write(f"- {r}")

    st.markdown("**Top failed or regressed cases**")
    if not memo["top_failed_cases"]:
        st.write("None — Variant B did not regress on any case.")
    else:
        for f in memo["top_failed_cases"]:
            st.write(
                f"- `{f['case_id']}` ({f['category']}): score delta {f['delta']:+}"
            )

    st.markdown("**Suggested next action**")
    st.write(memo["next_action"])


def render_failed_cases(result: Dict[str, Any]) -> None:
    st.subheader("Failed cases explorer")
    paired = result["paired"]
    failed = [(cid, a, b) for cid, a, b in paired if b["quality_score"] < a["quality_score"]]
    if not failed:
        st.info("No regressions detected — Variant B did not score lower than Variant A on any case.")
        return
    st.caption(f"{len(failed)} case(s) where Variant B scored lower than Variant A.")
    for cid, a, b in failed:
        with st.expander(
            f"{cid} — {a['category']} — A:{a['quality_score']} → B:{b['quality_score']}"
        ):
            st.markdown(f"**Input.** {a['input']}")
            st.markdown(f"**Expected behaviour.** {a['expected']}")
            cols = st.columns(2)
            with cols[0]:
                st.markdown(f"**{a['variant_name']} (A) output**")
                st.write(a["output"] or "_(no output)_")
                st.caption(f"Score {a['quality_score']}/5 — {a['judge_reasoning']}")
                st.json(a["rubric_breakdown"])
            with cols[1]:
                st.markdown(f"**{b['variant_name']} (B) output**")
                st.write(b["output"] or "_(no output)_")
                st.caption(f"Score {b['quality_score']}/5 — {b['judge_reasoning']}")
                st.json(b["rubric_breakdown"])


def render_results_table(result: Dict[str, Any]) -> None:
    st.subheader("Full results")
    rows = []
    for r in result["rows_a"] + result["rows_b"]:
        rows.append({
            "case_id": r["case_id"],
            "category": r["category"],
            "variant": r["variant_label"],
            "name": r["variant_name"],
            "score": r["quality_score"],
            "latency_ms": r["latency_ms"] if r["latency_ms"] is not None else "unavailable",
            "scoring_method": r["scoring_method"],
            "missing_output": r.get("missing_output", False),
            "output_preview": (r["output"] or "")[:140],
        })
    df = pd.DataFrame(rows).sort_values(["case_id", "variant"])
    st.dataframe(df, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="EvalForge", layout="wide")
    section_header()

    st.markdown("---")

    mode = st.selectbox(
        "Comparison mode",
        ["Prompt vs Prompt", "Model vs Model", "Custom Variant Comparison"],
        index=0,
        help="All three modes use the same eval engine. Only the labels and inputs differ.",
    )

    dataset = dataset_loader_ui()
    if dataset is None:
        st.stop()
    st.session_state["current_dataset"] = dataset

    st.subheader("2. Variants")

    col_a, col_b = st.columns(2)

    if mode == "Prompt vs Prompt":
        with col_a:
            st.markdown("### Variant A")
            name_a = st.text_input("Source name", value="prompt_a", key="name_a")
            prompt_a = st.text_area(
                "Prompt A",
                value=_read_text(DEFAULT_PROMPT_A),
                height=180,
                key="prompt_a",
            )
            outputs_a = outputs_loader_ui("Variant A", DEFAULT_OUTPUTS_A, "out_a", dataset)
        with col_b:
            st.markdown("### Variant B")
            name_b = st.text_input("Source name", value="prompt_b", key="name_b")
            prompt_b = st.text_area(
                "Prompt B",
                value=_read_text(DEFAULT_PROMPT_B),
                height=180,
                key="prompt_b",
            )
            outputs_b = outputs_loader_ui("Variant B", DEFAULT_OUTPUTS_B, "out_b", dataset)
    elif mode == "Model vs Model":
        st.markdown("**Shared prompt**")
        shared_prompt = st.text_area(
            "Prompt used for both models",
            value=_read_text(DEFAULT_PROMPT_B),
            height=180,
            key="shared_prompt",
        )
        with col_a:
            st.markdown("### Model A")
            name_a = st.text_input("Model A name", value="model_a", key="name_a")
            outputs_a = outputs_loader_ui("Model A", DEFAULT_OUTPUTS_A, "out_a", dataset)
        with col_b:
            st.markdown("### Model B")
            name_b = st.text_input("Model B name", value="model_b", key="name_b")
            outputs_b = outputs_loader_ui("Model B", DEFAULT_OUTPUTS_B, "out_b", dataset)
        prompt_a = shared_prompt
        prompt_b = shared_prompt
    else:  # Custom Variant Comparison
        with col_a:
            st.markdown("### Variant A")
            name_a = st.text_input("Variant A name", value="variant_a", key="name_a")
            prompt_a = st.text_area(
                "Prompt A (optional)",
                value=_read_text(DEFAULT_PROMPT_A),
                height=140,
                key="prompt_a",
            )
            outputs_a = outputs_loader_ui("Variant A", DEFAULT_OUTPUTS_A, "out_a", dataset)
        with col_b:
            st.markdown("### Variant B")
            name_b = st.text_input("Variant B name", value="variant_b", key="name_b")
            prompt_b = st.text_area(
                "Prompt B (optional)",
                value=_read_text(DEFAULT_PROMPT_B),
                height=140,
                key="prompt_b",
            )
            outputs_b = outputs_loader_ui("Variant B", DEFAULT_OUTPUTS_B, "out_b", dataset)

    if outputs_a is None or outputs_b is None:
        st.info("Provide outputs for both variants to run the eval.")
        st.stop()

    dataset_ids = {c["id"] for c in dataset}
    err_a, warn_a = validate_outputs(outputs_a, dataset_ids)
    err_b, warn_b = validate_outputs(outputs_b, dataset_ids)
    blocking = bool(err_a or err_b)
    for label, errors, warnings in (("Variant A", err_a, warn_a), ("Variant B", err_b, warn_b)):
        if errors:
            st.error(f"{label} blocking issues:")
            for e in errors:
                st.write(f"- {e}")
        for w in warnings:
            st.warning(f"{label}: {w}")
    if blocking:
        st.info("Fix the blocking issues above before running the eval.")
        st.stop()

    variant_a = {
        "label": "A",
        "source_type": "uploaded_output",
        "model_name": name_a,
        "prompt": prompt_a,
        "outputs": outputs_a,
    }
    variant_b = {
        "label": "B",
        "source_type": "uploaded_output",
        "model_name": name_b,
        "prompt": prompt_b,
        "outputs": outputs_b,
    }

    st.markdown("---")
    if st.button("Run eval", type="primary"):
        try:
            with st.spinner("Scoring locally…"):
                result = run_eval(dataset, variant_a, variant_b)
        except Exception as e:
            log.exception("run_eval failed")
            st.error(f"Eval failed: {e}")
            with st.expander("Traceback"):
                st.code(traceback.format_exc())
            st.stop()
        st.session_state["last_result"] = result
        try:
            saved = save_run(result, RUNS_DIR)
            st.session_state["last_run_path"] = str(saved.relative_to(ROOT))
        except Exception as e:
            log.exception("save_run failed")
            st.warning(f"Could not save run: {e}")

    result = st.session_state.get("last_result")
    if result is None:
        st.info("Click **Run eval** to score the variants.")
        return

    st.markdown("---")
    summary = result["summary"]
    render_leaderboard(summary)
    st.markdown("---")
    render_category_breakdown(summary)
    st.markdown("---")
    render_decision_memo(summary)
    st.markdown("---")
    render_failed_cases(result)
    st.markdown("---")
    render_results_table(result)
    saved_path = st.session_state.get("last_run_path")
    if saved_path:
        st.success(f"Run saved to `{saved_path}`")


if __name__ == "__main__":
    main()
