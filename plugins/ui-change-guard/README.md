# ui-change-guard

Pre-push safety net for UX/UI changes in web apps (HTML/Jinja/htmx/Alpine, React/Vue/Svelte) and native apps (React Native/Expo, SwiftUI/UIKit, Jetpack Compose, Flutter, Capacitor/Ionic hybrids). Built for a team where a designer makes front-end changes with Claude Code and the engineer cannot review every diff: the skill reviews the working tree against the base branch and answers **is this safe to push?** with a verdict and a list of concrete issues.

It targets the failure modes test suites tend to miss:

- a form field deleted or renamed in a template while the backend handler still reads it;
- a redesigned page that quietly lost buttons, actions, states, role-specific controls, or confirmations the old page had;
- UI that became unusably slow (polling, unbounded lists, N+1 from templates, heavy assets, expensive CSS/motion);
- broken htmx/Alpine wiring (targets that no longer exist, Alpine roots inside swap targets); on native, broken navigation/state/lifecycle wiring (renamed routes still deep-linked, screens removed from the navigator, lost cleanup);
- native-only breaks: permission requests without usage strings, denied-permission paths that look like a cancel, store-compliance regressions (account deletion, restore purchases, privacy manifest), safe-area/keyboard-avoidance/Dynamic Type regressions, assets missing densities or font registration;
- permission conditionals removed from templates (security leak), unsafe HTML injection;
- accessibility and responsive regressions;
- tests edited to pass instead of the UI fixed;
- changes that crossed out of the design domain into routes, models, migrations, or dependencies.

## Skills

### `/ui-change-guard:review-ui-change [base-ref | files]`

Reviews everything from the merge-base with `main`/`master` (or the given ref) to the working tree, including uncommitted and untracked files. Detects the platform, runs the bundled inventory-diff script, traces every removed/renamed dependency to its consumers (form → handler on web; binding → view-model → DTO → API on native), checks functional parity of redesigned pages/screens, hunts performance regressions (static + Playwright measurement on web, simulator/profiler on native) reviews test diffs for weakened assertions (it does not run the suite — CI does that), and applies the matching catalog: `references/checks.md` (web) and `references/checks-native.md` (native, with a Capacitor/hybrid section). It never edits source or tests, but when the branch has a PR it writes (or, on SAFE, removes) a marker-delimited engineer handoff section in the PR body (format: `skills/review-ui-change/references/engineer-handoff.md`).

Output:

```
# UI change review — SAFE | UNSAFE | NEEDS ENGINEER REVIEW
Base · files · pages reviewed · tests · perf measured
## Blockers      — will break something / lost functionality / weakened tests / security
## Warnings      — likely degradation (perf smell, a11y, responsive, test-only selectors)
## Needs engineer — outside the designer's domain or unverifiable from code
## Notes
## Checked and fine
```

Each Blocker names the page and element in user terms, the file:line, the evidence (grep hit, test output, measurement), and the smallest action that makes it safe.

### `/ui-change-guard:engineer-review-ui-change [PR number or URL]`

For the engineer receiving a flagged PR. Reads the PR body, all comments, and inline review comments, checks out the branch, briefs you on what the designer was trying to do, then asks one question per flagged danger. After every question is answered it implements the follow-ups, one Sonnet subagent per task, strictly in series (non-trivial tasks get a plan first, shown to you). Subagents stop and return questions instead of guessing; the skill relays them to you. With your OK it commits, and posts a humanized PR comment summarizing the outcome per decision item plus a "For the designer to follow up" section. Questions and the comment follow `/humanizer:humanizer` rules; install the `humanizer` plugin for best results, otherwise the rules are applied inline.

### `/ui-change-guard:push-guard install | uninstall | status`

Turns the review into a pre-push gate for the current repo (per clone; lives in `.git/`, nothing committed):

- **Pushes Claude makes** — the plugin's `PreToolUse` hook blocks `git push` until `review-ui-change` passes for HEAD (SAFE or NEEDS ENGINEER REVIEW). Inactive in repos where the guard is not installed.
- **Pushes from the terminal** — a git `pre-push` hook runs the review via `claude -p` (minutes and tokens per push) and blocks on UNSAFE. Because that run has Bash, the review's handoff step also updates the PR body on each guarded push. `git push --no-verify` skips it once.

A passed commit is recorded in `.git/ui-change-guard/reviewed-<sha>`, so each commit is reviewed once. `install` refuses to overwrite an existing non-guard `pre-push` hook (husky, etc.) and respects `core.hooksPath`.

### Bundled script

`skills/review-ui-change/scripts/ui_inventory_diff.py [--base REF] [--json] [FILE ...]` — per changed UI file, lists removed and added items. Web (Jinja/Django/Twig/HTML, Vue/Svelte/Astro, JSX/TSX): forms, fields, option values, buttons, links, htmx attributes, event handlers, ids/test-ids, template conditionals, template variables, includes, external assets, timers. Native (`.swift`, `.kt`, `.dart`, Android `.xml`, React Native `.tsx/.jsx`): actions, inputs and bindings, navigation targets, dialogs, accessibility labels, test identifiers, list containers (virtualized vs eager), timers/effects, permission requests, role/entitlement conditionals. Regex-based, usable standalone.

## Examples

```
/ui-change-guard:review-ui-change
/ui-change-guard:review-ui-change main
/ui-change-guard:review-ui-change templates/profile.html templates/partials/nav.html
/ui-change-guard:push-guard install
```

Works with the `user-flows` plugin: if `user-flows.md` exists, flows touching changed files are walked against the new markup and lost steps are reported by flow ID.

No environment variables required. Python 3 for the script; Playwright (web) or a simulator/emulator + Maestro (native) optional for performance measurement.
