# Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Heuristic scorer misses semantic nuance | High | Medium | Rubric breakdown is shown per case so reviewers can override; v3 roadmap adds local LLM-as-judge with a judge–human agreement audit. |
| 2 | Small dataset gives false confidence | High | Medium | Bundled set is 24 cases across 9 categories; PRD calls out that the golden dataset must grow over time. |
| 3 | Noisy or biased golden dataset | Medium | High | Each case has an explicit `expected` field and a category for traceability; reviewers can edit and reload the dataset. |
| 4 | Over-reliance on average score hides per-case regressions | High | High | The bundled demo is the proof: Variant B improves average quality from 2.21 to 3.88 yet still introduces 3 regressions. Failed-cases explorer lists every B<A case; recommendation engine downgrades to SHIP WITH CAVEAT when any regression exists; category breakdown surfaces averages within each category. Reviewers should always read the failed cases before approving a SHIP WITH CAVEAT. |
| 5 | Sample outputs mistaken for live model outputs | Medium | Medium | UI labels them as "sample outputs only — bundled with the repo, not generated live"; README repeats the same. |
| 6 | Local scorer is less accurate than LLM-as-judge | Medium | Medium | Acknowledged tradeoff. Rubric is intentionally inspectable. v3 adds LLM-as-judge with an agreement audit. |
| 7 | Future local-model integration complexity | Medium | Low | Roadmap stages Ollama and LM Studio support behind v2 to keep v1 dependency-light. |
| 8 | Latency reported as `unavailable` when not provided in JSONL | Low | Low | UI shows `unavailable` rather than zero or a fabricated number. PRD forbids fabricated metrics. |
| 9 | Output JSONL drift between dataset and outputs | Medium | Medium | Validator surfaces missing or extra `case_id` values as a warning before the run. |
| 10 | Reviewer fatigue when the failed-cases list is long | Medium | Medium | Decision memo highlights only the top 3 failed cases by score delta; full list is still browsable. |
| 11 | False sense of release safety from a SHIP recommendation | Medium | High | Recommendation always names risks even when the label is SHIP; reviewers are nudged to spot-check. |
| 12 | Recommendation flips on rounding noise | Low | High | `generate_recommendation` compares raw averages with an explicit epsilon (`RECOMMENDATION_EPSILON = 0.05`); a covering test pins the behaviour. |
| 13 | Bundled-demo headline numbers drift after a regex tweak | Medium | High | `tests/test_demo_baseline.py` asserts the README-claimed numbers; CI fails before the README claim drifts. |
| 14 | Two saves in the same second silently overwrite | Low | Medium | `save_run` now appends a uuid suffix to the filename; covered by a unit test. |
| 15 | Eval engine assumes pre-validated dataset | Low | Medium | `_evaluate_variant` raises explicit `ValueError` for missing `id`/`expected`; covered by tests. |
| 16 | Rubric pattern matches quoted user content | Low | Medium | Documented assumption in the `scorers.py` module docstring: agent text only. |
