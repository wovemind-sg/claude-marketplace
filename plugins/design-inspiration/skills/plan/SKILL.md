---
name: plan
description: Plan how to apply the designs the user chose on a design-inspiration shortlist, or how to build the mockup they accepted. Reads the Love / Maybe / No ratings and notes from the shortlist Artifact that /design-inspiration:find published, asks which model should plan, and spawns one subagent that writes an implementation plan restyling the app's pages after the chosen designs; from a mockup made by /design-inspiration:mockup it plans to build what the mockup shows, after checking no comment thread is still open. Use whenever the user has rated a shortlist or finished a mockup and wants to apply it, "plan the redesign", "use the designs I picked", "I rated the cards, go", "build the mockup", or passes a shortlist or mockup Artifact link, even if they do not say "plan".
argument-hint: "[mockup or shortlist url] [--model <name>]"
---

# Plan from the shortlist or the mockup

The user rated the designs on a shortlist page made by `/design-inspiration:find`, and may have built and accepted a mockup of their pages with `/design-inspiration:mockup`. Read their choices (or the mockup), hand them to one planning subagent, and show its plan in chat. Nothing is written to the repo: the user decides what to do with the plan, for example implementing it with `/plan-tools:plan-implement-complete`.

Run from the root of the app's repo, because the planner reads that repo's UI code.

## Arguments

Parse `$ARGUMENTS`:

| Argument | Default | Meaning |
|---|---|---|
| artifact URL | found with `Artifact` `action: "list"`: the newest artifact titled "<app name> Design Mockup" for this repo's app, else the newest titled "<app name> Design Shortlist"; ask with `AskUserQuestion` when several match, and stop with a pointer to `/design-inspiration:find` when none does | the mockup or shortlist to read |
| `--model <name>` | asked (see step 1) | model for the planning subagent |

## Which input

`Artifact` `action: "read"` with the URL. A page as large as a mockup is normally not returned inline: the result names a local file it saved the page to. When it does, that saved file is the page's source for every step below, so read it once in full with `Read`. It is large, so hand the planner its path, never the pasted source. The `<title>` decides:
- ends in "Design Shortlist": plan from the shortlist, steps 1 to 6;
- ends in "Design Mockup": plan to build the mockup, steps M1 to M6 under "Plan from a mockup";
- anything else: stop and say this skill needs a shortlist or a mockup made by this plugin.

## 1. Ask for the model

Unless `--model` was given, ask with one `AskUserQuestion`: "Which model should write the plan?" Options: Opus (first, the default: planning a redesign takes judgment across many files), Sonnet (cheaper and faster). Use the answer as the `Agent` `model`.

## 2. Read the page and its choices

Do this in the session, not in a subagent. It is a few tool calls, and the planner needs the result verbatim.

1. From the HTML you already read take:
   - the brief: everything in `<header id="brief">`, meaning the app name (`h1`), the `.summary` paragraph, and each `dt`/`dd` pair (a question and the user's answer);
   - each app-page section, `section.pg[data-page]`: the slug in `data-page` and the name in its `h2`;
   - each card inside it, `article.card[data-id]`: the id in `data-id`, the title (`h3`), designer and source link (`.credit`), the "Why it fits" and "What to take" text (`.fit`), and the image path (`img src`, normally `media/<card id>.png`).
2. `ArtifactData` (load it with ToolSearch if it is deferred) `list` the `ratings` collection and the `notes` collection, following any next page until all docs are read.
   - `ratings`: doc id = card id, field `r` = `love` | `maybe` | `no`.
   - `notes`: doc id = card id for a card note, or `overall--<page slug>` for a section's overall note, field `t` = text.
3. Group everything by section: its cards with their rating and note, plus the section's overall note. A card without a rating doc is unrated. Ignore it unless it has a note.
4. A note that plainly ends mid-sentence was saved incomplete. Do not interpret it or guess the rest: ask the user for the full note with `AskUserQuestion`, quoting what was saved (in the same call as any other question still to ask), and use their answer as the note.

## 3. Check there is something to plan

- No card rated `love` anywhere: stop. Tell the user to rate at least one design Love on the page, then run this skill again. A plan without a chosen design would be guesswork.
- A section with no `love` card is left out of the plan. Name those sections in your final reply so the user knows they were skipped on purpose.

## 4. Fetch the screenshots

The planner has to see the designs, not only their titles. Fetch the images of every `love` card, and of every `maybe` card that has a note (the note says which part to take), with one `Artifact` `action: "read"` call: `url` plus `paths` listing their `img src` values. Keep the local path the result gives for each one.

## 5. Spawn the planner

Spawn one `Agent` (general-purpose) with the chosen `model`. Its brief is the only context it gets, so give it everything:

- the repo's absolute path;
- the brief from step 2, as text;
- per included section: the page name and slug, the overall note, and each `love` card and each noted `maybe` card with its title, designer, source link, rating, note, "Why it fits", "What to take" and the absolute screenshot path;
- the sections that were left out, so it does not plan for them;
- this instruction:

  > Look at each screenshot (use Read on the image path) and study the designs: palette, typography, spacing and density, layout and grid, and components. Read this app's UI code: templates or components, styles, design tokens, theme and fonts. Then write an implementation plan that restyles each app page listed after the designs chosen for it. Love cards lead. A Maybe card contributes only what its note asks for, and each note and overall note is a requirement. Follow `/plan-tools:plan-helper` (invoke it with the Skill tool) when writing and checking the plan. Recreate the style in the app's own code and stack. Never reuse the source's images, illustrations, logos or copy, because they belong to their designers. Write one plan that covers every listed page, and name per change which design it comes from. Do not edit any file. If you hit a decision the designs, notes and brief do not settle, end your run with that question as your final report (2 to 4 concrete options, your recommendation first) and wait for the answer.

When the planner returns a question instead of a plan, ask the user with `AskUserQuestion` and send the answer back to the same agent with `SendMessage`. Repeat until it returns a plan. Do not answer its questions yourself: they are design choices that belong to the user.

The planner runs in the background. Wait for its completion notification, after the spawn and after every `SendMessage` to it, before going on: do not show a plan, reply or report in the meantime, because there is no plan until it reports.

## 6. Show the plan

Print the planner's plan in chat as it came back. Then add one line naming any section that was left out for having no Love card. Stop there: do not write the plan to a file, and do not start implementing.

## Plan from a mockup

Running this skill on a mockup means the user accepts it as the target. The mockup is what they saw and approved, so the plan builds that, not a fresh reading of the shortlist.

### M1. Check for open comments

`ArtifactComments` (load it with ToolSearch if it is deferred) `action: "read"` with the mockup URL, following any cursor until all threads are read. Resolved threads are done. If any thread is still open, stop before planning: an open comment is a change the user asked for that the mockup does not show yet.

List each open thread with its app page and its text. Tie it to a page as `/design-inspiration:mockup` step 7 does: the `#page-<slug>` id at the start of `[anchored at]` names the section, and the leading heading of `[location]` must be that section's app page name or a heading inside it; without the id, the heading must belong to exactly one section. Only real headings count (a section's `h2` or an `h1` to `h3` inside it), not the same words as a link or label in another section. When the two disagree, neither is present, or the heading matches no section or several, write "page unclear" rather than guess. Then ask with one `AskUserQuestion`: "Some comments on the mockup are still open. What now?" Options:
- "Revise the mockup first" (first): stop and tell the user to run `/design-inspiration:mockup <mockup url>`, then this skill again.
- "Plan anyway": plan the mockup as it stands. The open comments are not requirements; name them in your final reply.

