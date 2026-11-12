---
name: find
description: Find visual design inspiration for the app in the current repo. Works out what the app is from the code, asks a few design questions, searches Dribbble, Awwwards, Behance and other free inspiration sites, and publishes a shortlist of 6 to 8 screenshots per app page as a claude.ai Artifact where the user rates each Love / Maybe / No. Use whenever the user wants design ideas, inspiration, references, a moodboard, "something like Dribbble", a redesign direction, or "make this look better", even if they do not say "inspiration".
argument-hint: "[optional: screen or focus]"
---

# Find design inspiration

The output is one claude.ai Artifact page. It holds the brief (what the app is and what the user wants), then one section per app page with 6 to 8 candidate designs (fewer only when the search found fewer good, distinct ones, as step 4 says). The user rates each design and adds notes on the page. `/design-inspiration:plan <url>` reads those choices back later, so the page layout and its data names must match `assets/shortlist-template.html` exactly.

`$ARGUMENTS`, when given, names the screen or focus (for example "dashboard and settings" or "onboarding"). Treat it as the answer to the Scope question.

Make a work directory in the session's scratchpad: `WORK=<scratchpad>/design-inspiration-<timestamp>`, with `shots/` inside. Each search subagent writes into its own `shots/<subagent name>/` folder, so parallel workers never mix or overwrite each other's files. All screenshots, browser state and the filled page go there, never into the repo.

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
4. **Constraints and references** (multi-select, because a user can need several at once, such as keeping the brand colors and staying accessible): keep the brand colors or logo, a component library to stay within, accessibility needs, sites they already like.

If the user skips a question, use the default and mark it "(assumed)" in the brief. If the user types their own answer under "Other", put it in the brief in their own words, not paraphrased, because the plan skill and the user both read the brief later and the user's exact words carry what they meant.

## 3. Search and look

Read `references/sources.md` first. It lists the open sources (they load in a normal browser) and the gated sources (they block it), what kind of app page each suits, its domain and how to search it, the browsing rules every search subagent follows, and the patchright fallback that only the gated pass uses.

**Pick the sources per app page.** Each source in `references/sources.md`, open or gated, is marked as suiting in-app screens, landing and marketing pages, or both. For each app page, use only the sources that suit that kind of page: an in-app screen such as a dashboard, a table or settings gets the "in-app" and "both" sources, a landing or pricing page gets the "landing" and "both" sources. Landing-page galleries return marketing sites, which are poor references for an in-app screen, and searching them anyway costs a subagent and returns weak entries.

- **Search** each picked source the way its row in `references/sources.md` says: its own search URL, its own category listings, or WebSearch with its domain in `allowed_domains`. Run three or four distinct angles per source, not one: the screen type, the product type, a neighbouring screen type, each with and without the mood words (on a source browsed by category, a different listing is a different angle). One query per source returned five near-identical dense tables from one site in a real run, because one query finds one look many times over. Take at most one design per designer or product from each source. Aim for a pool of about 16 usable candidates per app page, twice the 8-card maximum, so step 4 has real choices to make; each subagent returns every usable candidate it finds, up to about 6 per source.
- **Look**: open each candidate's own page with `playwright-cli` and take an element screenshot of the design's main image into the subagent's folder as `$WORK/shots/<subagent name>/<card id>.png` (card id = `<page slug>--<short slug>`), as "Screenshots" in `references/sources.md` explains. The element alone can still carry a sticky header or popup laid over it, or be the wrong media block, so that section says how to hide those and size-check the block; only a candidate that is itself a whole live website gets a 1440 by 900 window screenshot, and nothing gets a full-page capture. A blocked page is handled as the pass below says. Then look at the image yourself: a broken image, a challenge page, a banner, a popup or site chrome, or a design plainly unrelated to the app is dropped here, and its file deleted.

Every candidate must be one design's own page that credits that one design's maker. A listing, category or search-results page is not a candidate, because the card links to it and credits its maker, and a listing has neither one design nor one maker.

**Run the search and look work in parallel Haiku subagents, in two passes.** Searching, opening pages and taking screenshots is mechanical. Haiku does it reliably for a fraction of the token cost, and running in parallel cuts the runtime. The work is split in two passes because the gated sources need patchright, a browser built to get past bot checks, and Claude Code's permission check can refuse any subagent whose brief carries it. Keeping patchright and the gated sources out of the open pass means such a refusal can only cost the gated sources, never the whole search.

