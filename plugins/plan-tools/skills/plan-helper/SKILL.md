---
name: plan-helper
description: Write and self-audit implementation plans so they ask or openly list every decision the user has not made (per the question level the user picks), never include unrequested changes, keep every change as small as it can be while still complete, and prove they cover everything asked. Use whenever you are writing, drafting, revising, or presenting an implementation plan — in plan mode, before ExitPlanMode, inside split-plan step 1b, or when the user says "plan this", "make a plan", "how would you implement" — even if the user doesn't mention plan-helper.
argument-hint: "[everything|balanced|material]"
---

The user has been burned by plans that looked fine and still produced the wrong result. Four failure modes, each with a rule below:

1. Claude filled gaps with its own decisions, and they weren't the user's.
2. The PR contained changes the user couldn't connect to anything they asked for.
3. The change was bigger than needed.
4. After all the testing and review, the result still missed parts of the request, looked bad, or was awkward to use.

Follow the workflow in order. The plan is not ready to present until the self-audit passes.

## Workflow

### 0. Pick the question level

The level decides which open decisions (step 3) go to the user and which you decide yourself and list in the plan. On a simple plan, asking every decision means many rounds where the user picks the recommended answer almost every time; the level lets them trade some of those questions for a list they review with the plan.

Take the level from the argument (`everything`, `balanced` or `material`), from the calling skill, or from the `Question level:` line of the plan you are revising, if any of them gives one. Otherwise ask it as the very first question, in one AskUserQuestion with these three options, each saying in plain English what it asks and what it decides for the user:

- **Everything**: every open decision is asked. Nothing is decided for the user.
- **Balanced**: anything the user will see or experience, and anything costly to undo, is asked. Internal details are decided and listed in the plan.
- **Material only**: only choices that change the direction of the work or cannot be cheaply undone are asked. Everything else, small UX details included, is decided and listed in the plan.

A subagent that is given no level uses `everything`, which is how plan-helper worked before levels existed.

### 1. Capture the asks

Split the user's request into atomic asks, quoting their words verbatim (A1, A2, …). Don't paraphrase — paraphrase is where meaning drifts. If an ask is vague ("make it nicer"), that vagueness is itself a decision to ask about in step 3.

### 2. Read the code

Read everything the asks touch: callers, tests, fixtures, config, existing helpers and patterns. You need this before you can tell which decisions are already made by the code and which are open, and before you can find the smallest change.

### 3. Ask the open decisions your level calls for

A decision is open when neither the user's request nor the existing code dictates the answer. That covers UX (layout, copy, placement, interactions), behavior, edge cases, naming, data shape, libraries, file structure, error handling, migration — anything. The bar is deliberately low: when unsure whether something is a decision, it is. A question costs the user seconds; a wrong guess costs them a rework cycle and the trust that the plan reflects them.

The level from step 0 decides which open decisions you ask and which you decide yourself:

| Level | Ask the user | You decide and list |
|---|---|---|
| Everything | Every decision neither the request nor the code dictates | Nothing |
| Balanced | Anything the user will see or experience (layout, wording, placement, interactions, behavior, user-facing edge cases); anything costly to undo (data shape, migration, new dependency, public API, security, size of the change) | Internal details: naming, file structure, internal error handling, test layout |
| Material only | Only choices that send the implementation in a different direction or cannot be cheaply reversed: architecture, data model and migration, scope, public API, security, billing | Everything else, including small UX details |

When you decide, take the answer the existing code's patterns point to; if they point to none, take the option you would have recommended. Record each one under **Assumed decisions** in the plan (step 4). A lower level saves the user questions, not visibility: they still see and can veto every choice made for them.

Two things are asked at every level: a vague ask ("make it nicer"), and whether to include something that serves no ask. They guard against other failure modes (missing what was asked, and unrequested changes), not the one a level relaxes.

