# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Layout

This directory (`/Users/e/Documents/Claude`) is a multi-project workspace. Active sub-projects:

- `Projects/focus-os-student-edition/` — Electron desktop app (three-process: main/preload/renderer). Has its own `CLAUDE.md`.
- `Projects/Portfolio/` — React/Vite portfolio site.
- `Projects/Github/EvalForge/` — contains `BUILD_GUIDE.md` (older guide using paid APIs) and a `requirements.txt`. Use as reference only; the current spec below supersedes it.
- `/Users/e/Documents/EvalForge/` — **the target build directory** (currently empty; EvalForge should be built here).

## EvalForge Dev Commands

Once the project is scaffolded in `/Users/e/Documents/EvalForge/`:

```bash
cd /Users/e/Documents/EvalForge
pip install -r requirements.txt   # streamlit, pandas only
streamlit run app.py              # launches the app at localhost:8501
```

No `.env` file required. No API keys required. All scoring is local and deterministic.

## Mission

Build EvalForge: a lightweight, fully open-source LLM evaluation and release-decision tool for AI PMs, founders, and prompt owners.

EvalForge helps users stop shipping prompt and model changes on vibes. It compares two local or user-provided LLM output variants against a golden dataset and produces a release recommendation based on:

- quality
- latency
- regressions
- failed cases
- rubric-based scoring
- decision reasoning

This is a GitHub portfolio project. It must demonstrate AI product judgment, technical fluency, eval design, metric thinking, release discipline, and open-source practicality.

## Critical Constraint

Do not use paid APIs.

Do not require:

- OpenAI API
- Anthropic API
- Gemini API
- hosted paid model APIs
- paid inference providers
- paid databases
- cloud-only dependencies

This project must run locally and remain open-source friendly.

Use offline or local-first evaluation methods for v1.

## Product Positioning

EvalForge is:

> An open-source LLM regression testing and release-decision tool for AI PMs and prompt owners.

EvalForge is not:

- a chatbot
- a generic prompt playground
- a paid API wrapper
- a dashboard full of vanity metrics
- an overbuilt SaaS app
- a RAG product
- an agent framework

The portfolio tagline is:

> Stop shipping prompt changes on vibes.

## Core User

Primary users:

1. AI PM
   - Owns prompt or model behavior.
   - Needs confidence before shipping a change.
   - Cares about quality, regressions, consistency, and decision clarity.

2. Founder
   - Ships quickly.
   - Needs lightweight quality control.
   - Cannot afford silent AI regressions.

3. Applied AI engineer
   - Changes prompts or models frequently.
   - Needs a repeatable regression harness.
   - Wants failed cases surfaced clearly.

4. Open-source builder
   - Wants an evaluation workflow without paid APIs.
   - Needs local, inspectable, forkable tooling.

## Core Job-to-Be-Done

Before I ship a prompt or model change, help me decide if it is actually better across quality, behavior, speed, and regressions using a fixed set of test cases I trust.

## Supported Comparison Modes

EvalForge must support exactly three comparison modes:

1. Prompt vs Prompt
   - Same model or same output source.
   - Different prompts.
   - Used to test whether a prompt change improves behavior.

2. Model vs Model
   - Same prompt.
   - Different model output files or local model runs.
   - Used to test whether switching models preserves or improves quality.

3. Custom Variant Comparison
   - Variant A can use any prompt and output source.
   - Variant B can use any prompt and output source.
   - Advanced mode for flexible experiments.

## Core Architecture Rule

Do not build separate engines for prompt comparison and model comparison.

Use one shared abstraction:

    Variant = {
        "label": "A" or "B",
        "source_type": "manual_output" or "uploaded_output" or "local_stub",
        "model_name": string,
        "prompt": string,
        "outputs": list
    }

All comparison modes must call the same function:

    run_eval(dataset, variant_a, variant_b)

This is the architectural spine of the project. Do not duplicate logic across modes.

## Open-Source V1 Strategy

Since no paid APIs are allowed, v1 should evaluate pre-generated or manually provided outputs.

The app should support:

1. Default demo outputs
   - Include sample Variant A and Variant B outputs for the default dataset.
   - These must be clearly marked as sample outputs.
   - Do not pretend they were generated live.

2. Uploaded output files
   - User can upload JSONL outputs for Variant A and Variant B.
   - EvalForge scores and compares them locally.

3. Manual output entry
   - User can paste outputs for small eval runs.
   - Useful for testing prompt changes from any model UI.

