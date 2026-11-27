---
name: pick-model
description: Recommend which Claude model (Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.2) and effort level to use for a job, from Anthropic's model guide. Use when the user describes a task, agent, subagent or workload and asks which model or effort to pick, or whether to move up or down a model.
argument-hint: <job description>
---

# pick-model

Recommend a model and effort for the job in `$ARGUMENTS`. Recommend only: do not run the job.

If `$ARGUMENTS` is empty, ask the user for the job description and stop.

## Steps

1. Read `${CLAUDE_SKILL_DIR}/references/guide.md` (the decision rules from Anthropic's guide).
2. Spawn one subagent with the Agent tool, `model: "haiku"`. Its prompt is, in order: the full text of guide.md; the job verbatim; and these instructions:
   - Pick the single task-table row that best matches the job. Use only models and effort levels named in the guide.
   - Apply the tie-breaks: judgment-heavy or large-scope work goes to the bigger model; cheap-to-verify, high-volume work goes to the smaller model. A clear spec alone does not mean Sonnet: migrations and performance work can need Opus 5.5 or Fable 5.2.
   - If the job fits no row clearly, answer Opus 5.5 at medium (the "You aren't sure yet" row). Do not guess a more exotic choice.
   - Reply in exactly this format, nothing else:
     `Model:` / `Effort:` / `Matched row:` / `Reason:` (one line, tied to the row) / `If it falls short:` (the guide's escalation order, applied to this job).
3. Check the reply names a model and an effort that appear in guide.md. If not, re-ask the subagent once. If it fails again, use Opus 5.5 at medium and say the fallback was used.
4. Show the reply to the user as is.
