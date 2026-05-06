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


# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------
# Visual identity — inline SVG logo + theme CSS
# ----------------------------------------------------------------------------

LOGO_SVG = """<svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect width="36" height="36" rx="10" fill="#4F46E5"/>
  <path d="M10 18.5 L15.5 24 L26 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --ef-bg: #FAFAF9;
  --ef-surface: #FFFFFF;
  --ef-surface-soft: #F5F5F4;
  --ef-border: #E7E5E4;
  --ef-border-strong: #D6D3D1;
  --ef-text: #0C0A09;
  --ef-text-muted: #57534E;
  --ef-text-faint: #A8A29E;
  --ef-accent: #4F46E5;
  --ef-accent-hover: #4338CA;
  --ef-accent-soft: #EEF2FF;

  --ef-emerald: #047857;
  --ef-emerald-bg: #ECFDF5;
  --ef-emerald-border: #6EE7B7;

  --ef-amber: #92400E;
  --ef-amber-bg: #FFFBEB;
  --ef-amber-border: #FCD34D;

  --ef-rose: #BE123C;
  --ef-rose-bg: #FFF1F2;
  --ef-rose-border: #FDA4AF;

  --ef-radius: 12px;
  --ef-radius-sm: 8px;
  --ef-shadow-sm: 0 1px 2px rgba(12, 10, 9, 0.04);
  --ef-shadow-md: 0 1px 3px rgba(12, 10, 9, 0.06), 0 4px 12px rgba(12, 10, 9, 0.03);
}

html, body, [class*="stApp"], [data-testid="stAppViewContainer"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--ef-bg) !important;
  color: var(--ef-text);
}

/* hide stock streamlit chrome for a clean app shell */
#MainMenu,
header[data-testid="stHeader"],
footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* main container */
[data-testid="stMain"] .block-container,
[data-testid="stAppViewContainer"] .block-container {
  padding-top: 2.25rem;
  padding-bottom: 4rem;
  max-width: 1180px;
}

/* typography */
h1, h2, h3, h4 {
  font-family: 'Inter', sans-serif;
  letter-spacing: -0.022em;
  color: var(--ef-text);
  font-weight: 700;
}
.stMarkdown p, [data-testid="stMarkdownContainer"] p {
  color: var(--ef-text);
  line-height: 1.6;
  font-size: 0.9375rem;
}
.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--ef-text-muted) !important;
  font-size: 0.8125rem;
}

/* hide built-in subheader spacing where we render our own */
.ef-section + [data-testid="stMarkdownContainer"] { margin-top: 0.25rem; }

/* hero */
.ef-hero {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  margin: 0 0 2rem;
  padding: 1.75rem 1.875rem;
  background: var(--ef-surface);
  border: 1px solid var(--ef-border);
  border-radius: var(--ef-radius);
  box-shadow: var(--ef-shadow-sm);
}
.ef-hero-mark {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}
.ef-hero-name {
  font-size: 1.625rem;
  font-weight: 800;
  letter-spacing: -0.028em;
  margin: 0;
  line-height: 1;
  color: var(--ef-text);
}
.ef-hero-meta {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--ef-text-muted);
  margin-top: 0.25rem;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.04em;
}
.ef-hero-meta-dot {
  width: 3px; height: 3px; border-radius: 999px;
  background: var(--ef-text-faint);
  display: inline-block;
}
.ef-hero-tagline {
  font-size: 1.375rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ef-text);
  margin: 0.25rem 0 0;
  line-height: 1.25;
}
.ef-hero-sub {
  font-size: 0.9375rem;
  color: var(--ef-text-muted);
  line-height: 1.55;
  max-width: 720px;
  margin: 0;
}

/* section header */
.ef-section {
  display: flex;
  align-items: baseline;
  gap: 0.875rem;
  margin: 1.75rem 0 1rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--ef-border);
}
.ef-section-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--ef-text-faint);
  letter-spacing: 0.1em;
}
.ef-section-title {
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--ef-text);
  letter-spacing: -0.01em;
}
.ef-section-meta {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--ef-text-faint);
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.02em;
}

/* verdict card — the headline of the results */
.ef-verdict {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 1.5rem 1.625rem;
  border-radius: var(--ef-radius);
  border: 1px solid;
  margin: 0.25rem 0 1.75rem;
  box-shadow: var(--ef-shadow-sm);
}
.ef-verdict-eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  opacity: 0.78;
}
.ef-verdict-label {
  font-size: 1.875rem;
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1;
}
.ef-verdict-explanation {
  font-size: 0.9375rem;
  line-height: 1.55;
  opacity: 0.92;
}
.ef-verdict.ship {
  background: var(--ef-emerald-bg);
  border-color: var(--ef-emerald-border);
  color: var(--ef-emerald);
}
.ef-verdict.caveat {
  background: var(--ef-amber-bg);
  border-color: var(--ef-amber-border);
  color: var(--ef-amber);
}
.ef-verdict.noship {
  background: var(--ef-rose-bg);
  border-color: var(--ef-rose-border);
  color: var(--ef-rose);
}

/* metric card */
.ef-metric {
  background: var(--ef-surface);
  border: 1px solid var(--ef-border);
  border-radius: var(--ef-radius-sm);
  padding: 0.95rem 1.05rem 1rem;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  box-shadow: var(--ef-shadow-sm);
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
.ef-metric:hover {
  border-color: var(--ef-border-strong);
  box-shadow: var(--ef-shadow-md);
}
.ef-metric-label {
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--ef-text-muted);
}
.ef-metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--ef-text);
  letter-spacing: -0.025em;
  line-height: 1.05;
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.ef-metric-arrow {
  color: var(--ef-text-faint);
  font-weight: 400;
  font-size: 1.1rem;
  margin: 0 0.15rem;
}
.ef-metric-delta {
  font-size: 0.8125rem;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}
.ef-metric-delta.good { color: var(--ef-emerald); }
.ef-metric-delta.bad { color: var(--ef-rose); }
.ef-metric-delta.neutral { color: var(--ef-text-faint); }
.ef-metric-meta {
  font-size: 0.72rem;
  color: var(--ef-text-faint);
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.02em;
}

/* notice / banner */
.ef-notice {
  background: var(--ef-amber-bg);
  border: 1px solid var(--ef-amber-border);
  border-radius: var(--ef-radius-sm);
  padding: 0.7rem 0.9rem;
  font-size: 0.875rem;
  color: var(--ef-amber);
  margin: 0.5rem 0 1rem;
}

/* kpi pill (decision memo risks/next action) */
.ef-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.ef-pill.muted {
  background: var(--ef-surface-soft);
  color: var(--ef-text-muted);
  border: 1px solid var(--ef-border);
}

/* button */
.stButton > button,
.stDownloadButton > button {
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9375rem;
  padding: 0.6rem 1.2rem;
  transition: all 150ms ease;
  cursor: pointer;
}
.stButton > button[kind="primary"] {
  background: var(--ef-accent);
  border: 1px solid var(--ef-accent);
  color: white;
}
.stButton > button[kind="primary"]:hover {
  background: var(--ef-accent-hover);
  border-color: var(--ef-accent-hover);
  transform: none;
}
.stButton > button[kind="secondary"] {
  background: var(--ef-surface);
  border: 1px solid var(--ef-border);
  color: var(--ef-text);
}
.stButton > button[kind="secondary"]:hover {
  border-color: var(--ef-border-strong);
  background: var(--ef-surface-soft);
}

/* form controls */
.stTextInput input,
.stTextArea textarea,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
  border-radius: 8px !important;
  border-color: var(--ef-border) !important;
  font-family: 'Inter', sans-serif !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
  border-color: var(--ef-accent) !important;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15) !important;
}

/* code & mono content */
.stTextArea textarea {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.84rem !important;
  line-height: 1.55 !important;
}

/* checkbox */
.stCheckbox > label {
  font-size: 0.9rem;
  color: var(--ef-text);
}

/* expander */
[data-testid="stExpander"] {
  background: var(--ef-surface);
  border: 1px solid var(--ef-border) !important;
  border-radius: var(--ef-radius-sm);
  margin-bottom: 0.6rem;
  box-shadow: var(--ef-shadow-sm);
}
[data-testid="stExpander"] summary {
  font-weight: 500;
  color: var(--ef-text);
  cursor: pointer !important;
  padding: 0.7rem 1rem !important;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
}
[data-testid="stExpander"] summary:hover {
  background: var(--ef-surface-soft);
}

/* dataframe */
[data-testid="stDataFrame"] {
  border: 1px solid var(--ef-border);
  border-radius: var(--ef-radius-sm);
  overflow: hidden;
}

/* alerts (st.warning/error/info/success) — soften streamlit defaults */
[data-testid="stAlert"] {
  border-radius: var(--ef-radius-sm) !important;
  border-width: 1px !important;
  font-size: 0.875rem;
}

/* spinner area */
.stSpinner > div {
  border-color: var(--ef-accent) transparent transparent transparent !important;
}

/* horizontal rule */
hr {
  border: 0;
  border-top: 1px solid var(--ef-border);
  margin: 1.5rem 0;
}

/* footer */
.ef-footer {
  margin-top: 2.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--ef-border);
  font-size: 0.75rem;
  color: var(--ef-text-faint);
  display: flex;
  justify-content: space-between;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.04em;
}
.ef-footer a {
  color: var(--ef-text-muted);
  text-decoration: none;
  border-bottom: 1px dotted var(--ef-text-faint);
}
.ef-footer a:hover { color: var(--ef-text); }

/* small responsive tweaks */
@media (max-width: 768px) {
  .ef-hero { padding: 1.25rem 1.25rem; }
  .ef-hero-tagline { font-size: 1.15rem; }
  .ef-verdict { padding: 1.1rem 1.25rem; }
  .ef-verdict-label { font-size: 1.5rem; }
}
</style>
"""


