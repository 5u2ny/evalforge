# Roadmap

## V1 (now)

- Three comparison modes on a single shared engine.
- Local rubric scorer plus exact-match and contains-keyword scorers.
- Bundled golden dataset (24 cases, 9 categories) and bundled weak/strong sample outputs.
- Leaderboard, category breakdown, decision memo, failed-cases explorer, full results table.
- Save run to JSONL in `data/runs/`.
- README and PM docs.

## V2

- Optional local-model integration: Ollama, LM Studio, llama.cpp adapters that produce JSONL outputs the app already understands.
- Rubric editor in the UI so reviewers can tune empathy, next-action, and policy-safety weights.
- Eval history dashboard listing previous runs in `data/runs/`.
- Dataset generator: seed cases by category from a small input set.

## V3

- Local LLM-as-judge mode with judge-vs-human agreement audit.
- CI integration that blocks merges if a prompt diff has no associated eval run.
- Prompt diff viewer with linked-eval context.
- Exportable release memo (Markdown plus PDF).
- Regression severity labels (P0–P2) per failed case.

## Stretch

- Multi-judge ensemble for local LLM-as-judge.
- Online eval mode that samples production traffic.
- Open shared benchmark page anyone can submit a model to.
- Plugins for new domains beyond customer support (search, RAG answers, code completions).
