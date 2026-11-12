# UI change review — full check catalog

Each item: **Signal** (what to look for in the diff / inventory), **Verify** (how to confirm it is a real problem), **Severity** when confirmed. Severities: Blocker · Warning · Needs engineer · Note. Apply every section to every changed file; skip an item only when the signal is absent.

Contents: 1 Backend contract · 2 Functional parity · 3 Performance · 4 Security · 5 Accessibility · 6 Responsive/layout · 7 Behavioral semantics · 8 htmx/Alpine/JS wiring · 9 Tests · 10 Scope · 11 Assets/build · 12 Content/i18n/SEO/analytics · 13 Shared components · 14 Non-browser templates

---

## 1. Backend contract (template → handler)

| Signal | Verify | Severity |
|---|---|---|
| REMOVED field `name=X` | grep handler of the form's action/`hx-post` and its schema/form class for `X`. Follow one hop: where is the value stored/sent? | Blocker if read (required or used downstream); Note if truly unread |
| Field RENAMED (`name` old→new) | Same grep for both names; handler still reads old name = value now always missing | Blocker |
| REMOVED hidden input (`csrf_token`, `_token`, `next`, `redirect`, `id`, `version`, `return_to`) | CSRF: every POST rejected. `next`/`redirect`: login no longer returns to the page. `id`/`version`: handler cannot find record / optimistic locking lost | Blocker |
| Form `enctype` removed/changed while a `type="file"` input exists | Uploads arrive empty | Blocker |
| Form `method` changed, or `action` changed | Route exists for that method? Same handler? | Blocker if no / different |
| Field moved outside `<form>` (markup restructure, modal extraction) | Is it inside the form element or linked with `form="<id>"`? htmx: inside `hx-include`? | Blocker |
| `<option value>` set changed | grep handler/enum/validator for the old and new values | Blocker if validator rejects or maps differently |
| Input `type` changed (`number`↔`text`, `checkbox`→`radio`/`select`, `date`→`text`) | Value shape/format the handler parses; `checkbox` absent-when-unchecked semantics | Warning; Blocker if handler parses strictly |
| Submit button `name`/`value` removed (handler branches on which button) | grep handler for the button name | Blocker |
| `hx-include`, `hx-vals`, `hx-headers`, `hx-params` removed/changed | Request now lacks fields/headers the handler reads | Blocker |
| ADDED template variable | Open the route(s) rendering this template; is the name passed? Undefined → empty or 500 in strict mode | Blocker if not passed |
| Changed `url_for`/`url`/`path`/`href` route name or params | Route exists with those params? | Blocker |
| Changed `include`/`extends`/`import`/component path | File exists? Same macro/slot names? | Blocker |
| Removed `{{ error }}`/`form.errors`/flash rendering | Server validation failures now invisible — user sees nothing happen | Blocker |

## 2. Functional parity (old page vs new page)

Build the old capability list from `git show <base>:<file>`; match each to the new file by *what it does*.

| Signal | Verify | Severity |
|---|---|---|
| REMOVED button/link/menu item/tab/action with no equivalent | Search the new markup and any new partial for the same `href`/`hx-*`/handler/action value | Blocker (lost functionality) |
| Element present but handler/`href`/`hx-*` gone | It is now inert | Blocker |
| REMOVED template conditional, block also gone | Role/state-specific feature lost (admin controls, owner actions, logged-in extras) | Blocker |
| Removed mobile- or desktop-only variant (responsive nav, hamburger menu, bottom bar) | Is the capability reachable on both breakpoints? | Blocker |
| Removed pagination / load-more / infinite scroll / sort / filter / search | Can the user still reach all records? (also perf §3) | Blocker |
| Removed loading indicator (`hx-indicator`, spinner) | User gets no feedback on slow actions | Warning |
| Removed empty state | Blank area instead of guidance | Warning |
| Removed confirmation (`hx-confirm`, `confirm()`, dialog) on destructive action | One click now deletes/pays/sends | Blocker |
| Removed cancel/back/close path (modal without close, wizard without back) | User trapped | Blocker |
| Removed unsaved-changes warning / undo | | Warning |
| Removed keyboard shortcut handler, drag-and-drop, context menu | | Warning (Blocker if it was the only way) |
| Removed `download`, `target`, `rel`, `type="submit"` → `type="button"` | Behavior change on click | Blocker |
| Hidden behind a new toggle/menu with no affordance | Is there a visible way to discover it? | Warning |
| `user-flows.md` flow step no longer performable | Walk each flow touching the file | Blocker, cite flow ID |

## 3. Performance

