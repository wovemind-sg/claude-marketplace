# design-inspiration

Finds visual design references for the app in your repo and helps you choose between them.

`/design-inspiration:find` works out what your app is from the code and asks you a few design questions. It then searches Dribbble, Awwwards, Behance and other free inspiration sites. If you choose, it first shows you pairs of designs to learn your taste and runs one more search aimed at it. It then publishes a shortlist of 6 to 8 screenshots per app page as a private claude.ai Artifact. On that page you rate each design Love / Maybe / No and add notes. `/design-inspiration:mockup` can then build a responsive mockup of your pages in the chosen look, which you comment on and have revised. `/design-inspiration:plan` reads your choices and plans how to apply them.

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
2. It asks scope, emphasis and priorities, mood and style, constraints and references, and whether to compare pairs first or go straight to a shortlist. A question the repo already answers is skipped.
3. It searches the sources in `skills/find/references/sources.md` that suit each app page (in-app screen or landing page), with several search angles per source and at most one design per designer, and screenshots just the design image of each candidate (no site header or sidebar). For in-app screens the sources are Dribbble, SaaSUI, the Kombai gallery, Collect UI and Behance; for landing pages, Awwwards, One Page Love, Recent.design, SaaS Landing Page, Siteinspire, Land-book, Lapa Ninja and Behance. It aims for about 16 usable candidates per app page, counted after looking at each screenshot, and runs one extra round with new angles when the pool is short. This runs in a few parallel Haiku subagents, each covering a small group of sources, to keep cost and runtime down, and the main session checks every result. Behance, Land-book and Lapa Ninja refuse a headless browser, so the subagent that covers them opens a visible browser window while it works. A page that still shows a bot check is skipped, never worked around, and the final reply names it.
4. If you chose to compare pairs, it publishes a page showing two designs per app page that differ on one trait, such as density or palette. On the page you pick the better one (or Neither) and write what you like and dislike in each, then choose Continue in the terminal. It builds a taste profile per app page from your answers and shows new pairs until it has learned enough, at most 10 pairs per app page; "Build the shortlist now" stops early. Pressing "Love it, find more like this" on a design ends the pairs for that app page. Then it runs one targeted search per app page: aimed at your taste, or, after a Love, at designs close to the loved one, including up to 3 by its maker.
5. It picks 6 to 8 distinct designs per app page, dropping near-copies and spreading across sites. It never pads the row with off-topic or weak designs: if fewer than 6 good ones turn up, it publishes those and tells you why and what would widen the search. Each card has a "why it fits" and a "what to take" note, a designer credit and a link to the original. After the pairs, the cards are picked by fit to your taste, and a loved design is the first card.
6. It publishes the shortlist as an Artifact, at the same link as the pairs page when there was one, with your taste from the pairs in the brief. When you asked for several app pages, each one gets its own section.

Rate the cards on the page. Ratings and notes are saved on the page and kept across reloads. Only you and editors can change them.

## Mockup before planning

This step is optional. It shows you what you will get before anything is planned.

```
/design-inspiration:mockup https://claude.ai/code/artifact/<shortlist id>
/design-inspiration:mockup https://claude.ai/code/artifact/<mockup id>
/design-inspiration:mockup --model sonnet
```

| Argument | Default | Meaning |
|---|---|---|
| artifact URL | the newest "<app> Design Mockup" or "<app> Design Shortlist" artifact for this repo (asks when several match) | a shortlist to build from, or a mockup to revise |
| `--model <name>` | asked, with Opus first | model of the subagent that builds the mockup |

