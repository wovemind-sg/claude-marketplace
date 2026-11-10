---
name: update-user-flows
description: Update the existing user-flows.md to reflect the code changes made in the current session — add flows for new features, revise flows whose behavior changed, remove flows for deleted features, then sync the Playwright user-flow tests via test-user-flow when anything changed. Use whenever the user asks to update, refresh, or sync the user flows after implementing, changing, or removing functionality. Requires a user-flows.md produced by extract-user-flows; do not use for generating flows from scratch.
---

Update `user-flows.md` at the project root so it stays accurate after the changes made in this session. The file feeds automated test generation, so stale flows mean wrong tests — but a full regeneration would churn IDs that existing tests reference. Update surgically instead.

If `user-flows.md` does not exist, stop and tell the user to run `/user-flows:extract-user-flows` first.

Before adding or revising any flow, read the sibling skill at `${CLAUDE_PLUGIN_ROOT}/skills/extract-user-flows/SKILL.md` — it defines what a user flow is, the granularity levels, the deduplication rules, and the exact entry format. Every flow you write must follow those definitions so the file stays consistent with what extraction would have produced.

## Determine what changed this session

Combine two sources:

1. **The conversation** — you already know what you built, changed, or removed this session; that intent tells you which behaviors changed, not just which lines.
2. **Git** — `git diff` (unstaged + staged) plus any commits made during this session, to catch everything concretely: `git diff <state-at-session-start>` when identifiable, otherwise the uncommitted diff and recent commits you authored. List the changed files.

If nothing relevant changed (docs-only, refactors with identical behavior), say so and leave the file untouched — a rewrite with no behavioral change just creates diff noise.

## Map changes to flows

Read `user-flows.md`. Each flow's **Source** line links it to code — use it in both directions:

- **Changed file appears in a flow's Source** → re-read that code path and check whether the flow's steps, precondition, or expected outcome still match reality. Also check whether the change introduces new paths through the existing feature (a new validation branch, a new option, a new error or permission case) — each is a new flow if it warrants one at the file's granularity.
- **Changed file appears in no flow** → it may be a new feature: trace its entry points and enumerate the flows it introduces, at the same granularity recorded in the file's header line.
- **Feature removed** → its flows must go.

Ground every judgment in the code as it is now, not in what the diff appears to imply.

## Apply the updates

- **Revised flow:** keep its ID; update only the fields that changed (steps, precondition, expected, source).
- **New flow:** assign the next ID after the highest existing one, place it under the matching area heading (create the heading if the area is new). Never reuse a removed flow's ID.
- **Removed flow:** delete its entry. Do not renumber anything else.
- Untouched flows stay byte-for-byte identical — no reformatting, reordering, or rewording, so the file's diff shows exactly what changed behaviorally.
- Run the same dedup check as extraction: a new flow that duplicates an existing one (same steps and outcome, only data values differ) must be merged into the existing entry instead of added.
- Update the `generated:` date in the header line; keep granularity and area as they were.

## Sync the tests

If any flow was added, revised, or removed, invoke the sibling skill `user-flows:test-user-flow` (via the Skill tool) after writing the file — it diffs flow hashes against test markers, so it acts only on the flows this update touched and leaves the rest of the suite alone. Skip it only when the file was left untouched, or when the project has no user-flow tests yet and the user hasn't asked for them (mention that `/user-flows:test-user-flow` can generate them).

## Finish

Report a change summary: flows added (IDs + names), flows revised (IDs + what changed), flows removed (IDs + names). Explicitly list the removed IDs — downstream tests referencing them need to be deleted or updated. Include the test-sync outcome if it ran. Do not paste the whole file back into the conversation.