### M2. Ask for the model

As in step 1.

### M3. Read the mockup

From the saved file read in "Which input" take:
- the brief: `<header id="meta">`, meaning the app name (`h1`), the `.summary` paragraph, each `dt`/`dd` pair, and the shortlist URL in `data-shortlist`;
- each app page, `section.mock[data-page]`: the slug in `data-page`, the name in its `h2`, the mode in `data-mode` (`restyle` keeps the real page's structure, `redesign` changes it), each item of its `.diffs` list ("Differences from the real page"), and for a redesign each item of its `.changes` list. A redesign section made before redesigns had a `.diffs` list has none; treat that as no differences.

The planner needs the mockup's full source. When the read result names a saved file holding the full page, use that file's absolute path; otherwise write the HTML to a file in the session's scratchpad. The saved file is the served document: a doctype, `<html>`, a `<head>` with styles the publish injects and a `<body>` open tag come before the page, which starts at its `<title>`. Each app page's mockup is the `<style>` and markup inside its section's `.viewport`.

### M4. Read the shortlist for context

`Artifact` `action: "read"` with the `data-shortlist` URL, and `ArtifactData` `list` its `ratings` and `notes` as in step 2. Per app page, take the `love` cards' titles, designers and source links, and the notes. This is context only: it tells the planner where the look came from, so it can credit each design. The mockup stays the target. Do not fetch the screenshots. If the shortlist cannot be read, go on without it and say so in your final reply.

### M5. Spawn the planner

Spawn one `Agent` (general-purpose) with the chosen `model`. Its brief is the only context it gets, so give it everything:

- the repo's absolute path;
- the brief from M3, as text;
- the absolute path of the mockup's saved HTML;
- per app page: the page name and slug, its mode, its `.diffs` items, the `.changes` items for a redesign, and from M4 its Love designs (title, designer, source link) and notes;
- this instruction:

  > The mockup HTML is the target: for each app page listed, its `section.mock[data-page="<slug>"]` shows what the user approved, and the markup and `<style>` inside that section's `.viewport` are the page to match. Read it closely: palette, typography, spacing and density, layout and grid, components, and how the layout changes at each breakpoint. Read this app's UI code: templates or components, styles, design tokens, theme and fonts. Then write an implementation plan that makes each listed app page look and work like its mockup. Mode "restyle": keep the page's structure and change its look. Mode "redesign": also make every listed structural change. The `.diffs` items of a page are places where the mockup does not show the real page as it will be (often a limit of the mockup page, such as an element fixed to the screen that could not stay fixed in the preview); there, keep the real page's behaviour, not the mockup's. The mockup's breakpoints are `@container viewport (min-width: ...)` queries, because the mockup page switches widths without resizing the window; translate each one into this app's own media queries (or its framework's breakpoints) at the same widths. Reuse the app's existing components and tokens wherever they can produce the same look, rather than copying the mockup's CSS. The mockup's sample data is made up: wire the real data instead. Say plainly, per page, where the real result will differ from the mockup and why. Follow `/plan-tools:plan-helper` (invoke it with the Skill tool) when writing and checking the plan. Never reuse the source designs' images, illustrations, logos or copy, because they belong to their designers. Write one plan that covers every listed page, and name the files it changes. Do not edit any file. If you hit a decision the mockup, brief and notes do not settle, end your run with that question as your final report (2 to 4 concrete options, your recommendation first) and wait for the answer.

Relay its questions to the user and wait for its completion notification, both as in step 5.

### M6. Show the plan

Print the planner's plan in chat as it came back. Then add one line naming any open comment left out because the user chose to plan anyway, and whether the shortlist could not be read. Stop there: do not write the plan to a file, and do not start implementing.