4. Optional local model extension
   - Do not implement full local model inference in v1 unless simple.
   - Add it to roadmap.
   - Possible future support: Ollama, LM Studio, llama.cpp.

## Required Tech Stack

Use:

- Python
- Streamlit
- pandas
- JSONL file storage
- local deterministic scoring
- rubric-based heuristic scoring

Do not use:

- OpenAI SDK
- Anthropic SDK
- paid APIs
- FastAPI
- Docker
- Postgres
- Supabase
- Firebase
- authentication
- vector databases
- React
- Next.js
- LangChain
- LlamaIndex
- unnecessary abstractions

Keep v1 simple, readable, and portfolio-ready.

## Required File Structure

Create or preserve this structure:

    EvalForge/
    ├── CLAUDE.md
    ├── app.py
    ├── eval_engine.py
    ├── scorers.py
    ├── utils.py
    ├── requirements.txt
    ├── .gitignore
    ├── README.md
    ├── data/
    │   ├── golden_dataset.jsonl
    │   ├── sample_outputs_a.jsonl
    │   ├── sample_outputs_b.jsonl
    │   └── runs/
    ├── prompts/
    │   ├── support_prompt_a.txt
    │   └── support_prompt_b.txt
    ├── docs/
    │   ├── PRD.md
    │   ├── persona.md
    │   ├── metrics_kpi_tree.md
    │   ├── risk_register.md
    │   ├── roadmap.md
    │   ├── experiment_plan.md
    │   └── demo_script.md
    └── screenshots/

## Dataset Schema

Default dataset file:

    data/golden_dataset.jsonl

Each row must follow this schema:

    {
      "id": "case_001",
      "input": "Customer says: 'My order is late, this is unacceptable.'",
      "expected": "Empathetic apology, offer to check status, no discount promise.",
      "category": "support_complaint",
      "scoring_method": "rubric"
    }

Create at least 20 realistic customer-support eval cases across:

- angry complaints
- refund requests
- unclear messages
- delivery issues
- policy edge cases
- cancellation requests
- billing confusion
- subscription problems
- damaged item complaints
- escalation requests

The dataset must feel realistic. Do not write fake demo cases like "I need help." Use cases that reveal differences between weak and strong prompts.

## Output File Schema

Default sample output files:

    data/sample_outputs_a.jsonl
    data/sample_outputs_b.jsonl

Each output row must follow this schema:

    {
      "case_id": "case_001",
      "output": "I am sorry your order is late. I can check the latest delivery status for you. I cannot promise a discount, but I can help review the issue."
    }

Every `case_id` must match a case in the golden dataset.

Variant A should include weaker outputs.

Variant B should include improved outputs.

The app must clearly label these as sample outputs.

## Prompt Files

Create:

    prompts/support_prompt_a.txt
    prompts/support_prompt_b.txt

Prompt A should be a weaker baseline prompt.

Prompt B should be an improved candidate prompt that adds:

- empathy
- clear next action
- policy-safe wording
- no unsupported promises
- concise tone
- escalation when needed
- refusal to invent order details
- explicit handling for unclear customer messages

## App Requirements

Build a Streamlit app in `app.py`.

The app must include:

### Header

Show:

    EvalForge
    Stop shipping prompt changes on vibes.

Subtext:

    Compare prompt and model variants across quality, latency, regressions, and release risk without paid APIs.

### Comparison Mode Selector

Dropdown with exactly:

- Prompt vs Prompt
- Model vs Model
- Custom Variant Comparison

### Prompt vs Prompt Behavior

- User enters or loads Prompt A.
- User enters or loads Prompt B.
- User loads or uploads outputs for Variant A.
- User loads or uploads outputs for Variant B.
- Variant A and B are compared against the same dataset.

### Model vs Model Behavior

- User enters or loads one shared prompt.
- User names Model A.
- User names Model B.
- User loads or uploads outputs for Model A.
- User loads or uploads outputs for Model B.
- Variant A and B are compared against the same dataset.

### Custom Variant Comparison Behavior

- User names Variant A.
- User names Variant B.
- User provides prompt and outputs for each.
- Variant A and B are compared against the same dataset.

### Dataset Loader

Support:

- loading default `data/golden_dataset.jsonl`
- uploading custom JSONL dataset

Validate dataset rows before running eval.

If dataset is invalid, show a clear Streamlit error and do not crash.

### Output Loader

Support:

