# EvalForge PRD

## Problem

AI teams ship prompt and model changes weekly. Most changes are not evaluated against a fixed dataset before they ship. LLM outputs are non-deterministic, so eyeballing a few cases is not a release gate. Quality regresses silently and category-level reliability drifts. The current workflow is "paste in a playground, read a few outputs, ship on vibes."

## Target user

- AI PMs who own a prompt or model in production
- Founders shipping AI features fast with little eval infrastructure
- Applied AI engineers iterating on prompts daily
- Open-source builders evaluating local models

## Jobs to be done

> Before I ship a prompt or model change, help me decide if it is actually better — across quality, behavior, regressions, and reliability — using a fixed set of test cases I trust.

## Goals

- Make eval the default before any prompt or model change.
- Surface regressions hidden by average scores.
- Produce a clear release recommendation: SHIP, SHIP WITH CAVEAT, DO NOT SHIP.
- Be runnable on any laptop with Python — no paid APIs, no API keys, no auth, no database.

## Non-goals

- Live model inference inside the app for v1.
- Hosted SaaS or multi-tenant deployment.
- LLM-as-judge in v1 (deterministic and rubric scoring only).
- Auth, billing, vector DB, RAG, agent orchestration.

## User stories

- As an **AI PM**, I can compare two prompts on the same dataset and see whether B is better than A overall and by category.
- As a **founder**, I can compare two model outputs (e.g., local llama vs hosted) on the same prompt and dataset.
- As an **engineer**, I can run a quick custom A/B variant comparison with arbitrary names and prompts.
- As an **open-source contributor**, I can clone the repo and run a meaningful eval in under five minutes with no signups.
- As a **release owner**, I can see the failed cases for B and the rubric reasoning so I can decide whether to ship.

## Success metrics

- Activation: first eval run completed under five minutes from clone.
- Quality: rubric scorer catches at least 80% of obvious regressions in the bundled sample set.
- Decision clarity: every run ends with a single, justified recommendation.
- Category coverage: failed-cases explorer surfaces every case where B underperforms A.

## V1 scope

- Bundled golden dataset of 24 cases across 9 categories.
- Bundled weak (A) and improved (B) sample outputs, clearly labelled.
- Three comparison modes on a single shared engine: Prompt vs Prompt, Model vs Model, Custom Variant Comparison.
- Local scoring methods: `rubric`, `exact_match`, `contains`.
- Leaderboard, category breakdown, decision memo, failed-cases explorer, full results table.
- Runs saved to `data/runs/` as JSONL.
- README and PM docs.

## Future scope

- Local model inference (Ollama, LM Studio, llama.cpp) so EvalForge can generate outputs in addition to evaluating them.
- Local LLM-as-judge with judge-vs-human agreement audit.
- CI check that blocks merges if a prompt diff has no associated eval run.
- Eval history dashboard, prompt diff viewer, exportable release memo.

## Why no paid APIs in v1

Removing paid APIs makes the project clonable and runnable anywhere with no signups, no billing, no API keys leaking in screenshots, and no environment setup beyond `pip install`. It also forces the design to be honest about what the local scorer can and cannot do — the rubric is deterministic and inspectable, which is itself a portfolio talking point. Future versions can add local model inference and local LLM-as-judge; both can also avoid paid APIs.
