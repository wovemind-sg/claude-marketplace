---
name: review-ui-change
description: Pre-push safety review of UX/UI changes made by a designer (or anyone editing templates, components, screens, styles, or front-end scripts) in web apps (HTML/Jinja/htmx/Alpine, React/Vue/Svelte) and native/mobile apps (React Native/Expo, SwiftUI/UIKit, Jetpack Compose, Flutter, Capacitor) — detects removed or renamed form fields the backend still depends on, redesigned pages that lost buttons/actions/states the old page had, performance regressions that make the UI sluggish, broken htmx/Alpine or navigation/state wiring, accessibility and layout regressions, security leaks from dropped permission conditionals, missing permission usage strings and store-compliance breaks on mobile, and tests that were weakened to pass. Produces a SAFE / UNSAFE verdict with the list of issues. Use this whenever a UI/UX change is about to be pushed, committed, or handed to the engineer — "is this safe to push", "check my changes", "review before I push", "did I break anything", "sanity check the redesign" — even if the user does not say "review", and run it proactively at the end of any session where templates, components, screens, CSS, or front-end JS/Swift/Kotlin/Dart UI code were edited.
argument-hint: "[optional: base branch/ref, e.g. main, or specific files/pages to focus on]"
---

Review the UI/UX changes in the working tree before they are pushed and answer one question: **is it safe to push?** Return a verdict and, if not safe, exactly what is wrong and where.

You are the safety net between a designer and production. The designer owns look, layout, copy, and interaction design — and legitimately changes those. What they usually cannot see is everything *else* that hangs off a template: the backend handler that reads a form field by name, the JavaScript that finds an element by id, the test that clicks a button by its label, the permission check that was an `{% if %}` around a block, the query cost of rendering a list, the user who navigates by keyboard. A UI change is "safe" when it changes only what the designer meant to change and nothing those hidden consumers depend on. Your job is to find every place the change reaches further than intended, and to say so plainly.

Be a reviewer, not a fixer. Report. Never edit source, tests, or styles while reviewing — the designer decides what to do with the findings (you may offer to fix after the report). The one thing you do write is the engineer handoff section in the PR body (Step 7). Never "fix" a finding by changing a test to match the new UI.

## Step 1 — Establish what changed

0. **Platform.** Decide what kind of UI this is, because the consumers differ: **web** (templates, htmx/Alpine, React/Vue/Svelte pages — the "backend" is a route handler reading a form), **native** (React Native/Expo, SwiftUI/UIKit, Jetpack Compose/Android Views, Flutter — the "backend" is a view-model/store serializing to an API, and the OS adds permissions, store rules, safe areas, lifecycle), or **hybrid** (Capacitor/Ionic — a web app with native plugin calls; both sets of rules apply). Look at the changed files' extensions and the project manifests (`package.json` deps, `app.json`, `*.xcodeproj`, `build.gradle`, `pubspec.yaml`, `capacitor.config.*`). A monorepo can be both; review each surface by its own rules.

1. **Base.** Use `$ARGUMENTS` if it names a ref; otherwise the merge-base of `HEAD` with `origin/main`/`main`/`master`; otherwise `HEAD`. The review covers everything from that base to the working tree, uncommitted and untracked files included — the designer may not have committed yet.
2. **File list.** `git diff --name-status <base>` plus `git ls-files --others --exclude-standard`. Classify each file:
   - **UI** — templates, components, stylesheets, front-end scripts, static assets, i18n strings.
   - **Non-UI** — routes/controllers/handlers, view-models/stores when the change goes beyond binding a new field, models, schemas/DTOs, migrations, services, API clients, config, dependency manifests, CI, infra, and native project files (`Info.plist`, `AndroidManifest.xml`, `app.json`, `*.pbxproj`, `build.gradle`, `Podfile`, `pubspec.yaml`, `capacitor.config.*`).
   - **Tests** — any test file.
   Every non-UI or test file touched by a designer's change is a finding in itself (see Step 5), because it means the change crossed out of the design domain.