- loading default sample outputs
- uploading Variant A JSONL outputs
- uploading Variant B JSONL outputs
- manual output entry for small datasets if practical

Validate output rows before running eval.

If outputs are missing for any dataset case, show a clear warning.

## Eval Engine Requirements

Create `eval_engine.py`.

Implement:

    run_eval(dataset, variant_a, variant_b)

For every case:

1. Match the case with Variant A output.
2. Match the case with Variant B output.
3. Score both outputs locally.
4. Track:
   - case id
   - category
   - input
   - expected
   - variant label
   - model name or variant name
   - prompt
   - output text
   - quality score
   - rubric breakdown
   - latency_ms if available
   - judge reasoning
   - scoring method

After all cases, compute:

- average quality A
- average quality B
- wins for B
- regressions/losses for B
- ties
- category-level performance
- recommendation

If latency is not available, display it as unavailable instead of fabricating it.

Do not invent cost metrics. Since no APIs are used, cost should be shown as:

    $0.00 local evaluation cost

or omitted from the leaderboard.

## Scoring Requirements

Create `scorers.py`.

Support three local scoring methods:

### 1. Rubric Scoring

For:

    "scoring_method": "rubric"

Score from 1 to 5 using deterministic heuristic checks.

Evaluate:

- empathy
- helpfulness
- policy safety
- expected behavior coverage
- clarity
- unsupported promise avoidance

Suggested scoring logic:

- Start from 1.
- Add points for matching expected behavior keywords or concepts.
- Add points for empathy markers where appropriate.
- Add points for clear next action.
- Add points for policy-safe phrasing.
- Subtract or withhold points for unsupported promises, vague responses, robotic tone, or missing expected action.
- Cap score between 1 and 5.

Return:

    {
      "score": 1-5,
      "reasoning": "short explanation",
      "breakdown": {
        "expected_coverage": boolean,
        "empathy": boolean,
        "next_action": boolean,
        "policy_safe": boolean,
        "unsupported_promise": boolean
      }
    }

The reasoning must be generated by rule-based logic, not an LLM API.

### 2. Exact Match Scoring

For:

    "scoring_method": "exact_match"

Return:

- 5 if output exactly matches expected
- 1 otherwise

### 3. Contains Keyword Scoring

For:

    "scoring_method": "contains"

Treat `expected` as the keyword or keyword phrase.

Return:

- 5 if expected appears in output
- 3 if partial match appears
- 1 if missing

## Recommendation Logic

Implement:

    generate_recommendation(summary)

Rules:

Recommend `ship` if:

- Variant B average quality is greater than or equal to Variant A
- regressions are 3 or fewer
- no critical category has major regression

Recommend `do_not_ship` if:

- Variant B quality is lower than Variant A
- regressions are greater than 3
- Variant B regresses on high-risk categories like refund, billing, policy, or escalation

Recommend `ship_with_caveat` if:

- quality improves or holds steady
- but regressions require manual review
- or category-level performance is mixed

Display recommendation labels as:

- SHIP
- SHIP WITH CAVEAT
- DO NOT SHIP

## UI Output Requirements

After an eval run, show these sections:

### 1. Leaderboard

Side-by-side table:

    Metric | Variant A | Variant B | Winner

Include:

- average quality
- wins
- regressions
- ties
- evaluated cases
- local evaluation cost

Do not show fake API cost.

### 2. Category Breakdown

Show average quality by category for Variant A and Variant B.

This helps prove the app catches regressions hidden by averages.

### 3. Decision Memo

This is the most important portfolio feature.

Show:

- final recommendation
- explanation
- top 3 risks
- top 3 failed or regressed cases
- suggested next action

### 4. Failed Cases Explorer

Show cases where Variant B scored lower than Variant A.

For each failed case, show:

- case id
- category
- input
- expected behavior
- Variant A output
- Variant B output
- A score
- B score
- scoring reasoning
- rubric breakdown

### 5. Full Results Table

Show all result rows in a dataframe.

### 6. Save Run

Save each run as JSONL in:

    data/runs/

Use timestamped filenames.

## README Requirements

Create a polished, recruiter-readable `README.md`.

Include:

1. Project title
2. Tagline: `Stop shipping prompt changes on vibes.`
3. Problem
4. Solution
5. Why no paid APIs
6. Core features
7. How it works
8. Architecture
9. Screenshots placeholder
10. Demo link placeholder
11. Loom video placeholder
12. How to run locally
13. PM artifact links
14. Roadmap
15. What this project demonstrates

