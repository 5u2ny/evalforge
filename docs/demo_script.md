# 90-second Loom script

Headline narrative: **Variant B improves average quality, but EvalForge catches 3 regressions that would be missed by vibe-checking outputs.**

## Beat 1 — hook (0:00–0:10)

"Most AI teams ship prompt changes on vibes. EvalForge is a release gate that runs on your laptop. No paid APIs, no API keys."

## Beat 2 — problem (0:10–0:25)

Show a fake "playground review" — copy two outputs from Variant B that look great. Voiceover: "If I eyeball two outputs and they look better, I ship. That is how regressions sneak through."

## Beat 3 — load the eval (0:25–0:40)

Open EvalForge in the browser. Pick **Prompt vs Prompt**. Show the bundled dataset checkbox preselected. Show the bundled sample outputs preselected. Voiceover: "24 customer-support cases across 9 categories. Sample outputs ship with the repo and are clearly labelled. No keys, no auth."

## Beat 4 — run and read the leaderboard (0:40–1:00)

Click **Run eval**. Show the leaderboard. Voiceover: "Variant B improves average quality from 2.21 to 3.88. 20 wins. Looks like a clean ship."
Pause on the regressions row. Voiceover: "But there are 3 regressions. That is what EvalForge exists to catch."

## Beat 5 — the 3 regressions (1:00–1:20)

Open the failed-cases explorer. Walk through each:

1. **case_013 (billing_issue).** Variant A says "I will refund you both charges immediately." Variant B over-escalates to a "specialized billing team" with no concrete next action. Voiceover: "B fixed the over-promising in A but lost the actual help."
2. **case_004 (policy_edge, 90-day return).** A is too generous, B is too vague. Voiceover: "B avoids over-promising but never explains the 30 day window."
3. **case_018 (damaged_item, shirt with hole).** B slips into 'guaranteed replacement' and skips asking for the order number. Voiceover: "Over-eager prompt — sounds great, breaks the rule."

Show the rubric breakdown panel. Voiceover: "The judge reasoning is rule-based and inspectable, not a black-box LLM."

## Beat 6 — decision memo (1:20–1:25)

Show the decision memo. Voiceover: "Recommendation flips from SHIP to SHIP WITH CAVEAT. Top risks listed. Next action recommended. Reviewer can decide whether the 3 regressions are acceptable."

## Beat 7 — close (1:25–1:30)

"EvalForge. Open source, no paid APIs, repo in the description."

## Notes for the recording

- Highlight the "sample outputs" label so viewers know the bundled outputs are not live model calls.
- Emphasise "no API keys" twice.
- Keep the demo dataset visible the whole time.
- Mention that uploaded JSONL outputs from any model — Ollama, LM Studio, ChatGPT copy-paste, Claude.ai, Gemini — work the same way.
- Do not skip the 3 regressions. They are the demo. Without them this looks like a wrapper.
