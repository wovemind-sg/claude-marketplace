# design-inspiration

Finds visual design references for the app in your repo and helps you choose between them.

`/design-inspiration:find` works out what your app is from the code and asks you a few design questions. It then searches Dribbble, Awwwards, Behance and other free inspiration sites, and publishes a shortlist of 6 to 8 screenshots per app page as a private claude.ai Artifact. On that page you rate each design Love / Maybe / No and add notes. `/design-inspiration:plan` then reads your choices from the page and plans how to apply them.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
claude plugin install design-inspiration@wovemind
```

This also installs `plan-tools`, which the plan skill depends on.

## Usage of `find`

```
/design-inspiration:find
/design-inspiration:find dashboard and settings
```

The optional argument names the screens or the focus. Without it, the skill asks.

What happens:
1. It reads the repo (README, routes and pages, styles and design tokens, platform) and never asks what the app is.
2. It asks one round of up to four questions: scope, emphasis and priorities, mood and style, constraints and references. A question the repo already answers is skipped.
3. It searches the sources in `skills/find/references/sources.md` that suit each app page (in-app screen or landing page) and screenshots each candidate. This runs in a few parallel Haiku subagents, each covering a small group of sources, to keep cost and runtime down, and the main session checks every result.
4. It picks 6 to 8 distinct designs per app page. Each card has a "why it fits" and a "what to take" note, a designer credit and a link to the original.
5. It publishes the shortlist as an Artifact. When you asked for several app pages, each one gets its own section.

Rate the cards on the page. Ratings and notes are saved on the page and kept across reloads. Only you and editors can change them.

## Planning from the shortlist

```
/design-inspiration:plan https://claude.ai/code/artifact/<id>
/design-inspiration:plan https://claude.ai/code/artifact/<id> --model sonnet
/design-inspiration:plan
```

| Argument | Default | Meaning |
|---|---|---|
| artifact URL | the newest "<app> Design Shortlist" artifact for this repo (asks when several match) | the shortlist you rated |
| `--model <name>` | asked, with Opus first | model of the planning subagent |

What happens:
1. It reads the brief, every app-page section, and your ratings and notes from the page.
2. If no design is rated Love, it stops and asks you to rate first. An app page with no Love card is left out of the plan, and the reply names it.
3. It fetches the screenshots of the Love cards and of the Maybe cards you wrote a note on.
4. It spawns one planning subagent with the model you chose. The subagent studies the designs (palette, type, spacing, layout, components), reads your app's UI code, and writes one implementation plan for all the rated pages, following `/plan-tools:plan-helper`. It recreates the style in your own code and never reuses the source's images, illustrations or logos. Any design question it cannot settle comes back to you.

Output: the plan, printed in chat. Nothing is written to the repo, and nothing is implemented. To build it, hand the plan to `/plan-tools:plan-implement-complete` or implement it yourself.

## Requirements

- `playwright-cli` (the Playwright CLI) for opening and screenshotting pages.
- `uv`, for the patchright fallback on sites that block automated browsers (Behance, Land-book, Lapa Ninja). Patchright runs on demand through `uv run --with patchright`, and nothing is installed for good. Claude Code's auto mode may refuse it as bot-check circumvention. Allow `uv run --with patchright` in your permission settings if you want those sites, otherwise they are skipped.
- The claude.ai Artifact tool, to publish the shortlist. Without it, the skill leaves the page as a local HTML file, and ratings do not work there.
- `plan-tools`, installed automatically.

## Example

In a repo for a small invoicing web app:

```
> /design-inspiration:find dashboard and invoice editor
```

The skill reads the repo and learns it is a FastAPI + htmx invoicing app with a Tailwind palette. It asks about emphasis ("fast data entry"), mood ("calm, professional") and constraints ("keep the green brand color"). It searches Dribbble, Awwwards, Collect UI, SaaS Landing Page and the other sources for "invoicing dashboard" and "invoice editor form". Then it publishes one page with two sections, Dashboard and Invoice editor, each holding 7 cards. You love two dashboards, mark one editor as Maybe with the note "only the line-item table", and then run `/design-inspiration:plan <url>`.