| Signal | Verify | Severity |
|---|---|---|
| `hx-trigger="every Ns"`, `setInterval`, rAF loop | Interval < 5 s, or on many elements, or in a loop | Warning; Blocker if measured request storm |
| Per-row `hx-trigger="load"` / `revealed` removed in favor of eager | N requests on load | Warning |
| Loop over unbounded collection (pagination/slice/virtualization removed) | Count rows in a realistic DB; DOM node count after load | Blocker if > ~1,500 nodes or visibly slow |
| Relationship access inside loop (`item.owner.name`) newly added | Route eager-loads? (`joinedload`, `selectinload`, `prefetch_related`, `select_related`, `include`) | Blocker (N+1) if not |
| New `<script src>`/`<link>` libraries, fonts (several families/weights) | Size; `defer`/`async`; `font-display` | Warning |
| Sync script in `<head>` without `defer` | Blocks render | Warning |
| Images without `width`/`height`, without `loading="lazy"` below fold, huge files in diff (`git diff --stat`, `ls -la`) | Layout shift, bytes | Warning |
| Autoplay video, animated GIF, inline base64 | | Warning |
| `transition: all`; animating `width/height/top/left/margin/padding/box-shadow/filter`; infinite animations; `backdrop-filter`/`blur()` on large or fixed areas; `box-shadow`/`filter` per list row | Jank on scroll, especially mobile | Warning |
| Unthrottled `scroll`/`resize`/`mousemove`/`input` handlers; `hx-trigger="keyup"` without `delay:…ms changed` | | Warning |
| Large `x-data` state, `x-html` of big fragments, widget re-init on every swap without teardown | | Warning |
| Removed `hx-swap` target narrowing (now swapping whole page/section) | | Warning |
| Measured: > 3 s networkidle locally, > 2 MB transferred, repeating request < 5 s, order-of-magnitude slower than base | Playwright timing + request log + node count | Warning; Blocker if order of magnitude vs base |

## 4. Security surface

| Signal | Verify | Severity |
|---|---|---|
| REMOVED permission/role conditional with block still rendered | Who can now see/click it? Backend still enforces? Even if yes: leaks existence, generates 403s | Blocker |
| New `x-html`, `innerHTML`, `|safe`, `{!! !!}`, `dangerouslySetInnerHTML`, `v-html` | Is the content user-provided? | Blocker if yes |
| New inline `<script>`/`onclick` under a CSP | Check CSP header/meta | Blocker if CSP blocks it |
| `target="_blank"` without `rel="noopener noreferrer"` | | Warning |
| Secrets, internal hostnames, debug data, other users' data newly in markup | | Blocker |
| Removed `autocomplete="off"`/`new-password` on sensitive fields | | Warning |
| Removed CSRF token (§1) | | Blocker |
| New external asset from an untrusted CDN without SRI | | Warning |

## 5. Accessibility

| Signal | Verify | Severity |
|---|---|---|
| Input lost `<label for>`/`aria-label`/`aria-labelledby` (placeholder only) | | Warning |
| `<button>`/`<a>` → `<div>`/`<span>` with click handler | Not focusable/keyboard-operable/announced | Warning (Blocker if primary action) |
| `<img>` lost `alt`; decorative image without `alt=""` | | Warning |
| `outline: none` / `outline: 0` without `:focus-visible` replacement | | Warning |
| State shown by color only (error red, active green) | Icon/text alternative? | Warning |
| Contrast drop (light gray text, text on image) | Compute ratio; 4.5:1 body, 3:1 large | Warning |
| Heading order broken, `<h1>` removed, landmarks removed | | Warning |
| Touch target < 44×44 px | | Warning |
| Modal without focus trap, `Escape`, `aria-modal`, focus return | | Warning |
| Motion without `prefers-reduced-motion` guard | | Warning |
| Text-entry control `font-size` < 16px (CSS class or inline `style=`) | iOS zooms on focus | Warning |
| Removed `aria-live`/status region for async results | | Warning |
| Removed skip link, `lang`, `tabindex` order changes, positive `tabindex` added | | Warning |

## 6. Responsive / layout

| Signal | Verify | Severity |
|---|---|---|
| Removed/changed media queries or responsive utility classes | Check at 360, 768, 1280 px | Warning; Blocker if controls unreachable |
| Fixed pixel widths/heights replacing fluid ones | | Warning |
| `overflow: hidden` that clips content or focus rings | | Warning |
| `100vh` on mobile (address bar), removed safe-area padding | | Warning |
| z-index changes burying modals/toasts/dropdowns | | Warning |
| Long strings without `overflow-wrap`/truncation; RTL regressions | | Warning |
| Print stylesheet removed where printing matters (invoices, tickets) | | Warning |

## 7. Behavioral semantics hidden in markup

| Signal | Verify | Severity |
|---|---|---|
| Default changed: `checked`, `selected`, default option, prefilled value | Especially consent/marketing opt-in (legal), destructive defaults | Blocker for consent/legal/destructive; Warning otherwise |
| Removed client validation (`required`, `pattern`, `min`, `max`, `maxlength`, `step`) | Does the backend validate too? If not: bad data accepted | Blocker if backend trusts client; Warning otherwise (ugly server errors) |
| Changed `autocomplete`, `inputmode`, `type` affecting mobile keyboards/autofill | | Warning |
| Copy changes altering meaning: legal/consent/privacy text, pricing/currency/units, destructive-action wording ("Delete" → "Archive" when it still deletes), button label no longer describing the action, error text now misleading | | Blocker for legal/pricing/destructive; Warning otherwise |
| Changed `step`/`min` on money/quantity inputs | | Warning |
| Removed `disabled`/`readonly` making an uneditable field editable | Does the backend ignore it? | Blocker if backend persists it |
| Changed `name` on radio groups so options no longer group | | Blocker |