**Open pass (always).** Give each `Agent` with `model: "haiku"` one app page and a group of two or three of that page's picked open sources, and spawn them all in one message. One subagent per source was tried and produced about 20 subagents for two app pages, most returning one to four weak entries: grouping keeps the count small, which cuts cost and runtime, and the picking above keeps every source relevant. Name each subagent `<page slug>-<n>` and give it:
- from `references/sources.md`: the "How to use a source" rules, the table rows of its own sources only (domain, how to search, notes), and the "Browsing (every subagent)" section, and nothing else from that file;
- the app summary, the app page and the mood words;
- its name, used as its playwright session (`-s=<subagent name>`) and its screenshot folder (`$WORK/shots/<subagent name>/`, absolute path);
- the job: search each source with three or four distinct angles, open, screenshot the design's image element, then look at each screenshot (Read it) and keep the candidate only if the picture is the design itself and readable (a banner, a login or cookie wall, a popup, an empty state or mostly site chrome means retake it once by the source's rule, else drop it), record title / designer / design page URL / source site, keep at most one design per designer or product per source, return every usable candidate up to about 6 per source, and drop broken, off-topic or listing-page results. Its own look is the first check and the session's is the second, because every bad picture it returns takes a slot in the pool and hides how thin the pool is. It deletes every screenshot it drops and returns every one it keeps, so its folder matches its returned list;
- this rule, word for word: "If a page shows a bot check, a challenge, a 403 or an empty body, record it as blocked and move on. Never try to get past it by any means.";
- the return format: a JSON list `[{"id","title","designer","url","site","shot"}]` with absolute screenshot paths, plus one line per source naming the searches it ran, any blocked pages, and whether the source gave nothing usable.

**Gated pass (after the open pass has returned, and only where it fits).** When a gated source suits an app page, spawn one more Haiku subagent for that app page, named `<page slug>-gated`, covering the gated sources that suit it; spawn the gated subagents for all app pages in one message. Give it the same items as an open-pass subagent, except: the table rows of its gated sources, the "Browsing (every subagent)" section plus the "Patchright fallback (gated pass only)" section, and instead of the rule above: "If a page is blocked in playwright-cli, make one patchright attempt as the fallback section says. If the permission check refuses patchright, do not retry or reword it and do not try any other route: record every page not loaded as refused." Its return format adds, per source, any page skipped because patchright was refused.

If the permission check refuses a gated-pass spawn, or the patchright command inside it: do not retry, do not reword the brief, and do not do that work another way, in this session or in another subagent. Skip the gated sources for that app page, note them for the final reply, and carry on with what the open pass returned. The gated pass is optional by nature: a refusal there never stops the run.

**Refused spawn.** Whenever the permission check refuses an `Agent` spawn, never retry it, reword it to get it accepted, or do the refused work in this session instead. A refusal is the user's settings speaking, not a wording problem. A refused gated-pass spawn is handled above. A refused open-pass spawn is unexpected, since its brief has no bypass: skip that group and note its sources as not searched for that app page. If no open-pass subagent ran at all, stop: tell the user exactly which spawns were refused and that nothing was searched, and publish nothing, because an empty page would look like a finished search.

**Waiting.** The search subagents run in the background, in every round (open pass, gated pass and extra round). After spawning them, and after any message to one of them, wait for every completion notification of that round before going on: do not spawn the next round, count the pool or shortlist in the meantime, and do not poll with sleep loops, because a pool counted early is missing whatever is still coming in.

Keep the judgment work in this session: choosing the final designs, writing the fit notes and building the page all decide the quality the user sees.

**Reliability guard.** Build the shortlist from whatever both passes returned. Look at every returned screenshot first (Read it), then count. A candidate is **usable** only when its `shot` file exists, its `url` is one design's own page on the named site, and the picture is on-topic for this app page, clean (the design itself, not a challenge page, banner, popup or site chrome), readable, and not a near-duplicate of another candidate in the pool. Drop the rest. Count each app page's usable candidates, never the number returned: in a real run only about 40% of the returned candidates were usable once viewed, so the returned count hid a thin pool. Go through every picked source for every app page, in both passes, not only the subagents that came back empty.