What happens on a shortlist:
1. It reads your ratings and notes the same way `plan` does. App pages with no Love card are left out and named.
2. It asks once: the model, and per app page "Shallow redesign" (keeps the page's structure: a table stays a table, and every section, field and control stays), "Deep redesign" (keeps its features and data, but may present them differently, such as a table turned into cards or a graph) or "Full redesign" (anything may change). Each page of the mockup lists its deliberate changes.
3. A subagent builds each app page in the look of your Love designs, with made-up sample data. It recreates the style in its own HTML and CSS and never reuses the source's images, logos or copy.
4. The skill checks every page at desktop, tablet and phone width, then publishes one Artifact titled "<app> Design Mockup": a tab per app page and a Desktop / Tablet / Phone switch.

The comment loop: comment on the mockup in claude.ai, on any tab, and send each thread to Claude (reply with "Send to Claude" or mention @claude). Then run `/design-inspiration:mockup <mockup url>`. It ties each comment to its app page (and asks you when it cannot tell), changes only what you asked, republishes at the same link, and replies to and resolves each thread. Threads you did not send to Claude are still acted on, but stay open and are listed for you. Each page also lists its "Differences from the real page": what the mockup cannot show faithfully.

When no session is watching the mockup, claude.ai shows "Claude tried to reply but couldn't. To retry, reply to the comment and send the reply to Claude" under a comment sent to Claude. The comment is still saved, and running `/design-inspiration:mockup <mockup url>` picks up every open comment.

When you are happy, run `/design-inspiration:plan <mockup url>`.

## Planning

`plan` takes either the mockup or the shortlist. Give it the mockup if you made one: it then plans to build what the mockup shows. Without a mockup it plans straight from your shortlist ratings.

```
/design-inspiration:plan https://claude.ai/code/artifact/<mockup id>
/design-inspiration:plan https://claude.ai/code/artifact/<id>
/design-inspiration:plan https://claude.ai/code/artifact/<id> --model sonnet
/design-inspiration:plan
```

| Argument | Default | Meaning |
|---|---|---|
| artifact URL | the newest "<app> Design Mockup" artifact for this repo, else the newest "<app> Design Shortlist" (asks when several match) | the mockup you accepted, or the shortlist you rated |
| `--model <name>` | asked, with Opus first | model of the planning subagent |

What happens on a shortlist:
1. It reads the brief, every app-page section, and your ratings and notes from the page.
2. If no design is rated Love, it stops and asks you to rate first. An app page with no Love card is left out of the plan, and the reply names it.
3. It fetches the screenshots of the Love cards and of the Maybe cards you wrote a note on.
4. It spawns one planning subagent with the model you chose. The subagent studies the designs (palette, type, spacing, layout, components), reads your app's UI code, and writes one implementation plan for all the rated pages, following `/plan-tools:plan-helper`. It recreates the style in your own code and never reuses the source's images, illustrations or logos. Any design question it cannot settle comes back to you.

What happens on a mockup (running `plan` on it means you accept it):
1. If a comment thread on the mockup is still open, it stops, lists the open threads with their app page, and asks whether to revise the mockup first (`/design-inspiration:mockup <mockup url>`) or plan anyway.
2. It reads each app page's mockup, its mode (shallow, deep or full redesign) and its listed deliberate changes, and follows the mockup's link back to the shortlist for the brief and the credits of your Love designs.
3. It spawns one planning subagent with the model you chose. The subagent treats the mockup as the target, reads your app's UI code, and plans to build each page in your own code: it reuses your existing components and tokens where they give the same look, turns the mockup's width breakpoints into your app's media queries, and says plainly where the real result will differ from the mockup.

Output: the plan, printed in chat. Nothing is written to the repo, and nothing is implemented. To build it, hand the plan to `/plan-tools:plan-implement-complete` or implement it yourself.

## Requirements

- `playwright-cli` (the Playwright CLI) for opening and screenshotting pages.
- `python3`, for the mockup check's local server.
- The claude.ai Artifact tool, to publish the shortlist. Without it, the skill leaves the page as a local HTML file, and ratings do not work there.
- `plan-tools`, installed automatically.

## Example

In a repo for a small invoicing web app:

```
> /design-inspiration:find dashboard and invoice editor
```

The skill reads the repo and learns it is a FastAPI + htmx invoicing app with a Tailwind palette. It asks about emphasis ("fast data entry"), mood ("calm, professional") and constraints ("keep the green brand color"). It searches Dribbble, SaaSUI, the Kombai gallery and Collect UI, the sources that suit in-app screens, from several angles each ("invoicing dashboard", "invoice editor form", "billing table", and so on). You chose to compare pairs, so for three rounds you pick between two dashboards and two editors and say what you like in each, until you press "Love it" on an airy editor and the next search looks for designs close to it. Then it publishes one page with two sections, Dashboard and Invoice editor, each holding 7 cards. You love two dashboards, mark one editor as Maybe with the note "only the line-item table", and then run `/design-inspiration:plan <url>`.
