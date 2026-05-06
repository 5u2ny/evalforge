# EvalForge

> Stop shipping prompt changes on vibes.

An open-source LLM regression testing and release-decision tool for AI PMs and prompt owners. EvalForge compares two prompt or model variants against a golden dataset and produces a release recommendation backed by quality, regressions, and category-level reliability. No paid APIs. No API keys. No auth. No database.

## The problem

Every AI team has the same daily problem. Someone tweaks a prompt. The change ships. A different feature regresses three days later and nobody notices. LLM outputs are non-deterministic, so eyeballing a few cases is not a release gate. The current workflow is "paste a few examples in the playground, read the answers, ship on vibes." Quality regresses silently.

## The solution

EvalForge runs a fixed golden dataset against two variants you provide, scores every case locally with deterministic and rubric-based scorers, and returns:

- a side-by-side leaderboard
- a category-level breakdown that surfaces regressions hidden by averages
- a decision memo with top risks, top failed cases, and a next action
- a failed-cases explorer with rubric reasoning per case
- a release recommendation: **SHIP**, **SHIP WITH CAVEAT**, or **DO NOT SHIP**

## Why no paid APIs

This v1 is built to be open-source friendly. It ships with a bundled golden dataset and bundled sample outputs for both variants so anyone can clone the repo and run an eval in under a minute. You can plug in real outputs from any model — local Ollama, LM Studio, ChatGPT copy-paste, Claude.ai, Gemini, anything that produces JSONL — by uploading or pasting the file. The product does not call any paid API and does not require any key.

## Core features

- Three comparison modes built on a single shared eval engine
  - **Prompt vs Prompt**
  - **Model vs Model**
  - **Custom Variant Comparison**
- Bundled golden dataset of 24 realistic customer-support cases across 9 categories
- Bundled weak-baseline (Variant A) and improved (Variant B) sample outputs, clearly labelled as sample data
- Local rubric scorer that grades empathy, expected-behavior coverage, next-action clarity, and policy safety
- Exact-match and contains-keyword scorers for deterministic cases
- Category-level breakdown with high-risk flagging (refund, billing, policy edge, escalation)
- Decision memo with risks, failed cases, and a next action
- Run results saved as timestamped JSONL in `data/runs/`
- Local evaluation cost is `$0.00` because nothing is called

## How it works

1. Load the bundled golden dataset (or upload your own JSONL).
2. Provide outputs for Variant A and Variant B. Use the bundled samples, upload JSONL, paste JSONL, or type manually.
3. The eval engine scores every case locally and aggregates per-category averages.
4. The recommendation engine produces a release decision based on quality delta, regression count, and high-risk category performance.
5. Results render as a leaderboard, category breakdown, decision memo, failed-cases explorer, and full results table. The run is saved to `data/runs/`.

## Architecture

A single shared abstraction `Variant` powers all three modes. Prompt-vs-prompt and model-vs-model are not separate engines — they are presets over the same engine.

```
Variant = {
  "label":       "A" | "B",
  "source_type": "manual_output" | "uploaded_output" | "local_stub",
  "model_name":  str,
  "prompt":      str,
  "outputs":     [{ "case_id": str, "output": str, "latency_ms": float | None }, …]
}

run_eval(dataset, variant_a, variant_b) -> { rows_a, rows_b, paired, summary }
```

| Layer | File | Responsibility |
|---|---|---|
| UI | `app.py` | Streamlit screens, mode selector, loaders, result rendering |
| Engine | `eval_engine.py` | Pair cases, score variants, compute summary, build recommendation, save run |
| Scorers | `scorers.py` | Local rubric + exact-match + contains-keyword scoring |
| Validation | `utils.py` | JSONL load, parse, validate dataset and outputs |

## Screenshots

Add screenshots after running locally. Suggested files: `screenshots/leaderboard.png`, `screenshots/decision_memo.png`, `screenshots/failed_cases.png`.

## Demo links

- Live demo: _add Streamlit Community Cloud URL after deployment_
- 90-second Loom: _add Loom link after recording_

## Benchmark card

> 24 cases · 2 variants · 3 regressions caught · $0.00 local eval cost · **SHIP WITH CAVEAT**

The point of EvalForge is not "Variant B wins everywhere." The point is that B improves overall quality (2.21 → 3.88 average) while quietly regressing on 3 cases that a vibe-check on a few outputs would miss. EvalForge surfaces those 3 cases in the failed-cases explorer, weighs them in the decision memo, and downgrades the recommendation from SHIP to SHIP WITH CAVEAT. That is the workflow this product exists to enforce.

## How to run locally

Requires Python 3.10 or newer.

```bash
git clone <your-fork-url>
cd EvalForge
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. No `.env`, no API keys, no extra setup. Click **Run eval** with the defaults and you should see avg A 2.21 → avg B 3.88, 20 wins, 3 regressions, ties 1, recommendation **SHIP WITH CAVEAT**. Open the failed-cases explorer to see the 3 regressions: an over-escalated billing duplicate, a vague 90-day-return reply, and an over-promised damaged-item handoff.

## PM artifacts

- [PRD](docs/PRD.md)
- [Personas](docs/persona.md)
- [Metrics and KPI tree](docs/metrics_kpi_tree.md)
- [Risk register](docs/risk_register.md)
- [Roadmap](docs/roadmap.md)
- [Experiment plan](docs/experiment_plan.md)
- [Demo script](docs/demo_script.md)

## Roadmap

- **v1 (now).** Local rubric and deterministic scoring, three comparison modes, bundled dataset, bundled sample outputs, save run.
- **v2.** Optional local-model integration (Ollama, LM Studio, llama.cpp); rubric editor; eval history dashboard; dataset generator.
- **v3.** Local LLM-as-judge with judge-vs-human agreement audit; CI check that blocks unevaluated prompt changes; prompt diff viewer; exportable release memo; regression severity labels.

## What this project demonstrates

- AI PM judgment about LLM quality control under nondeterminism
- Eval design: dataset, scorer, run, decision
- Metric thinking: regressions and category-level performance over headline averages
- Release discipline: every change has a recommendation backed by evidence
- Open-source practicality: no API keys, no auth, no database, runs anywhere with Python

The bundled outputs are sample data shipped with the repo for demonstration. Replace them with real model outputs by uploading or pasting JSONL files.
