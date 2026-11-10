---
name: extract-user-flows
description: Extract every user flow (an end-to-end interaction a client can have with the app, e.g. login → search → add to cart → checkout) from the current application codebase and write a deduplicated inventory to user-flows.md. Use whenever the user asks to extract, list, map, inventory, or generate user flows, user journeys, usage scenarios, or interaction paths — especially as a precursor to writing automated/E2E tests. Accepts an optional granularity (low|medium|high) and an optional free-text area filter (e.g. "login").
argument-hint: "[low|medium|high] [optional area description, e.g. 'login']"
---

Extract the user flows of the application in the current working directory and write them to `user-flows.md` at the project root.

A **user flow** is one complete, goal-directed interaction a client can have with the app, from entry point to observable outcome. Example: `open /login → enter email+password → submit → land on dashboard`. Flows are the unit a later model will turn into automated tests, so each flow must be independently testable: concrete steps, a clear precondition, and a verifiable outcome.

## Parse the arguments

`$ARGUMENTS` may contain, in any order:

- **Granularity** — the word `low`, `medium`, or `high`. Default: **high**.
- **Area filter** — any remaining free text describes the area of the app to cover (e.g. "login", "checkout and payments", "the admin panel"). If present, extract flows only for features matching that description. If absent, cover the whole app.

## Explore the app

Ground every flow in evidence from the code — never invent features that don't exist. Map the app before writing anything.

If the repository has a graphify knowledge graph (a `graphify-out/` directory) and the `/graphify` skill is available, query it first — it already holds the codebase's structure and relationships, which is faster and more reliable than re-exploring from scratch. Fall back to raw exploration only for gaps the graph doesn't cover.

1. Find the entry points: routes/URL maps, page components or templates, API endpoints that the UI calls, CLI/webhook entry points if the "client" is a machine.
2. Identify the actors and states that gate behavior: anonymous vs. authenticated user, roles/permissions, feature flags, empty vs. populated data states.
3. Trace what each interactive element actually does — form submissions, buttons, links, redirects — through to its outcome (page change, record created, email sent, error shown).

For a large codebase, delegate exploration of separate areas to parallel subagents and merge their findings.

## Granularity

Granularity controls how comprehensive the inventory is, not how detailed each flow is (steps stay concrete at every level):

- **low** — only the critical happy paths: one flow per major feature, the paths the business would notice breaking within an hour.
- **medium** — all happy paths plus the important variations: validation failures the user will commonly hit, alternate entry points, cancel/back-out paths on destructive or paid actions.
- **high** — comprehensive: everything in medium plus edge cases, error and permission-denied paths, empty states, boundary behaviors (expired session, double-submit, unauthenticated access to protected pages). Aim for the full set of flows a thorough QA engineer would enumerate.

## Deduplication

The output must contain no duplicates. Two flows are duplicates when they exercise the same steps and outcome and differ only in data values — merge them into one flow and note the variable input (e.g. "search for any term", not one flow per term). A flow that is a strict prefix of another is only its own flow if it ends in a distinct verifiable outcome. Before writing the file, do an explicit dedup pass over the full list and merge or drop offenders.

## Output format

Write `user-flows.md` in this exact structure. The format is optimized for a model to later read and generate tests from: stable IDs let generated tests be traced back to flows, preconditions/expected map directly to test setup/assertions, and source pointers tell the test writer where to look.

```markdown
# User Flows

> granularity: <low|medium|high> | area: <filter or "all"> | generated: <YYYY-MM-DD>

## <Area name, e.g. Authentication>

### UF-001: <Short flow name>
- **Actor:** <who performs it, e.g. anonymous user, admin>
- **Precondition:** <required state before the flow, e.g. "registered account exists">
- **Steps:** <step 1> → <step 2> → <step 3>
- **Expected:** <observable, assertable outcome>
- **Source:** <key file(s)/route(s) implementing this flow>
```

Rules:

- Number IDs sequentially (`UF-001`, `UF-002`, …) across the whole file; never reuse an ID for a different flow.
- Group flows under `##` area headings so an area-filtered regeneration can replace one section cleanly.
- Keep each step an atomic user action or observable transition, concrete enough to automate ("click Purchase on the item page"), free of implementation detail a test doesn't need.
- Keep **Expected** assertable: what a test could check (URL, visible text, record created, email queued) — not vague ("it works").

## Updating an existing file

If `user-flows.md` already exists:

- **No area filter:** regenerate the whole file.
- **With an area filter:** replace only the matching area section(s), keep all other sections untouched, and continue ID numbering from the highest existing ID so IDs already referenced by tests stay stable.

## Update the project's CLAUDE.md

After writing the file, add a short section to the project's `CLAUDE.md` (create the file with just this section if it doesn't exist; refresh the section if it's already there instead of duplicating it) so future sessions know the inventory exists and how to use it:

- `user-flows.md` at the project root is the inventory of user flows (stable `UF-NNN` IDs, grouped by area), generated by `/user-flows:extract-user-flows`.
- Keep it in sync after behavior changes with `/user-flows:update-user-flows` — don't edit flow entries by hand, and never renumber IDs (tests reference them).
- Playwright E2E tests can be generated and synced from it with `/user-flows:test-user-flow`.

Keep the section to a few lines — CLAUDE.md is loaded every session, so it earns its place by being short.

## Finish

Report: total flow count, count per area, granularity used, the file path, and whether CLAUDE.md was created or updated. Do not paste the whole file back into the conversation.
