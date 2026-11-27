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
2. Pick the single task-table row that best matches the job. Use only models and effort levels named in the guide.
3. Apply the tie-breaks: judgment-heavy or large-scope work goes to the bigger model; cheap-to-verify, high-volume work goes to the smaller model. A clear spec alone does not mean Sonnet: migrations and performance work can need Opus 5.5 or Fable 5.2.
4. If the job fits no row clearly, answer Opus 5.5 at medium (the "You aren't sure yet" row), because a more exotic guess costs more when wrong.
5. Reply in exactly this format, nothing else:
   `Model:` / `Effort:` / `Matched row:` / `Reason:` (one line, tied to the row) / `If it falls short:` (state the guide's escalation order for this job: verify your own work, raise effort one level, then move to the next model up at lower effort; not generic advice).
