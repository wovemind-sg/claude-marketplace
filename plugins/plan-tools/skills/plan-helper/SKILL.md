---
name: plan-helper
description: Write and self-audit implementation plans so they never guess at the user's decisions, never include unrequested changes, keep every change as small as it can be while still complete, and prove they cover everything asked. Use whenever you are writing, drafting, revising, or presenting an implementation plan — in plan mode, before ExitPlanMode, inside split-plan step 1b, or when the user says "plan this", "make a plan", "how would you implement" — even if the user doesn't mention plan-helper.
---

The user has been burned by plans that looked fine and still produced the wrong result. Four failure modes, each with a rule below:

1. Claude filled gaps with its own decisions, and they weren't the user's.
2. The PR contained changes the user couldn't connect to anything they asked for.
3. The change was bigger than needed.
4. After all the testing and review, the result still missed parts of the request, looked bad, or was awkward to use.

Follow the workflow in order. The plan is not ready to present until the self-audit passes.

## Workflow

### 1. Capture the asks

Split the user's request into atomic asks, quoting their words verbatim (A1, A2, …). Don't paraphrase — paraphrase is where meaning drifts. If an ask is vague ("make it nicer"), that vagueness is itself a decision to ask about in step 3.

### 2. Read the code

Read everything the asks touch: callers, tests, fixtures, config, existing helpers and patterns. You need this before you can tell which decisions are already made by the code and which are open, and before you can find the smallest change.

### 3. Ask every open decision

A decision is open when neither the user's request nor the existing code dictates the answer. That covers UX (layout, copy, placement, interactions), behavior, edge cases, naming, data shape, libraries, file structure, error handling, migration — anything. The bar is deliberately low: when unsure whether something is a decision, it is. A question costs the user seconds; a wrong guess costs them a rework cycle and the trust that the plan reflects them.

- Use AskUserQuestion, batched up to 4 questions per round, as many rounds as needed.
- Write questions, options, and descriptions in full, plain English, never caveman or other compressed styles, even when one is active for the session. The user decides from this text alone, and clipped fragments hide what is being decided. If the `humanizer` plugin is available, invoke `/humanizer:humanizer` on the drafted question text before sending it; otherwise just write the questions in plain English.
- Each question stands on its own (the user may only see the dialog): name the thing, say what you found if it matters.
- Give 2–4 concrete options. Put your recommendation first, marked "(Recommended)", with a one-line reason.
- **Size trade-offs:** where a piece has a real smaller-vs-larger choice (e.g. reuse the existing component vs. a new one; patch one screen vs. all of them), present it as a question with both options and what each covers.
- Do not proceed with a placeholder answer and "we can change it later". Get the answer.

New decisions surfacing later (while writing the plan, during the audit) go back to the user the same way.

### 4. Write the plan

The plan must contain these sections:

**Requirement map** — one row per ask:

| Ask (verbatim) | Delivered by (step) | Verified by | Status |
|---|---|---|---|

Status starts as `[ ]`; implementers tick it to `[x]` once the ask is delivered and verified.

**Decisions** — every answer from step 3, as `question → user's answer`. Implementers follow these; they never re-decide them.

**Steps** — for each step:
- Files and what changes in each.
- `Serves: A<n>` — which ask(s) this step exists for.
- `Why this size:` — why no smaller change works. First check whether existing code, helpers, or patterns already do it; reuse beats new code, and a one-line change beats a new abstraction. "It's cleaner" or "while we're here" are not reasons.

**Verification** — tests, plus running the real app or command and exercising each ask end to end the way the user will use it (click through the UI, run the CLI, open the page at the relevant viewport). Tests passing is not proof that it looks right or is pleasant to use; seeing it is. Name exactly what to run and what to check for each ask.

**Implementation rules** — copy this block verbatim into the plan, so it binds whoever implements it (including split-plan sessions):

```markdown
## Implementation rules

- Change only what a step in this plan lists. Every changed line must trace to an ask in the requirement map. No drive-by refactors, renames, reformatting, dependency bumps, or "while I'm here" fixes — note them in the final report instead.
- Follow the Decisions section exactly. If you hit a decision this plan doesn't answer, stop and ask the user (AskUserQuestion) — don't pick one yourself. If you are a subagent and can't ask the user directly, end your run with the question as your final report (plain English, 2–4 options, your recommendation first); the parent will ask the user and send you the answer so you can continue.
- Tick each requirement map row's Status once it is delivered and verified. In a split plan, tick your session's rows in `.planning/SPEC.md`.
- Keep each change as small as it can be while still complete. Reuse existing code and patterns before writing new ones.
- Done means every requirement map row assigned to your work (the whole plan, or your session's rows) is delivered and verified — including running the real app/command per the Verification section, not only tests.
```

### 5. Self-audit before presenting

Re-read the plan against each rule and fix what fails:

- **Coverage:** every ask has a row, a delivering step, and a real-use verification. No ask silently dropped or narrowed.
- **No unrequested changes:** every step and every file has a `Serves:` pointing to a real ask. Cut anything that doesn't. If something seems necessary but serves no ask (e.g. a bug you found), ask the user whether to include it instead of including it.
- **Size:** for each step, could less code, fewer files, or reuse of something existing achieve the same ask? If yes, shrink it, or ask the user if it's a real trade-off.
- **No assumed decisions:** scan the plan for any choice not in the Decisions section and not dictated by the code. Each one becomes a question.
- **Rules block** is present verbatim.

Then present the plan (ExitPlanMode if in plan mode, unless a calling skill such as split-plan says to present later).