**Extra round (once per app page, then stop).** An app page gets one extra round when its usable count is below about 16, or when any picked source ended with no usable candidate, because its subagent returned nothing for it or only broken entries. A source silently left empty, or a pool too small to choose from, narrows the shortlist without the user knowing, so check every app page and every source, not only the first one you notice.
- Open sources: take the open sources that ended empty and, when the pool is short, every open source that suits the page (those searched and any not yet searched). Group them two or three per Haiku subagent, as in the open pass, named `<page slug>-extra-<n>`, each with the open-pass brief above plus the searches already run on its sources, and tell it to use only new angles. Spawn the extra subagents for all app pages in one message.
- A gated source that ended empty gets its one re-run by you in this session, under the gated-pass rules.
- A source reported as blocked or refused, or not searched because its spawn was refused, is not empty: do not re-run it.

Check what the extra round returns the same way, then stop searching for that app page, whatever the count: a second extra round mostly returns the same designs again. A source still empty after the extra round is named in the final reply. If the `Agent` tool is unavailable, do the work of both passes and the extra round yourself, one source at a time, under the same rules.

When the user picked more than one app page, run steps 3 and 4 once per app page, with queries specific to that page. A settings screen and a landing page need different references.

## 4. Shortlist

For each app page, pick 6 to 8 designs, each a distinct direction the user can choose between. The user asked for good candidates to choose from, and a row of near-copies or filler passes every check yet still looks bad:
- **Drop near-duplicates.** Two designs with the same layout idea, the same density and the same palette family are one direction: keep the better one.
- **Spread across source sites** where the pool allows, so no single site's house style fills the row.
- **Never pad the count.** A design that is off-topic for this app page, or weak, stays out even when that leaves fewer than 6.
- **Fewer honest cards beat a full row of filler.** If fewer than 6 good, distinct designs are left after the extra round, publish the ones you have and say so in the final reply (step 6).

For each chosen design, write:
- **title**: the design's name as the site shows it;
- **designer**: the person or studio credited on the page. Curated galleries of shipped products (SaaSUI, SaaS Landing Page, Siteinspire and the like) often name no designer: credit the product or company as the maker, and name the gallery as the source site, so every card still says who made it and where it was found;
- **source site and link**: the design's own page;
- **why it fits**: one or two sentences tying it to this app and the user's answers;
- **what to take**: the concrete part worth borrowing (layout, type pairing, color, a component, density).

With several app pages, every app page gets its own section with its own cards (6 to 8, or fewer as above) and its own overall note box, all in the same Artifact. Card ids are unique across the whole page, so prefix them with the page slug.

## 5. Publish

1. Copy `assets/shortlist-template.html` to `$WORK/index.html` and copy each chosen screenshot to `$WORK/media/<card id>.png`.
2. Fill it as its header comment explains. Put the app summary and every question with its answer in `<header id="brief">`, because the plan skill reads the brief from there. Repeat the `<section class="pg">` block per app page and the `<article class="card">` block per design. Set `data-page`, `data-id`, the `img src` (`media/<card id>.png`) and the source links. Escape `&`, `<`, `>` and quotes in inserted text. Leave no `{{...}}` placeholder.
3. Load the `artifact-design` skill and follow its page contract. Also load the `artifact-capabilities` skill, because the publish call below passes `capabilities`, and the Artifact tool requires that skill before any `capabilities` publish.
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

Reply with the link and one line: "Rate the cards (Love / Maybe / No, notes optional), then run `/design-inspiration:plan <url>`." Then name, by source and app page: every source skipped because it was blocked; every gated source skipped because the permission check refused the gated pass or patchright (and that the user can allow `uv run --with patchright` in their permission settings and run again); every open source not searched because its spawn was refused; and every source still empty after the extra round. For each app page with fewer than 6 cards, say how many it has, why (for example the suitable sources had few designs for that screen, or the rest were near-copies or off-topic), and what would widen it: the gated sources if they were skipped, or a broader scope such as a neighbouring screen type. The user judges the shortlist by what it covers, so they need to know what was left out. Artifacts are private by default.