- Use AskUserQuestion, batched up to 4 questions per round, as many rounds as needed.
- Write questions, options, and descriptions in full, plain English, never caveman or other compressed styles, even when one is active for the session. The user decides from this text alone, and clipped fragments hide what is being decided. If the `humanizer` plugin is available, invoke `/humanizer:humanizer` on the drafted question text before sending it; otherwise just write the questions in plain English.
- Each question stands on its own (the user may only see the dialog): name the thing, say what you found if it matters.
- Give 2–4 concrete options. Put your recommendation first, marked "(Recommended)", with a one-line reason.
- **Size trade-offs:** where a piece has a real smaller-vs-larger choice (e.g. reuse the existing component vs. a new one; patch one screen vs. all of them), present it as a question with both options and what each covers.
- Do not proceed with a placeholder answer and "we can change it later". Get the answer.

New decisions surfacing later (while writing the plan, during the audit) follow the same level: those it calls for go back to the user the same way, the rest you decide and add to Assumed decisions.

### 4. Write the plan

The plan must contain these sections:

**Question level** — a `Question level:` line naming the level from step 0. Implementers apply the same bar to decisions that come up while they work.

**Requirement map** — one row per ask:

| Ask (verbatim) | Delivered by (step) | Verified by | Status |
|---|---|---|---|

Status starts as `[ ]`; implementers tick it to `[x]` once the ask is delivered and verified.

**Decisions** — every answer from step 3, as `question → user's answer`. Implementers follow these; they never re-decide them.

**Assumed decisions** — every decision you made yourself because it fell below the level's bar, as `decision → choice — one-line reason`. Empty at Everything. The user reviews this list with the plan, and it is copied into the PR body, so no choice made for them stays hidden.

**Steps** — for each step:
- Files and what changes in each.
- `Serves: A<n>` — which ask(s) this step exists for.
- `Why this size:` — why no smaller change works. First check whether existing code, helpers, or patterns already do it; reuse beats new code, and a one-line change beats a new abstraction. "It's cleaner" or "while we're here" are not reasons.

**Verification** — tests, plus running the real app or command and exercising each ask end to end the way the user will use it (click through the UI, run the CLI, open the page at the relevant viewport). Tests passing is not proof that it looks right or is pleasant to use; seeing it is. Name exactly what to run and what to check for each ask.

**Implementation rules** — copy this block verbatim into the plan, so it binds whoever implements it (including split-plan sessions):

```markdown
## Implementation rules

- Change only what a step in this plan lists. Every changed line must trace to an ask in the requirement map. No drive-by refactors, renames, reformatting, dependency bumps, or "while I'm here" fixes — note them in the final report instead.
- Follow the Decisions section exactly. If you hit a decision this plan doesn't answer, use the plan's question level. If the level would not ask it, pick the answer the existing code points to (else the one you would recommend) and add it to the plan's Assumed decisions (in a split plan, in `.planning/SPEC.md`). If the level would ask it, stop and ask the user (AskUserQuestion) — don't pick one yourself. If you are a subagent and can't ask the user directly, end your run with the question as your final report (plain English, 2–4 options, your recommendation first); the parent will ask the user and send you the answer so you can continue.
- When you raise the PR, copy the plan's Assumed decisions into the PR body under an "Assumed decisions" heading, so reviewers see every choice the user did not make.
- Tick each requirement map row's Status once it is delivered and verified. In a split plan, tick your session's rows in `.planning/SPEC.md`.
- Keep each change as small as it can be while still complete. Reuse existing code and patterns before writing new ones.
- Done means every requirement map row assigned to your work (the whole plan, or your session's rows) is delivered and verified — including running the real app/command per the Verification section, not only tests.
```

### 5. Self-audit before presenting

Re-read the plan against each rule and fix what fails:

- **Coverage:** every ask has a row, a delivering step, and a real-use verification. No ask silently dropped or narrowed.
- **No unrequested changes:** every step and every file has a `Serves:` pointing to a real ask. Cut anything that doesn't. If something seems necessary but serves no ask (e.g. a bug you found), ask the user whether to include it instead of including it.
- **Size:** for each step, could less code, fewer files, or reuse of something existing achieve the same ask? If yes, shrink it, or ask the user if it's a real trade-off.
- **No unlisted decisions:** every choice in the plan is in Decisions, dictated by the code, or listed in Assumed decisions and below the level's bar. Any other choice, including an assumed one the level would have asked, becomes a question.
- **Rules block** is present verbatim.

Then present the plan (ExitPlanMode if in plan mode, unless a calling skill such as split-plan says to present later).
