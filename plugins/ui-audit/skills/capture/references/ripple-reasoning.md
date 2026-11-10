# Ripple reasoning

`dep_hash.py` only knows what the manifest says. Ripple reasoning finds screens a change can reach that the manifest does not list. Run it for every file in `shared_changed` and every changed file in `unmapped_changed_files`, plus any changed file whose kind is in the table. The output is a list of extra screens, each with a one-line reason; record the reasons in the manifest `ripple_notes`.

## What to ask per kind of change

| Change | Reach | How to check |
|---|---|---|
| Global CSS, utility classes, resets | Every screen that uses the touched selectors | `rg` the selector or class in templates and components; the screens using them are affected even if their deps lack the file. Selector like `.card + .card` or `main` reaches everything with that markup. |
| Design tokens (colors, spacing, type scale, CSS variables) | Every screen that references the variable | `rg` the variable; token changes in a theme file usually mean all screens |
| Layout/base template, root component, app shell | All screens it wraps | Read which routes extend/use it |
| Shared component or partial | Screens that render it | `rg` its name/import and map files to screens, including components that wrap it |
| Media queries or breakpoints | The affected viewport only | Note which viewport; re-capture only that one plus the neighbouring breakpoint |
| `z-index`, `position`, stacking contexts, overflow | Screens with overlays, sticky headers, dropdowns, modals | Capture the open-menu/modal states, not only defaults |
| Fonts, font sizes, line height, `@font-face` | Everything with text | Treat as all-screens; check long-text screens for wrapping |
| i18n strings, text length, RTL | Screens that render the keys; narrow layouts, buttons, tables | Capture the longest-language or RTL variant if configured |
| Global JS, polyfills, event listeners, analytics/overlay widgets | Screens where the script runs; any page with injected UI (banners, chat) | Treat as all-screens for interactive states |
| Dependency or build config upgrades (CSS framework, component library version) | All screens | Full sweep |
| Images/icons/SVG sprites | Screens referencing the asset | `rg` the filename |
| Server-side data or seed changes | Screens showing that data | Capture screens bound to the touched model |

When unsure whether a screen is reached, include it: a no-change result is cheap (the diff drops it), a miss defeats the audit.

## Recording

For every ripple decision append to `manifest.ripple_notes`: `file`, `reason`, `added` (sha), `widen` (`all-screens`, `listed`, `none`). When the same file changes again, reuse the note instead of re-reasoning unless the change kind differs (a color tweak versus a selector rewrite). If a shared file was missing from `shared`, add it with its dependents so `dep_hash.py` catches it next time.

## When to widen to a full sweep

Do a full sweep (all screens, all viewports in config) when: the user asks; the first audit of a repo; a framework/CSS-library/design-token/root-layout/global-font change; `unmapped_changed_files` is large or includes the router or app entry; the manifest is older than the repo's recent restructuring (many files in deps no longer exist); or an unexpected unintended change appears on a screen outside the predicted set (widen once, then continue incrementally). Say so in the report so reviewers know why the audit is larger.

Reflect the reasoning in classification: a screen whose files the diff did not touch but that changed visually is `unintended` and goes first in the report.
