---
name: plan
description: Plan how to apply the designs the user chose on a design-inspiration shortlist. Reads the Love / Maybe / No ratings and notes from the shortlist Artifact that /design-inspiration:find published, asks which model should plan, and spawns one subagent that writes an implementation plan restyling the app's pages after the chosen designs. Use whenever the user has rated a shortlist and wants to apply it, "plan the redesign", "use the designs I picked", "I rated the cards, go", or passes a shortlist Artifact link, even if they do not say "plan".
argument-hint: "[artifact url] [--model <name>]"
---

# Plan from the shortlist

The user rated the designs on a shortlist page made by `/design-inspiration:find`. Read their choices, hand them to one planning subagent, and show its plan in chat. Nothing is written to the repo: the user decides what to do with the plan, for example implementing it with `/plan-tools:plan-implement-complete`.

Run from the root of the app's repo, because the planner reads that repo's UI code.

## Arguments

Parse `$ARGUMENTS`:

| Argument | Default | Meaning |
|---|---|---|
| artifact URL | found with `Artifact` `action: "list"`: the newest artifact titled "<app name> Design Shortlist" for this repo's app; ask with `AskUserQuestion` when several match, and stop with a pointer to `/design-inspiration:find` when none does | the shortlist to read |
| `--model <name>` | asked (see step 1) | model for the planning subagent |

## 1. Ask for the model

Unless `--model` was given, ask with one `AskUserQuestion`: "Which model should write the plan?" Options: Opus (first, the default: planning a redesign takes judgment across many files), Sonnet (cheaper and faster). Use the answer as the `Agent` `model`.

## 2. Read the page and its choices

Do this in the session, not in a subagent. It is a few tool calls, and the planner needs the result verbatim.

1. `Artifact` `action: "read"` with the URL. From the HTML take:
   - the brief: everything in `<header id="brief">`, meaning the app name (`h1`), the `.summary` paragraph, and each `dt`/`dd` pair (a question and the user's answer);
   - each app-page section, `section.pg[data-page]`: the slug in `data-page` and the name in its `h2`;
   - each card inside it, `article.card[data-id]`: the id in `data-id`, the title (`h3`), designer and source link (`.credit`), the "Why it fits" and "What to take" text (`.fit`), and the image path (`img src`, normally `media/<card id>.png`).
2. `ArtifactData` (load it with ToolSearch if it is deferred) `list` the `ratings` collection and the `notes` collection, following any next page until all docs are read.
   - `ratings`: doc id = card id, field `r` = `love` | `maybe` | `no`.
   - `notes`: doc id = card id for a card note, or `overall--<page slug>` for a section's overall note, field `t` = text.
3. Group everything by section: its cards with their rating and note, plus the section's overall note. A card without a rating doc is unrated. Ignore it unless it has a note.

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

## 6. Show the plan

Print the planner's plan in chat as it came back. Then add one line naming any section that was left out for having no Love card. Stop there: do not write the plan to a file, and do not start implementing.
