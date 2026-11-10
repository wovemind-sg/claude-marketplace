---
name: split-plan
description: Produce isolated, context-sized session files for a large feature — either by splitting an implementation plan the user already has, or by writing the plan from scratch first and then splitting it. Use when the user has an implementation plan and wants it split into sessions, when they describe a feature big enough to need multiple Claude Code sessions but have no plan yet, or when they ask to prepare work for Claude Code's context limits.
---

You are producing context-sized session files for a large feature. The implementing model is Sonnet. This is planning only — NEVER implement anything from the plan in this session.

Two entry points, same output:
- **Plan exists** — the user points you at a plan document; you restructure it.
- **No plan** — the user describes the feature; you write the plan first (step 1b), then split it.

## Plan mode

This skill usually runs in plan mode, where file writes are blocked. If you are in plan mode: complete steps 1–3 below, present the session breakdown as your plan, call ExitPlanMode, and write files only after the user approves. NEVER attempt to write files while plan mode is active.

## Steps

1. **Locate and read the plan.** If you don't know where it is, ask the user — do not guess. If no plan exists, go to 1b.

1b. **No plan? Write one first.** Interview the user for scope, constraints, stack, and what "done" looks like, read the relevant existing code, then draft the full implementation plan yourself, following `/plan-tools:plan-helper`. Get the user's agreement on it before splitting — splitting a plan they haven't signed off on just multiplies a wrong design across many session files. The drafted plan becomes `.planning/SPEC.md` in step 4. In plan mode, don't call ExitPlanMode for the plan alone: present it together with the session breakdown in the single ExitPlanMode call described above.

2. **Decide whether splitting is needed at all.** Estimate the plan's total implementation effort: files touched, code volume, reading required. One session comfortably holds ~120k tokens of work. If the entire plan fits in one session, STOP here: tell the user the plan is small enough to implement in a single session, and end. Splitting a small plan adds session files, handoffs, and progress tracking with zero benefit.

3. **Design the sessions.** Each session MUST:
   - Have exactly one goal (a single feature, module, or vertical slice)
   - Fit in one context window (~120k tokens of work)
   - End in a fully working, committable state — no half-implemented features crossing session boundaries
   - Declare explicit inputs (what files/context it needs) and outputs (what it produces)

4. **Write the files.** Default location is `.planning/` at the project root — use a different location only if the user names one.

   | File | Content |
   |---|---|
   | `.planning/SPEC.md` | The full plan, preserved as reference — the user's original if they had one, otherwise the one you drafted in 1b |
   | `.planning/progress.md` | Session 1 as "active", all others "not_started" |
   | `.planning/CLAUDE.md` | Project conventions, stack, folder structure, key decisions the sessions need. Keep under 60 lines. Plan-scoped: NEVER modify the project's root CLAUDE.md, and do not duplicate what it already covers |
   | `.planning/sessions/session-01.md`, `session-02.md`, … | One per session: Goal, Prerequisites, Exact tasks (numbered, specific), Files to create/modify, How to verify it's done, if the plan came from plan-helper: its `## Implementation rules` block copied verbatim, plus the Decisions that apply to this session and the requirement-map rows it delivers (session subagents get only this file, not the full plan), **update project root CLAUDE.md with what changed** (conventions, stack, structure introduced/changed this session — if none exists yet, session 1 creates one from scratch since it's a new project), Handoff instructions (what to write to progress.md when complete) |

5. **Show the result.** List the sessions with one-line summaries so the user can review and adjust before anything starts.