3. **Inventory diff.** Run the bundled script from the project root:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-ui-change/scripts/ui_inventory_diff.py --base <base>
   ```
   For web files it lists, per changed template/component, every removed and added form, field, option value, button, link, htmx attribute, event handler, id/test-id, template conditional, template variable, include, external asset, and timer. For native files (`.swift`, `.kt`, `.dart`, Android `.xml`, and `.tsx/.jsx` importing React Native) it lists actions (buttons, press/click handlers, gestures), inputs and their bindings, navigation targets, dialogs/alerts/sheets, accessibility labels, test identifiers, list containers (virtualized vs eager), timers/effects, permission requests, and role/entitlement conditionals. This is your worklist: **every REMOVED line must be explained** (relocated, renamed, or deliberately dropped with the consumer updated) and every ADDED line must be checked for cost and correctness. Also read the raw `git diff` — the script is regex-based and will miss things expressed unusually (fields built in a loop, components rendered from config, CSS-only changes).
4. **Shared surfaces.** For every changed partial, layout, macro, component, or global stylesheet, enumerate its consumers (`grep -rn` for the include/import/component name, or the CSS class). A change to a shared piece is a change to every page that uses it; review those pages too, not just the one the designer was looking at.
5. **Flow inventory.** If the project has a `user-flows.md` (from the `user-flows` plugin), list the flows whose `Source` lines point at changed files — those flows must still be completable after the change (Step 3).

## Step 2 — Trace every removed or renamed dependency

This is the "deleted a form field the backend needed" class. For each REMOVED/renamed item from the inventory diff, find its consumers before deciding it is harmless:

- **Form field (`name=`), option value, hidden input, submit button `name`/`value`:** grep the backend for the exact string — request parsing (`request.form[...]`, `form.get(...)`, `Form(...)`, `req.body.x`, `params[:x]`), pydantic/serializer/form classes, validation schemas, and the handler for the form's `action`/`hx-post` route. A field the handler reads as required is a **Blocker**: the request will fail or raise. A field the handler reads optionally is a **Blocker** too if downstream code relies on the value (persisted column, notification, billing) — follow it one hop further. Also check: a removed `csrf_token`/anti-forgery hidden input (every POST now rejected), a removed `enctype="multipart/form-data"` on a form with a file input (uploads silently arrive empty), a changed `method`, a field moved outside its `<form>` element (no longer submitted), a `<select>` whose option values changed (backend enum/validator rejects or mis-maps), an input whose `type` changed (`number`→`text` sends strings; `checkbox`→`radio` changes the value shape).
- **Element `id`, `data-testid`, class used as a hook:** grep JS/TS, htmx `hx-target`/`hx-include`/`hx-swap-oob`, Alpine `$refs`/`x-ref`, CSS, **and tests**. A target an htmx response or script still points at but that no longer exists is a **Blocker** (htmx logs an error and swaps nothing; JS throws). A selector only tests use is a **Warning** — the test will fail and must be updated by the engineer, not weakened.
- **Event handler / htmx attribute (`@click`, `hx-post`, `hx-trigger`, `x-model`, `onsubmit`):** if removed, the element is now inert — a button that does nothing is a **Blocker** unless the action was intentionally removed and nothing else exposes it. If `hx-include`/`hx-vals`/`hx-headers` were dropped, the request now carries fewer fields; treat like a removed form field.
- **Template conditional (`{% if user.is_admin %}`, `v-if="can.edit"`):** this is the most dangerous removal. If the block it guarded is still rendered, content or actions are now shown to users who should not see them — a **Blocker (security)** even when the backend still enforces the permission, because it leaks existence and invites errors. If the block was removed with it, that is a lost feature for the gated role (Step 3).
- **Template variable / include / route name:** an ADDED variable the route does not pass renders empty or raises (`UndefinedError`, 500 in strict mode) — open the route that renders this template and confirm it supplies the name. A changed `url_for`/`path`/`href` must resolve to an existing route with the same required parameters. A changed `include`/`import` path must exist.
- **i18n keys, analytics attributes (`data-track`, `data-analytics`, `gtag`), SEO tags (`<title>`, `<h1>`, meta, canonical):** removed → **Warning**, with the consumer named.

**Native analog.** On native there is no `<form>`: the field is a binding (`$phone`, `value={phone}`, `vm.phone`, a `TextEditingController`) feeding a view-model or store that is serialized into an API request body. Treat a removed binding exactly like a removed form field: find the DTO/`Codable`/`data class`/schema that carries it, then the API call, then the backend. A removed `NavigationLink`/`navigate(...)`/`Navigator.push` is a removed link; a removed `testID`/`accessibilityIdentifier`/`testTag`/`Key` is a removed test selector; a removed `if user.isAdmin { ... }` / `{isPremium && ...}` is a removed permission conditional. Section N1 and N8 of `references/checks-native.md` list the native-specific consumers (deep-link config, other screens reading shared state, event names, lifecycle hooks).

When grep finds nothing, say so explicitly in the report ("no backend consumer found for `phone`") — absence of evidence is a finding the engineer can confirm in seconds.

## Step 3 — Check functional parity of redesigned pages

This is the "redesigned the page but lost half the buttons" class. For each changed page or component, build the **old capability list** from the base version and confirm each capability survives in the new version. Capabilities are not just buttons — enumerate all of:

- every button, link, menu item, tab, context-menu/kebab action, bulk/selection action, keyboard shortcut, drag-and-drop, swipe;
- every form and every field, including ones hidden behind "advanced"/"more" toggles;
- every **state view**: loading indicator, empty state, error message slot (`{{ error }}`, `{{ form.errors }}`, flash messages), validation feedback, success confirmation, disabled/readonly variants, pagination/infinite scroll, sort and filter controls, search;
- every **role/condition branch**: admin-only controls, owner vs viewer, logged-out vs logged-in, feature-flagged blocks, mobile-only vs desktop-only variants (e.g. a responsive nav menu);
- every **safety interaction**: confirmation dialogs on destructive actions, "undo", cancel/back paths, unsaved-changes warnings;
- every **wiring** on those elements: `type="submit"` vs `type="button"`, `hx-confirm`, `href`, `target`, `download`, `rel`;
- on native, additionally: swipe/long-press/context-menu/pull-to-refresh gestures, toolbar/tab-bar/app-bar items, FABs, keyboard-return submit, share/export intents, platform-conditional blocks (`#if os(iOS)`, `Platform.OS`), and widget/watch/shortcut entry points that render the same data (section N2 of `checks-native.md`).