## 8. htmx / Alpine / JS wiring

| Signal | Verify | Severity |
|---|---|---|
| `hx-target`/`hx-swap-oob` id no longer exists | htmx errors, nothing swaps | Blocker |
| Alpine root (`x-data`) now inside an htmx swap target, or `hx-swap="outerHTML"` on it | Reactivity dies after first swap | Blocker |
| `x-cloak` removed on `x-show` content | Flash of hidden content | Warning |
| `tojson`/JSON inside double-quoted attribute | Breaks attribute | Blocker |
| `$refs`/`getElementById`/`querySelector` target renamed | grep JS for the old selector | Blocker |
| Script that initialises widgets no longer re-runs after swap (`htmx:afterSwap` hook removed) | | Blocker |
| Removed `hx-indicator`, `hx-disabled-elt` (double submit) | | Warning |
| App-wide `htmx:responseError`/`htmx:sendError`/`htmx:timeout` handling removed, or the project has no such handler anywhere (grep the JS and templates) while the diff adds htmx/boosted UI | failed requests look like nothing happened | Warning (Blocker if the diff removed an existing handler) |
| `hx-boost`/`hx-push-url` changes altering history/back behavior | | Warning |
| Event names changed (`$dispatch('x')`, `htmx.trigger`, custom events) | grep listeners | Blocker |
| Form now submitted via JS `fetch` instead of native/htmx: CSRF header, redirects, error display handled? | | Blocker if not |

## 9. Tests

| Signal | Verify | Severity |
|---|---|---|
| Test diff: deleted assertions, `skip`/`xfail`/`only`/`.skip`, loosened matchers, changed expected values, selector changed to match new UI without checking the behavior | Read every test hunk in the diff | Blocker ("tests weakened") |
| Selector/test-id removed from markup, test not updated | Will fail; must be updated by engineer, not weakened | Warning |
| New UI with no test coverage where sibling features have tests | | Note |

## 10. Scope (designer domain boundary)

| Signal | Verify | Severity |
|---|---|---|
| Any route/controller/handler/view function edited | Diff hunk | Needs engineer (Blocker if it removes validation/auth) |
| Model, schema, serializer, form class, migration edited | | Needs engineer |
| Service/business logic, background job, email sending edited | | Needs engineer |
| Config, env, feature flags, CI, Docker, infra edited | | Needs engineer |
| Dependency manifest (`package.json`, `pyproject.toml`, `requirements`, lockfiles) changed | | Needs engineer |
| Generated/vendored files or lockfiles with large diffs | | Needs engineer |

## 11. Assets / build

| Signal | Verify | Severity |
|---|---|---|
| New CSS/JS file not linked from layout/bundle entry | grep for the filename | Blocker |
| Tailwind/utility classes built dynamically (`bg-${color}-500`, string concatenation) | Purged at build → unstyled in prod | Blocker |
| Renamed/moved static file still referenced elsewhere | grep old path | Blocker |
| Static path hard-coded instead of `url_for('static')`/asset helper | Breaks with CDN/hash | Warning |
| New font files/CDN without `font-display` | | Warning |
| Source maps, `.DS_Store`, design exports, huge binaries committed | | Warning |

## 12. Content / i18n / SEO / analytics

| Signal | Verify | Severity |
|---|---|---|
| Translated string replaced with hard-coded text, or i18n key removed | grep locale files | Warning |
| `<title>`, `<h1>`, meta description, canonical, Open Graph removed/changed | | Warning |
| `data-track`/analytics attributes, event names removed | grep analytics code | Warning |
| Links to help/legal/privacy/terms removed | Often legally required in footer/checkout | Blocker if legal |
| Placeholder/lorem text left in | | Warning |

## 13. Shared components

| Signal | Verify | Severity |
|---|---|---|
| Changed partial/layout/macro/component/global CSS | grep all consumers; review each page for the §1–§8 effects | Severity of the worst consumer effect |
| Macro/component signature changed (params, slots) | Every call site updated? | Blocker if not |
| Global CSS selector change (`button {}`, `.btn {}`, `input {}`) | Affects pages not in the diff | Warning; Blocker if it hides/disables controls |

## 14. Non-browser templates

| Signal | Verify | Severity |
|---|---|---|
| Email templates: external CSS, `<script>`, modern CSS, missing plain-text alt | Email clients will not render | Blocker |
| PDF/print templates: web-only features, page breaks | | Warning |
| Templates rendered by background jobs with a different context | Variables available there? | Blocker if not |
