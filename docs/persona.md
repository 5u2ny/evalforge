# Personas

## AI PM (primary)

**Name.** Devon, AI PM at a 60-person SaaS company.
**Owns.** The system prompt for the customer-support assistant.
**Pain.** Every prompt change ships on vibes. Last quarter, a tone change that helped on complaints regressed on refund requests, and nobody caught it for two weeks.
**Goals.** Confidence before a prompt change ships. A simple paper trail. A way to surface the cases that hurt most.
**Use of EvalForge.** Run an eval on the support golden dataset before merging a prompt change. Read the category breakdown to spot regressions. Use the failed-cases explorer to decide ship vs no-ship.

## Founder

**Name.** Priya, technical founder of a 5-person AI startup.
**Owns.** Model choice and core prompt for the entire product.
**Pain.** No bandwidth for a real eval pipeline, but cannot afford silent regressions. Every model swap is a coin flip.
**Goals.** A 10-minute regression check before any model swap. Visible cost and risk.
**Use of EvalForge.** Run model A vs model B on a 30-case dataset before swapping the model. Read the recommendation and the high-risk category flags.

## Applied AI engineer

**Name.** Marcus, senior engineer iterating on prompts daily.
**Owns.** Prompt versions and model deployments.
**Pain.** Iteration cycle is faster than evaluation. Existing eval tools are heavy.
**Goals.** A regression harness that runs in under a minute. JSONL in, decision out.
**Use of EvalForge.** Drop a JSONL of outputs into the app, run the eval, see the diff, decide whether to push.

## Open-source builder

**Name.** Sam, indie developer evaluating local models.
**Owns.** A small AI side project running on a Mac with Ollama.
**Pain.** Existing eval tools assume cloud APIs and paid keys. Cannot share a Loom of an eval run that requires a paid key on screen.
**Goals.** Tooling that runs on a laptop, no signup, fully forkable.
**Use of EvalForge.** Use the bundled dataset, paste outputs from local llama-3 vs local mistral, see which one wins on the support benchmark.