def _inject_theme() -> None:
    # Use st.html (bypasses markdown processor) so CSS isn't escaped or
    # mangled by Streamlit's markdown sanitizer.
    if hasattr(st, "html"):
        st.html(_THEME_CSS)
    else:
        st.markdown(_THEME_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Component helpers
# ----------------------------------------------------------------------------

def _hero() -> None:
    st.markdown(
        f"""
        <div class="ef-hero">
          <div class="ef-hero-mark">
            {LOGO_SVG}
            <div>
              <div class="ef-hero-name">EvalForge</div>
              <div class="ef-hero-meta">
                <span>v0.1.0</span><span class="ef-hero-meta-dot"></span>
                <span>open source</span><span class="ef-hero-meta-dot"></span>
                <span>no paid APIs</span>
              </div>
            </div>
          </div>
          <div class="ef-hero-tagline">Stop shipping prompt changes on vibes.</div>
          <div class="ef-hero-sub">Compare prompt and model variants across quality, regressions, and release risk &mdash; locally, with no API keys.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section(num: str, title: str, meta: str = "") -> None:
    meta_html = f'<span class="ef-section-meta">{meta}</span>' if meta else ""
    st.markdown(
        f"""
        <div class="ef-section">
          <span class="ef-section-num">{num}</span>
          <span class="ef-section-title">{title}</span>
          {meta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _verdict_card(rec: Dict[str, str]) -> None:
    label = rec["label"]
    cls = {
        "SHIP": "ship",
        "SHIP WITH CAVEAT": "caveat",
        "DO NOT SHIP": "noship",
    }.get(label, "caveat")
    st.markdown(
        f"""
        <div class="ef-verdict {cls}">
          <div class="ef-verdict-eyebrow">Recommendation</div>
          <div class="ef-verdict-label">{label}</div>
          <div class="ef-verdict-explanation">{rec["explanation"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _metric(
    col,
    label: str,
    value_html: str,
    delta: Optional[str] = None,
    delta_class: str = "neutral",
    meta: Optional[str] = None,
) -> None:
    delta_html = (
        f'<span class="ef-metric-delta {delta_class}">{delta}</span>' if delta else ""
    )
    meta_html = f'<div class="ef-metric-meta">{meta}</div>' if meta else ""
    col.markdown(
        f"""
        <div class="ef-metric">
          <div class="ef-metric-label">{label}</div>
          <div class="ef-metric-value">{value_html}{delta_html}</div>
          {meta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _notice(text: str) -> None:
    st.markdown(f'<div class="ef-notice">{text}</div>', unsafe_allow_html=True)


def _footer() -> None:
    st.markdown(
        """
        <div class="ef-footer">
          <span>EvalForge · v0.1.0</span>
          <span>Built locally · 96 tests · $0.00 per run</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# Cached file IO
# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------------

def dataset_loader_ui() -> Optional[List[Dict[str, Any]]]:
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


# ----------------------------------------------------------------------------
# Result rendering
# ----------------------------------------------------------------------------

def render_metrics(summary: Dict[str, Any]) -> None:
    a_name = summary["variant_a_name"]
    b_name = summary["variant_b_name"]
    avg_a = summary["avg_quality_a"]
    avg_b = summary["avg_quality_b"]
    delta = round(avg_b - avg_a, 2)
    delta_str = f"{delta:+.2f}"
    delta_class = "good" if delta > 0 else ("bad" if delta < 0 else "neutral")

    paired_n = summary.get("paired_n", summary["n_cases"])
    dataset_n = summary.get("dataset_n", paired_n)
    if dataset_n != paired_n:
        _notice(
            f"Only {paired_n} of {dataset_n} dataset cases were evaluated. "
            f"Variant A missing {summary.get('missing_outputs_a', 0)} outputs · "
            f"Variant B missing {summary.get('missing_outputs_b', 0)}. "
            "Metrics below reflect the paired subset only."
        )

    cols = st.columns(4)
    quality_html = (
        f'{avg_a}<span class="ef-metric-arrow">→</span>{avg_b}'
    )
    _metric(
        cols[0],
        "Avg quality (1-5)",
        quality_html,
        delta=delta_str,
        delta_class=delta_class,
        meta=f"{a_name} vs {b_name}",
    )

    wins = summary["wins_b"]
    _metric(
        cols[1],
        "Wins for B",
        str(wins),
        meta=f"{wins} of {paired_n} cases",
    )

    regs = summary["regressions_b"]
    reg_class = "bad" if regs > 0 else "good"
    _metric(
        cols[2],
        "Regressions",
        str(regs),
        delta="caught" if regs > 0 else "none",
        delta_class=reg_class,
        meta="cases where B < A",
    )

    _metric(
        cols[3],
        "Ties",
        str(summary["ties"]),
        meta="A and B scored equal",
    )

    cols2 = st.columns(3)
    _metric(
        cols2[0],
        "Cases evaluated",
        str(paired_n),
        meta=f"of {dataset_n} dataset cases" if dataset_n != paired_n else "all dataset cases scored",
    )

    lat_a = summary["avg_latency_ms_a"]
    lat_b = summary["avg_latency_ms_b"]
    if lat_a is not None and lat_b is not None:
        lat_value = f"{lat_a}<span class=\"ef-metric-arrow\">→</span>{lat_b} ms"
        lat_meta = "ms per case"
    else:
        lat_value = "—"
        lat_meta = "no latency in JSONL"
    _metric(cols2[1], "Avg latency", lat_value, meta=lat_meta)

    _metric(
        cols2[2],
        "Local eval cost",
        "$0.00",
        meta="no API was called",
    )


def render_category_breakdown(summary: Dict[str, Any]) -> None:
    rows = []
    for c in summary["category_breakdown"]:
        rows.append({
            "Category": c["category"] + ("  ·  high-risk" if c["high_risk"] else ""),
            "n": c["n"],
            "Avg A": c["avg_a"],
            "Avg B": c["avg_b"],
            "Δ": c["delta"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(
        "Δ = average B minus average A. Negative = regression. "
        "High-risk categories trigger DO NOT SHIP when Δ < -0.5."
    )


def render_decision_details(summary: Dict[str, Any]) -> None:
    memo = summary["decision_memo"]

    st.markdown("**Top risks**")
    for r in memo["top_risks"]:
        st.write(f"- {r}")

    st.markdown("**Top failed or regressed cases**")
    if not memo["top_failed_cases"]:
        st.write("None &mdash; Variant B did not regress on any case.")
    else:
        for f in memo["top_failed_cases"]:
            st.markdown(
                f"- <span class=\"ef-pill muted\">{f['category']}</span> "
                f"`{f['case_id']}` &nbsp; score delta {f['delta']:+}",
                unsafe_allow_html=True,
            )

    st.markdown("**Suggested next action**")
    st.write(memo["next_action"])


def render_failed_cases(result: Dict[str, Any]) -> None:
    paired = result["paired"]
    failed = [(cid, a, b) for cid, a, b in paired if b["quality_score"] < a["quality_score"]]
    if not failed:
        st.info("No regressions detected — Variant B did not score lower than Variant A on any case.")
        return
    st.caption(f"{len(failed)} case(s) where Variant B scored lower than Variant A.")
    for cid, a, b in failed:
        with st.expander(
            f"{cid}  ·  {a['category']}  ·  A:{a['quality_score']} → B:{b['quality_score']}"
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
    rows = []
    for r in result["rows_a"] + result["rows_b"]:
        rows.append({
            "case_id": r["case_id"],
            "category": r["category"],
            "variant": r["variant_label"],
            "name": r["variant_name"],
            "score": r["quality_score"],
            "latency_ms": r["latency_ms"] if r["latency_ms"] is not None else "—",
            "scoring_method": r["scoring_method"],
            "missing_output": r.get("missing_output", False),
            "output_preview": (r["output"] or "")[:140],
        })
    df = pd.DataFrame(rows).sort_values(["case_id", "variant"])
    st.dataframe(df, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="EvalForge",
        page_icon="✓",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_theme()
    _hero()

    # ---- Setup -----------------------------------------------------------

    _section("01", "Comparison mode")
    mode = st.selectbox(
        "Comparison mode",
        ["Prompt vs Prompt", "Model vs Model", "Custom Variant Comparison"],
        index=0,
        label_visibility="collapsed",
        help="All three modes use the same eval engine. Only the labels and inputs differ.",
    )

    _section("02", "Dataset")
    dataset = dataset_loader_ui()
    if dataset is None:
        st.stop()
    st.session_state["current_dataset"] = dataset

    _section("03", "Variants", meta=f"mode: {mode.lower()}")
    col_a, col_b = st.columns(2)

    if mode == "Prompt vs Prompt":
        with col_a:
            st.markdown("**Variant A**")
            name_a = st.text_input("Source name", value="prompt_a", key="name_a", label_visibility="collapsed")
            prompt_a = st.text_area(
                "Prompt A",
                value=_read_text(DEFAULT_PROMPT_A),
                height=180,
                key="prompt_a",
            )
            outputs_a = outputs_loader_ui("Variant A", DEFAULT_OUTPUTS_A, "out_a", dataset)
        with col_b:
            st.markdown("**Variant B**")
            name_b = st.text_input("Source name", value="prompt_b", key="name_b", label_visibility="collapsed")
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
            label_visibility="collapsed",
        )
        with col_a:
            st.markdown("**Model A**")
            name_a = st.text_input("Model A name", value="model_a", key="name_a", label_visibility="collapsed")
            outputs_a = outputs_loader_ui("Model A", DEFAULT_OUTPUTS_A, "out_a", dataset)
        with col_b:
            st.markdown("**Model B**")
            name_b = st.text_input("Model B name", value="model_b", key="name_b", label_visibility="collapsed")
            outputs_b = outputs_loader_ui("Model B", DEFAULT_OUTPUTS_B, "out_b", dataset)
        prompt_a = shared_prompt
        prompt_b = shared_prompt
    else:  # Custom Variant Comparison
        with col_a:
            st.markdown("**Variant A**")
            name_a = st.text_input("Variant A name", value="variant_a", key="name_a", label_visibility="collapsed")
            prompt_a = st.text_area(
                "Prompt A (optional)",
                value=_read_text(DEFAULT_PROMPT_A),
                height=140,
                key="prompt_a",
            )
            outputs_a = outputs_loader_ui("Variant A", DEFAULT_OUTPUTS_A, "out_a", dataset)
        with col_b:
            st.markdown("**Variant B**")
            name_b = st.text_input("Variant B name", value="variant_b", key="name_b", label_visibility="collapsed")
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
    for v_label, errors, warnings in (("Variant A", err_a, warn_a), ("Variant B", err_b, warn_b)):
        if errors:
            st.error(f"{v_label} blocking issues:")
            for e in errors:
                st.write(f"- {e}")
        for w in warnings:
            st.warning(f"{v_label}: {w}")
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

    st.markdown("<div style='margin-top: 0.75rem'></div>", unsafe_allow_html=True)
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
        _footer()
        return

    summary = result["summary"]

    # ---- Results --------------------------------------------------------
    # Verdict is the headline; metrics support it; everything else is detail.

    _section("04", "Verdict")
    _verdict_card(summary["recommendation"])

    _section("05", "Metrics")
    render_metrics(summary)

    _section("06", "Category breakdown")
    render_category_breakdown(summary)

    _section("07", "Decision details")
    render_decision_details(summary)

    _section("08", "Failed cases", meta=f"{summary['regressions_b']} regression(s)")
    render_failed_cases(result)

    _section("09", "Full results", meta=f"{summary['paired_n']} paired cases")
    render_results_table(result)

    saved_path = st.session_state.get("last_run_path")
    if saved_path:
        st.caption(f"Run saved to `{saved_path}`")

    _footer()


if __name__ == "__main__":
    main()