For each old capability: locate the equivalent in the new markup (same action — it may be relabeled, moved, or restyled; match on *what it does*, not what it says). Missing with no equivalent → **Blocker (lost functionality)**, naming the capability and where it used to be. Present but inert (handler, `href`, or `hx-*` gone) → Blocker. Present only for some roles/breakpoints where it used to be for all → Blocker. A destructive action that lost its confirmation → Blocker. A `<button>`/`<a>` replaced by a `<div>`/`<span>` with a click handler → **Warning (accessibility)**: not focusable, not keyboard-operable, not announced.

If `user-flows.md` exists, walk every flow that touches the changed files step by step against the new markup; any step that can no longer be performed is a Blocker, cited by flow ID.

Do not accept "the designer must have meant to remove it" as an explanation. You cannot know that; the report asks them. Only an explicit statement in the conversation ("we're dropping the export button") downgrades a lost capability to a Note recording the deliberate removal.

## Step 4 — Hunt for performance regressions

This is the "UI became unusably slow" class. Performance regressions from UI changes are usually one of a handful of patterns; check each against the diff (static) and, when the app can be run, measure (dynamic).

**Static — look in the diff for:**
- **Polling and timers:** `hx-trigger="every Ns"` (especially on many elements or under 5 s), `setInterval`, `requestAnimationFrame` loops, Alpine `x-effect`/`$watch` that mutate their own dependencies. Per-row `hx-trigger="load"` inside a loop = N requests on page load. Flag anything under 5 s or inside a loop.
- **Lists without limits:** a `{% for %}`/`x-for`/`.map` that used to be paginated, sliced, or virtualized and no longer is; rendering a full collection where a page was rendered; nested loops producing thousands of nodes; a template now touching a relationship inside a loop (`{{ order.customer.name }}`) that the view did not eager-load — this is an N+1 query introduced from the template side. Check the route's query for prefetch/joinedload/`select_related`.
- **Heavy assets:** new `<script src>`/`<link>` to large libraries or multiple font families/weights, synchronous scripts in `<head>` without `defer`/`async`, inline base64 images, images without `width`/`height` (layout shift) or `loading="lazy"`, autoplaying video, uncompressed hero images added to the repo (check file sizes in the diff with `git diff --stat`).
- **Expensive CSS and motion:** `transition: all`, animating `width`/`height`/`top`/`left`/`margin`/`box-shadow`/`filter` instead of `transform`/`opacity`, `backdrop-filter`/large `blur()` over big areas, infinite animations, `box-shadow` on every row of a list, `will-change` sprinkled widely, universal selectors with expensive properties, heavy `:has()`/`:nth-child` over long lists, `position: fixed` + `backdrop-filter` on mobile.
- **Unthrottled listeners:** handlers on `scroll`, `resize`, `mousemove`, `input` (search-as-you-type without `delay:`/debounce; htmx `hx-trigger="keyup"` without `delay:300ms changed`).
- **Client re-render traps:** huge `x-data` objects, `x-html` of large server fragments, re-initialising third-party widgets on every htmx swap without cleanup, removed `hx-swap` settings that previously limited the swapped region.
- **Removed caching or lazy loading:** deleted `hx-trigger="revealed"`/`intersect`, removed `loading="lazy"`, removed `defer`.

