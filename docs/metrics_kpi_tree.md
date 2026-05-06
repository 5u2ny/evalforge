# Metrics and KPI tree

> EvalForge does not call any paid API. There is no per-run model cost. Cost is reported as `$0.00 local evaluation cost` everywhere it appears. This file deliberately omits fabricated cost metrics.

## North star

**Percentage of prompt or model changes that are evaluated before shipping.**
For a portfolio project the target is 100% on the bundled dataset; for a real team the same target applies. Every change should produce an EvalForge run before merge.

## Activation

- Time from clone to first completed eval run, target under 5 minutes.
- First successful run uses the bundled dataset and bundled sample outputs.

## Quality

- Average rubric score per variant on the golden dataset (1–5 scale).
- Per-case score with rubric breakdown (empathy, expected coverage, next action, policy safety).

## Regression

- Number of cases where Variant B scored lower than Variant A.
- Severity flag when high-risk categories (refund, billing, policy edge, escalation) regress by more than 0.5 average points.

## Category-level reliability

- Average score by category for both variants.
- Delta column to surface category-level regressions hidden by overall averages.
- High-risk category flagging in the breakdown table and in the recommendation.

## Local evaluation completion

- Did the run complete end to end with a saved JSONL in `data/runs/`?
- Did every dataset case have an output for both variants? Missing outputs are flagged before scoring.

## Cost

Reported as `$0.00 local evaluation cost`. Not modelled because no API is called. Live cost will be added when local-model inference is integrated, and only for the inference step. The eval engine itself remains free to run.
