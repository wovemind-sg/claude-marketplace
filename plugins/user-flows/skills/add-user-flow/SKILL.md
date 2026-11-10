---
name: add-user-flow
description: Add one specific new user flow to user-flows.md from a free-text description of what the client wants added — e.g. "let users export their order history as CSV". First checks whether an equivalent flow already exists (reports its ID and stops if so, making no changes); otherwise grounds the flow in the actual code, appends it, and syncs the Playwright user-flow tests via test-user-flow. Use whenever the user describes a single new flow, journey, or scenario to add to the inventory — as opposed to update-user-flows (re-derives many flows from the whole session's code changes) or extract-user-flows (regenerates/extracts from the codebase at large). Creates user-flows.md if it doesn't exist yet.
argument-hint: "<free-text description of the new user flow>"
---

Add one new user flow to `user-flows.md` at the project root, described by `$ARGUMENTS`. This is a single, targeted addition — not a re-derivation from the whole codebase or session, so scope your work to just the one flow described.

Before doing anything else, read the sibling skill at `${CLAUDE_PLUGIN_ROOT}/skills/extract-user-flows/SKILL.md` — it defines what a user flow is, the entry format, and the dedup rule. Every flow you write must match that format so the file stays consistent.

## Get or create the file

If `user-flows.md` doesn't exist, create it with the standard header (`granularity: medium | area: all | generated: <today>`) and no flows yet — don't run a full extraction first.

## Check for an existing equivalent flow

Read `user-flows.md` and compare `$ARGUMENTS` against every existing flow using the same dedup rule extraction uses: same steps and outcome, differing only in data values, counts as the same flow. Judge by what the flow actually does, not by wording — "let users cancel a pending order" and "allow buyers to back out of an order before it ships" describe the same flow even with no words in common.

If an equivalent flow already exists, **stop here** — report its ID, name, and why it matches, and make no changes to the file.

## Ground and add the flow

If no equivalent exists, trace the described behavior through the actual code (entry point, the interactive elements involved, what they actually do) so the flow is evidence-based, not invented from the description alone. If the description doesn't match anything in the code, say so and stop rather than writing a flow for a feature that doesn't exist.

Write the new entry in the exact format extraction uses (Actor/Precondition/Steps/Expected/Source):

- Assign the next ID after the highest existing one in the whole file; never reuse an ID.
- Place it under the matching `##` area heading, creating the heading if the area is new.
- Leave every other flow byte-for-byte identical — no reformatting, reordering, or rewording.
- Update the header's `generated:` date; keep granularity and area as they were (or as set above, for a newly created file).

## Sync the tests

If the project already has user-flow tests (a directory with `# user-flow:` marker comments — search for one before assuming none exists), invoke the sibling skill `user-flows:test-user-flow` (via the Skill tool) after writing the file, so a test gets generated for the new flow. Skip this if no such tests exist yet; mention that `/user-flows:test-user-flow` can set them up.

## Finish

Report either: the existing flow's ID/name that blocked the add (no changes made), or the new flow's ID/name/area plus the test-sync outcome. Do not paste the whole file back into the conversation.
