---
name: find
description: Find visual design inspiration for the app in the current repo. Works out what the app is from the code, asks a few design questions, searches Dribbble, Awwwards, Behance and other free inspiration sites, and publishes a shortlist of 6 to 8 screenshots per app page as a claude.ai Artifact where the user rates each Love / Maybe / No. Use whenever the user wants design ideas, inspiration, references, a moodboard, "something like Dribbble", a redesign direction, or "make this look better", even if they do not say "inspiration".
argument-hint: "[optional: screen or focus]"
---

# Find design inspiration

The output is one claude.ai Artifact page. It holds the brief (what the app is and what the user wants), then one section per app page with 6 to 8 candidate designs. The user rates each design and adds notes on the page. `/design-inspiration:plan <url>` reads those choices back later, so the page layout and its data names must match `assets/shortlist-template.html` exactly.

`$ARGUMENTS`, when given, names the screen or focus (for example "dashboard and settings" or "onboarding"). Treat it as the answer to the Scope question.

Make a work directory in the session's scratchpad: `WORK=<scratchpad>/design-inspiration-<timestamp>`, with `shots/` inside. All screenshots, browser state and the filled page go there, never into the repo.

## 1. Understand the app

Work it out from the repo. Never ask the user what the app is, because the repo already says it, and a question about it wastes their one question round.

- If `graphify-out/` exists, run `/graphify` first and query it for the app's purpose, pages and UI stack. It is cheaper than reading many files.
- Read the README and any product docs.
- List the pages or screens: routes, templates, page components, navigation.
- Read the current look: CSS or Tailwind config, design tokens, theme files, the component library, fonts, logo and brand colors.
- Note the platform: web app, marketing site, iOS/Android or Capacitor, desktop.

Write a two or three sentence app summary and list the app pages by name. You need both for the queries and for the page header.

## 2. Ask

Ask in one `AskUserQuestion` call with up to 4 questions, each with up to 4 options. Drop any question the repo or `$ARGUMENTS` already answers. Note those answers as "(from the repo)" in the brief instead. The four topics:

1. **Scope**: which app pages to find inspiration for (multi-select, built from the pages you found). Default: the main screen.
2. **Emphasis and priorities**: what the design must get right, for example clarity of data, speed for frequent use, trust, delight, or conversion.
3. **Mood and style**: for example calm and minimal, bold and colorful, dark and technical, warm and friendly.
4. **Constraints and references**: keep the brand colors or logo, a component library to stay within, accessibility needs, sites they already like.

If the user skips a question, use the default and mark it "(assumed)" in the brief.

## 3. Search and look

Read `references/sources.md` first. It lists every source, its `site:` query, how to tell when a page is blocked, and the patchright fallback.

- **Search** every source in `references/sources.md` with queries built from the app type, the app page and the mood answers. Collect a wide pool, roughly 4 to 6 candidates per source and app page.
- **Look**: open each candidate's own page with `playwright-cli` and screenshot it into `$WORK/shots/<card id>.png` (card id = `<page slug>--<short slug>`). If the page is blocked, use the patchright fallback once. Then look at the image yourself. A broken image, a challenge page, or a design plainly unrelated to the app is dropped here.

**Run the search and look work in parallel Haiku subagents.** Searching, opening pages and taking screenshots is mechanical. Haiku does it reliably for a fraction of the token cost, and running the sources in parallel cuts the runtime. Spawn one `Agent` with `model: "haiku"` per source site and app page, all in one message. Give each one:
- the source's section from `references/sources.md` (query, notes, the browsing rules and the patchright snippet);
- the app summary, the app page and the mood words;
- its own playwright session name (`-s=<source>-<page>`) and the absolute `$WORK` path;
- the job: search, open, screenshot, record title / designer / design page URL / source site, and drop broken or plainly off-topic results;
- the return format: a JSON list `[{"id","title","designer","url","site","shot"}]` with absolute screenshot paths, plus one line naming any blocked pages.

Keep the judgment work in this session: choosing the final designs, writing the fit notes and building the page all decide the quality the user sees.

**Reliability guard.** Before you use a returned candidate, check that its `shot` file exists and is not a challenge page (look at it), and that its `url` is the design's own page on the named site. Drop it otherwise. If a subagent returns nothing, or only broken entries, re-run that one source once, yourself in this session. If the `Agent` tool is unavailable, do the search and look work yourself, one source at a time.

When the user picked more than one app page, run steps 3 and 4 once per app page, with queries specific to that page. A settings screen and a landing page need different references.

## 4. Shortlist

For each app page, pick 6 to 8 designs that cover distinct directions, not eight near-copies of one look. Use more than one source site where the pool allows. For each one, write:
- **title**: the design's name as the site shows it;
- **designer**: the person or studio credited on the page;
- **source site and link**: the design's own page;
- **why it fits**: one or two sentences tying it to this app and the user's answers;
- **what to take**: the concrete part worth borrowing (layout, type pairing, color, a component, density).

With several app pages, every app page gets its own section with its own 6 to 8 cards and its own overall note box, all in the same Artifact. Card ids are unique across the whole page, so prefix them with the page slug.

## 5. Publish

1. Copy `assets/shortlist-template.html` to `$WORK/index.html` and copy each chosen screenshot to `$WORK/media/<card id>.png`.
2. Fill it as its header comment explains. Put the app summary and every question with its answer in `<header id="brief">`, because the plan skill reads the brief from there. Repeat the `<section class="pg">` block per app page and the `<article class="card">` block per design. Set `data-page`, `data-id`, the `img src` (`media/<card id>.png`) and the source links. Escape `&`, `<`, `>` and quotes in inserted text. Leave no `{{...}}` placeholder.
3. Load the `artifact-design` skill and follow its page contract.
4. Call `Artifact` with:
   - `file_path`: `$WORK/index.html`;
   - `files`: `{"media/<card id>.png": "$WORK/media/<card id>.png", ...}`, one entry per screenshot;
   - `icon`: `image`;
   - `description`: one sentence naming the app and its pages;
   - `capabilities`: `{"db":{"rules":[{"path":"ratings","read":"view","write":"admin"},{"path":"notes","read":"view","write":"admin"}]},"user":{}}`.

   The page stores ratings in the `ratings` collection (doc id = card id, field `r` = `love` / `maybe` / `no`). It stores notes in `notes` (doc id = card id or `overall--<page slug>`, field `t`). Only the owner and editors can change them.
5. After publishing, run one `ArtifactData` `list` of `ratings` to confirm the store answers. An empty list is expected.

If the `Artifact` tool is unavailable, stop after filling the page (item 2 above) and tell the user where `$WORK/index.html` is, and that ratings only work on a published page.

## 6. Finish

Reply with the link and one line: "Rate the cards (Love / Maybe / No, notes optional), then run `/design-inspiration:plan <url>`." Mention any source that was blocked and skipped. Artifacts are private by default.