Position the project as:

    An open-source LLM regression testing and release-decision tool for AI PMs and prompt owners.

Do not describe it as merely a prompt playground.

## PM Docs Requirements

Create these files:

### `docs/PRD.md`

Include:

- problem
- target user
- jobs-to-be-done
- goals
- non-goals
- user stories
- success metrics
- v1 scope
- future scope
- why no paid APIs in v1

### `docs/persona.md`

Create personas for:

- AI PM
- founder
- applied AI engineer
- open-source builder

### `docs/metrics_kpi_tree.md`

Include:

- north star metric
- activation metric
- quality metric
- regression metric
- category-level reliability metric
- local evaluation completion metric

Do not include fake cost metrics.

### `docs/risk_register.md`

Include risks:

- heuristic scorer misses semantic nuance
- false confidence from small datasets
- noisy eval datasets
- over-reliance on average scores
- sample outputs being mistaken for live model outputs
- local scoring being less accurate than LLM-as-judge
- future local model integration complexity

### `docs/roadmap.md`

Include:

- v1
- v2
- v3

Future roadmap ideas:

- Ollama support
- LM Studio support
- local LLM-as-judge
- CI check for prompt changes
- eval history dashboard
- judge-human agreement audit
- rubric builder
- dataset generator
- exportable release memo
- prompt diff viewer
- regression severity labels

### `docs/experiment_plan.md`

Explain how to test whether EvalForge improves prompt release confidence.

Include:

- baseline manual review workflow
- EvalForge-assisted review workflow
- time-to-decision comparison
- regression catch comparison
- confidence survey

### `docs/demo_script.md`

Write a 90-second Loom script.

The demo script must emphasize:

- no paid APIs
- default dataset
- Prompt vs Prompt comparison
- Model vs Model comparison through uploaded outputs
- failed cases explorer
- decision memo
- portfolio relevance

## `requirements.txt`

Use:

    streamlit
    pandas

Only add more dependencies if required.

Do not include paid API SDKs.

Do not include:

    openai
    anthropic

## `.gitignore`

Include:

    .env
    .venv/
    __pycache__/
    *.pyc
    data/runs/*.jsonl
    .DS_Store

## Build Order

Follow this order:

1. Read existing project files before editing.
2. Create or repair the required file structure.
3. Create default dataset.
4. Create sample Variant A and Variant B outputs.
5. Create prompt files.
6. Build scoring layer.
7. Build eval engine.
8. Build Streamlit UI.
9. Add save-run support.
10. Add README.
11. Add PM docs.
12. Run a local sanity check if possible.

## Quality Bar

The final app must:

- run with `streamlit run app.py`
- require no paid API keys
- require no `.env` file
- load the default dataset
- load sample outputs
- support Prompt vs Prompt
- support Model vs Model
- support Custom Variant Comparison
- support uploaded JSONL outputs
- score outputs locally
- show leaderboard
- show category breakdown
- show decision memo
- show failed cases explorer
- show full results table
- save run results
- include README
- include PM docs

## Implementation Rules

- Keep v1 simple.
- Prefer readable Python over clever abstractions.
- Do not over-engineer.
- Do not add auth.
- Do not add a database.
- Do not add Docker.
- Do not add LangChain.
- Do not add LlamaIndex.
- Do not add paid API SDKs.
- Do not add RAG features.
- Do not create fake live model responses.
- Clearly label bundled sample outputs as sample outputs.
- Do not silently swallow errors.
- Do not fabricate cost or latency metrics.
- Use clear function names.
- Keep functions small.
- Add comments only for non-obvious logic.
- Do not delete existing work unless replacing it with better work.
- After changes, summarize what changed and what still needs manual input.

## Manual Input Needed From User

Assume the user will manually provide:

- screenshots after running locally
- live demo link after deployment
- Loom link after recording
- optional real model outputs from ChatGPT, Claude, Gemini, Ollama, LM Studio, or another model source

Do not fabricate these.

## Final Response Format

After implementation, respond with:

1. Files created or changed
2. How to run locally
3. What works
4. What still needs manual input
5. Known limitations or risks

## Approach

- Read existing files before writing. Don't re-read unless changed.
- Thorough in reasoning, concise in output.
- Skip files over 100KB unless required.
- No sycophantic openers or closing fluff.
- No emojis or em-dashes.
- Do not guess APIs, versions, flags, commit SHAs, or package names. Verify by reading code or docs before asserting.