**Dynamic — when the dev server can be started (check `Makefile`, `package.json`, `README`):** load each changed page with Playwright (the `/playwright-cli` skill if available, else a short `playwright` script) and record: time to `load`/`networkidle`, DOM node count (`document.querySelectorAll('*').length`), number of network requests in the first 10 s after load (polling shows up here), and total transferred bytes. Interact with the main controls and note anything visibly sluggish. Compare against the base version if a baseline is cheap (a running staging URL, or `git worktree add <scratch> <base>` when the app runs without heavy setup); otherwise judge against thresholds: >1,500 DOM nodes on a list page, >3 s to networkidle locally, any request repeating under 5 s, >2 MB transferred — each is a **Warning**, and a clear order-of-magnitude regression versus base is a **Blocker**. Say in the report which pages you measured and which you could not.

**Native static patterns** are the same ideas in different clothes — virtualized list replaced by an eager one (`FlatList`→`ScrollView`+`.map`, `LazyColumn`→`Column`+`forEach`, `List`→`VStack`+`ForEach`, `ListView.builder`→`Column`), timers/effects without cleanup, work in `body`/`build()`/render, re-render storms from unstable props, JS-thread animations, full-size images in thumbnails, blur/shadow per row, new work on the startup path. Section N3 of `checks-native.md` has the full list. **Native dynamic measurement:** when a simulator/emulator or device is available (Maestro flows if the project has them, else manual), open each changed screen and watch for dropped frames on scroll, screen-open time, and memory growth when navigating back and forth; use the platform profiler (Xcode Instruments, Android Studio Profiler, RN perf monitor/Flipper, Flutter DevTools) when something feels slow. Test on a mid-tier device profile, not only the newest simulator.

## Step 5 — Scope, tests, and the rest of the checklist

Load the catalog for the platform you identified in Step 1 and apply every section to the diff — each item has the signal to look for, the verification step, and the severity:

- **Web:** `${CLAUDE_PLUGIN_ROOT}/skills/review-ui-change/references/checks.md`.
- **Native:** `${CLAUDE_PLUGIN_ROOT}/skills/review-ui-change/references/checks-native.md`, plus sections 2, 7, 9, 10, 13 of `checks.md` (it says which). Native adds classes web does not have: permission usage strings and store-compliance rules (a new camera call without its `Info.plist` string crashes on request; a removed account-deletion entry or restore-purchases button gets the app rejected), denied-permission paths that look like a cancel, safe-area and keyboard-avoidance regressions, Dynamic Type clipping, state that does not survive rotation or process death, deep-link routes that break when a screen name changes, assets missing densities or font registration.
- **Hybrid (Capacitor/Ionic):** both files; section N11 holds the webview-specific traps (the non-existent `isNativePlatformAvailable` gate, `allowNavigation` for OAuth, denied-permission handling, 16px inputs).

Highlights you must never skip:

- **Changes outside the UI domain.** Any touched route, model, schema/DTO, migration, service, API client, config, dependency manifest, or native project file (`Info.plist`, `AndroidManifest.xml`, `app.json`, `build.gradle`, `Podfile`, `pubspec.yaml`) is a **Needs-engineer** finding, listed file by file, regardless of how small. A designer's Claude editing a handler to "make the field optional" is exactly the change that should be reviewed by the engineer.
- **Tests.** Do not run the test suite — CI runs it on every push, so running it here adds no protection. Spend the effort on what CI cannot see: read the diff of test files. A weakened test still passes CI, so this is judgment only you can apply: deleted assertions, loosened selectors, skipped/`xfail`ed tests, or changed expected values are a **Blocker** — tests were modified to pass, not the UI fixed to pass them. Report these as "tests weakened", quoting the removed assertion.
- **Security surface:** removed permission conditionals (Step 2), new `x-html`/`innerHTML`/`|safe`/`dangerouslySetInnerHTML` on user-provided content, new inline scripts under a CSP, `target="_blank"` without `rel="noopener"`, secrets or internal URLs now in markup, removed `autocomplete="off"` on sensitive fields.
- **Accessibility:** inputs that lost their `<label>`/`aria-label` (placeholder is not a label; on native: `accessibilityLabel`/`contentDescription`/`semanticLabel`), images that lost `alt`, `outline: none` without a replacement focus style, color-only state indication, contrast drop, heading order, touch targets under 44 px, modals without focus trap/`Escape`, motion without `prefers-reduced-motion`, text-entry controls below `font-size: 16px` (iOS zooms the page on focus).
- **Responsive and layout:** (native: safe areas, keyboard avoidance, Dynamic Type, size classes, dark mode, RTL) removed breakpoint rules, fixed pixel widths, `overflow: hidden` that clips content, `100vh` on mobile, z-index changes that bury modals/toasts, removed safe-area padding, long strings without wrapping.
- **Behavioral semantics hidden in markup:** changed default values (`checked`, `selected`, default option), removed client validation (`required`, `pattern`, `min`/`max`/`maxlength`) the backend may trust, changed `autocomplete`/`inputmode`/`type` affecting mobile keyboards, copy changes that alter meaning — legal/consent text, pricing, destructive-action wording, button labels that no longer say what the action does.
- **htmx + Alpine interplay:** an element carrying `x-data`/`x-show` that is now inside an htmx swap target loses reactivity after the first swap; `hx-swap="outerHTML"` on an Alpine root; missing `x-cloak`; Alpine components with `tojson` output inside double-quoted attributes.
- **Assets and build:** new CSS/JS files not linked from the layout, Tailwind classes built dynamically (purged at build), renamed static files still referenced elsewhere, new dependencies.

