# Experiment plan

## Question

Does using EvalForge before shipping a prompt change reduce silent regressions and shorten time-to-decision compared to a manual playground review?

## Population

- AI PMs and engineers who own a prompt in production.
- Sample size for a portfolio demo: 5 reviewers running both workflows on the bundled dataset.

## Conditions

- **Baseline.** Reviewer reads 8 random outputs in a playground, then decides ship or no-ship from intuition.
- **EvalForge.** Reviewer runs the full golden dataset through EvalForge, reads the leaderboard, category breakdown, and failed cases, then decides.

## Primary metric

- **Regression catch rate.** Percentage of seeded regressions the reviewer correctly flags before shipping.

## Secondary metrics

- **Time to decision.** Minutes from start of review to ship/no-ship call.
- **Confidence score.** Self-reported 1–5 confidence in the decision.
- **Decision agreement.** Percentage of reviewers reaching the same conclusion as the EvalForge recommendation.

## Test design

1. Inject 3 known regressions into Variant B by editing `data/sample_outputs_b.jsonl` (e.g., a refund case where B promises a discount, a delivery case where B invents tracking details, an escalation case where B fails to escalate).
2. Half of reviewers do the baseline workflow first, half do the EvalForge workflow first.
3. Record metrics for each condition.
4. Compare regression catch rate across conditions.

## Hypothesis

EvalForge raises regression catch rate by at least 30 percentage points and reduces time-to-decision by at least 50 percent versus the manual playground baseline.

## Validity threats

- Reviewers may already be familiar with the bundled dataset.
- Heuristic scorer may not match a real LLM-as-judge.
- Single-domain (customer support) does not generalize to all AI features.
- Small sample size limits statistical power; treat as directional rather than conclusive.

## Read-out

- Report regression catch rate, time-to-decision, and confidence per condition in a one-page summary.
- Include the seeded regressions list so the result is auditable.
- Note any reviewer who disagreed with the EvalForge recommendation and why.
