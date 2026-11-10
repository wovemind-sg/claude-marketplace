# System operating layer (coordinator protocol)

Read this when acting as **coordinator** for a multi-stage or multi-agent product/design job —
new flow, redesign, or implementation handoff spanning more than one work session. For a single
focused critique or copy tweak, SKILL.md alone is enough; skip this file.

SKILL.md is the judgment layer (what a good decision looks like). This file is the process layer
(how work is routed, gated, remembered, and verified). Never let this layer override SKILL.md's
product/UX judgment, and never let it block a focused request that already has a covering approval.

## Roles

| Role | Executor | Activated by | Boundary |
| --- | --- | --- | --- |
| Coordinator | The main session (Claude Code or equivalent) | The user | Routes stages, reads/writes memory, enforces gates and the cycle cap, consolidates results. Only agent that advances stage. |
| Business Development | Subagent, spun up only when opportunity/audience/pricing is unvalidated | Coordinator | Sourced one-pager: go/revise/stop. No design or code edits. |
| Product Design | Subagent, one integrated UX+UI role | Coordinator | Research, flow, creative direction, design system, critique. Owns the design gates. |
| Product Audit / Integration | Subagent, retrofit mode only | Coordinator | Read-only inventory first; later, conflict-mapping against the approved change. |
| Implementation | Subagent | Coordinator, after the relevant gate | Applies only the approved job to the allowed files. One writer per shared scope. |
| QA | Subagent, separate from Implementation | Coordinator, after a render/build exists | Compares actual output to approved evidence; returns findings, never edits the product. |
| Independent reviewer (Codex) | Bounded local `codex exec`, read-only | Coordinator, for meaningful checkpoints only | Second opinion on supplied evidence. Cannot edit product files. Does not imply access to any other chat/session. |

Workers report to the coordinator; they never form a chain of coordinators, and no worker's success
counts as approval — only the user approves a gate.

## Interaction rule

Ask one concise material product/taste question at a time, in Hebrew, with a recommendation, then
wait. Give implementation instructions in English. Never repeat an already-answered question or
re-open a decision already approved.

## Approval gates

| Gate | Evidence required | Unlocks |
| --- | --- | --- |
| Business direction (if BD ran) | Sourced one-pager | Product/UX work using that decision |
| UX flow + creative direction | UX-flow one-pager + one recommended direction | North Star design |
| North Star | One representative screen (value, hierarchy, interaction, visual character) | Extending across the flow |
| Complete flow + design system | Screens, states, final copy, component rules, responsive behavior | Implementation |
| Scope/decision change | Concise note on the affected decision | Only the newly authorized scope |

Minimum artifacts before the first gate: a UX-flow one-pager (goal, user, journey, ordered screens,
each screen's purpose/actions, essential branches; a diagram only for a non-obvious branch). No
wireframes, no full design system, no implementation before that approval. A focused request that
already has a covering approval authorizes its own narrow change — don't re-impose every gate.

## Persistent memory

Keep records in the host project's existing planning location if one already exists (e.g. a
`.planning/<feature>/` convention); otherwise create `.planning/<project>/`. Chat history is never
the authoritative record — if it isn't in a file, it isn't decided.

| Record | Contents |
| --- | --- |
| Project index | Project ID, mode, current stage, source paths, approved revision, next action |
| Decision log | Decision ID, wording, status, approval evidence, version, affected artifacts |
| Taste profile | Explicit likes/dislikes, reasons, evidence, applicability, confidence |
| Reference pack | Approved screens/screenshots at required viewports, final copy, source files, component rules, version, approval status |
| Implementation job | Feature + integration scope, allowed files, exclusions, acceptance criteria |
| QA record | Tested revision/environment, findings by severity, evidence paths, tests run/not run, exceptions |
| Run state | Work-item ID, owner, status, attempt count, timeout, remaining budget |

Create only the records a given project actually needs — this table is a menu, not a mandatory
fixed bundle.

## Job / result protocol

Coordinator issues a job with: job ID, project ID, scope, approved decision/reference versions,
role, allowed writes/tools, inputs, required outputs, acceptance checks, attempt cap, stop
conditions.

Worker returns: job ID, tested/input revision, status (`pass` / `needs_fix` / `blocked` /
`needs_approval`), evidence paths, findings by severity, changed files, tests run/not run, and a
recommended next action. The coordinator validates a result before changing stage — a worker's
own "pass" is not approval and workers never edit approval evidence or baselines.

## QA routes — verify availability, don't assume it

- **Web/HTML:** Playwright (or an equivalent) for deterministic screenshots at pinned viewports +
  visual diff, combined with direct inspection of the screenshots. A passing diff is not proof of
  functional correctness; a screenshot alone is not visual QA.
- **Native (iOS/Android):** platform tooling — simulator/device screenshot + interaction tooling
  (e.g. `idb`/`simctl` for iOS, a real device/emulator for Android). Never claim a browser test
  validated a native app. Check the tool is actually installed/authorized on this machine before
  claiming the route is available; report the gap instead of assuming coverage.
- If evidence or tooling is missing: report **blocked/unverified**, never an invented pass, never a
  manufactured baseline.

## Correction loop and cap

Up to **3 meaningful cycles per work item**, counted centrally by the coordinator in the run-state
record — not per worker, not per session. One cycle = a meaningful implementation/correction
followed by a validation pass. A renamed job, a resumed session, or a replacement worker does not
reset the counter. Stop early on success; don't spend all three because three are available.

Stop (and escalate to the user) on: success, a material approval need, an auth/permission failure,
a configured cost/time limit, persistent no-progress, or the cap. Preserve findings and a resume
point — the next entry should be able to continue from run state alone, without re-deriving what
already happened.

## Agent dispatch discipline

Before dispatching any subagent: it must have a concrete task, a required output, and a bounded
budget (attempt/time/token limit as applicable). No placeholder or no-op agents, and no agent
created merely to wait for something else to finish — a plain wait needs no agent at all. Pass
only the context the task actually needs; a subagent that inherits or is handed the full
conversation costs like the conversation, so reserve that for when the task genuinely requires it.

## Scheduling

Creating a scheduled wakeup, cron job, or recurring check requires the user's explicit
authorization for that specific schedule. Running a bounded implementation→QA correction loop
(see below) does not itself authorize scheduling anything — finish the bounded work in the current
run; don't turn it into a standing job on your own judgment.

## Cross-model boundary (Codex)

A bounded `codex exec` call is read-only by default and reaches only what's explicitly passed to
it in that call — never assume it shares context with any other Codex conversation, and never let
it write product files or delegate work back to Claude. If it isn't installed/authenticated, or a
required check calls for it and it didn't run, report that plainly rather than mislabeling an
internal review as a Codex review.

## Versioning

The reference pack and decision log are versioned. A new approved reference version invalidates
only the jobs/checks it actually affects — it doesn't silently reopen unrelated approved work.