## Step 6 — Report

Severity drives the verdict:

- **Blocker** — will break something or lose functionality: broken backend contract, lost capability, weakened tests, security leak, order-of-magnitude slowdown.
- **Warning** — likely degrades the experience or will bite soon: perf smell without measurement, accessibility regression, test-only selector removed, responsive risk.
- **Needs engineer** — not wrong per se, but outside the designer's domain or unverifiable from the code alone.
- **Note** — deliberate removals confirmed in conversation, things checked and found fine that the engineer would otherwise ask about.

Verdict: **UNSAFE** if any Blocker. **NEEDS ENGINEER REVIEW** if no Blocker but any Needs-engineer item or a Warning you could not rule out. **SAFE** otherwise (Warnings and Notes may still be listed).

Use exactly this structure:

```
# UI change review — <VERDICT>

Base: <ref>  ·  Files: <n> UI, <n> non-UI, <n> tests  ·  Pages reviewed: <list>
Platform: <web | native (RN/SwiftUI/Compose/Flutter) | hybrid>  ·  Test diffs: <n reviewed / none>  ·  Perf measured: <pages/screens or "not measured — why">

## Blockers
1. **<short title>** — `<file>:<line>`
   What changed: <one line>
   Why it breaks: <consumer / lost capability / measurement, with file:line of the evidence>
   To make it safe: <the smallest concrete action>

## Warnings
...

## Needs engineer
...

## Notes
...

## Checked and fine
- <removed item> — no consumer found in <where you looked>
```

Write for the designer: name the page or screen and the element the way a user would ("the Save button on the profile screen"), then the file and line. Every Blocker needs evidence — the grep hit, the test output line, the measurement — not a hunch. Keep "Checked and fine" short but present: it is what lets the engineer trust that a SAFE verdict was earned rather than assumed. If the diff is empty or touches no UI files, say so in one line and stop.

## Step 7 — Hand off to the engineer

The engineer who picks up a risky PR was not in this session, so the report in this terminal never reaches them. Put it in the PR body. Do this only after the report is written.

Read the format in `${CLAUDE_PLUGIN_ROOT}/skills/review-ui-change/references/engineer-handoff.md`. For "what the designer was going for", use the conversation and the commit messages on the branch; write "Not stated" if neither says.

1. Run `gh pr view --json number,body` for the current branch. If it fails because there is no PR, skip the write, print the section in the reply so the designer can paste it later, and tell the designer to re-run `/ui-change-guard:review-ui-change` after opening the PR, because the push guard records each commit as reviewed and will not re-run the review (or write the handoff) for the same commit.
2. Verdict UNSAFE or NEEDS ENGINEER REVIEW: build the section from the report (one D-item per Blocker, Warning, and Needs-engineer finding). If the body already contains the start and end markers, replace everything between them, markers included; otherwise append the section after a blank line. Leave the rest of the body untouched (GitHub often stores bodies with `\r\n` line endings; match the blank line and markers in whichever style the body uses and keep its other bytes as they are). Re-fetch the body (`gh pr view --json body`) immediately before writing and apply the edit to that fresh copy, so an edit made on GitHub since the first read is not lost. Write the new body to a temp file and run `gh pr edit <number> --body-file <file>`.
3. Verdict SAFE: if the body contains a marked section from an earlier run, remove it (and the blank line before it) the same way. If there is none, do nothing.

Never touch the PR title, comments, or anything outside the markers. If `gh pr edit` fails, report the error and print the section instead.
