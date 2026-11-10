---
name: demo-video-webapp
description: Record just the screen-demo beats for a web app — silent, per-feature screen recordings with no AI presenter and no voice-over, cut into clean beat-NN.mp4 clips. Automates writing the flows, screen recording (Playwright), client review/trims, and splitting into per-beat clips, walking the user through the few manual parts one step at a time. Use when the user wants raw demo footage or beat clips for a web app without narration. For a full launch video with an AI presenter and voice-over use launch-video-webapp instead. For Android apps use demo-video-app.
---

# Demo video beats — web app

You are recording the screen-demo beats for the web app in this repository: silent,
per-feature clips only — no AI presenter, no voice-over, no assembled final video. The
user may be non-technical. You do everything that can be done from the terminal; the user
does only what needs a human (credentials, reviewing the take) — and always one thing at
a time.

Read the repo before anything else: routes, templates/pages, README, how the app is
started locally, onboarding flow.

## The one-step rule (most important)

The user must never be asked to do more than one thing in a single message.

- Each of your messages ends with exactly one action for the user, in plain language,
  then "Tell me when that's done". Then stop and wait.
- Verify their step with a command before moving on. Don't trust "done" on its own.
- Never present a to-do list. No "first… then…". If a phase has several manual steps,
  that is several messages.
- No jargon without a one-phrase gloss. Never show commands or code to the user unless
  they ask; run them yourself and report the outcome in a sentence.
- Do everything you can yourself. Starting the app locally, writing the flows,
  recording — all yours.

## Files

    video/script.md          the shot list (one line per beat, doubles as the flow spec)
    video/beats.json         parsed script (generated)
    video/flows/beat-NN.py   Playwright flows, one per beat (you write)
    video/recordings/        full.mp4 (the whole take) + beat-NN.mp4 (silent, cut from it)
    video/marks.json         each beat's start time in full.mp4 (generated)
    video/review.json        the client's trims/notes on the take (generated)
    video/beats_review.json  the client's per-beat sign-off (generated)
    video/progress.md        your checklist — update after every completed step

Scripts live in the sibling `launch-video-webapp` skill's `scripts/` folder (run with the
repo as working directory): `parse_script.py`, `record_web.py`, `review.py`,
`apply_crops.py`, `split_beats.py`, `review_beats.py`. Read their docstrings if unsure.
The output clips have no audio track — nothing here writes voice-over or avatar files.

## Resuming

If `video/progress.md` exists, read it and continue from the first unchecked item.
Don't re-ask things already answered there. Otherwise create it from the phase list below.

## Phase 0 — Check the tools

Run `bash <launch-video-setup skill dir>/scripts/check.sh webapp` (the setup skill is a
sibling of `launch-video-webapp`; if it isn't installed, check `ffmpeg`, `python3 -c
"import PIL, playwright"` yourself — the ElevenLabs key isn't needed here). If anything is
MISSING, stop and give the user one action: run `/launch-video-setup`. Don't continue
until the check passes.

## Phase 1 — Plan the beats

1. Learn the app from the repo. Identify the 2–4 things a first-time viewer must see.
2. Write `video/script.md` following `assets/script-template.md`: a header, then one
   `## N. Title (demo)` section per beat, in order — no avatar sections, this skill only
   produces raw footage. One short line per beat describing what happens on screen; it's
   the spec for the flow file you write next, not spoken text. Set `Format: vertical`
   (phone-sized browser) unless the product is desktop-only, then `Format: landscape`.
   Set `Base URL:` to where the app will run locally.
3. Run `python3 <launch-video-webapp skill dir>/scripts/parse_script.py video` to validate.

## Phase 2 — Record the demo beats

All yours, no user actions unless something needs credentials you can't find. Pace the
flows for a human watching for the first time.

1. Read `<launch-video-webapp skill dir>/references/playwright-cheatsheet.md`.
2. Start the app locally in the background (uvicorn / npm run dev / docker compose — the
   repo tells you) with whatever database, Redis or `.env` it needs, and confirm the
   `Base URL` answers. If a value is needed that isn't in the repo (an API key, a test
   login), that is a single user action: "To record I need a test account to sign in
   with. What email/phone and password should I use? (Not a real customer's.)"
3. Seed the data each beat needs (fixtures, a debug endpoint, direct DB inserts) so the
   screens aren't empty. Fictional names only.
4. Write `video/flows/beat-NN.py` for every beat, in order, from the line in `script.md`
   (pace ~2 s per action, type with `press_sequentially`). Then record the whole demo in
   one pass: `python3 <launch-video-webapp skill dir>/scripts/record_web.py video`. It
   runs every beat's flow back-to-back in one continuous browser page, and writes
   `video/recordings/full.mp4` plus `video/marks.json` (each beat's start time in the
   take). It does **not** split into per-beat clips yet — that happens after the client
   reviews the take, in Phase 2.5. If a beat's flow fails, look at the
   `<beat-id>-error.png` screenshot it saves, fix the selector, and re-run the same
   command (it re-records the whole take, which is short).

## Phase 2.5 — Review and split

The client watches the full take and either sends back edits or marks it ready — before
it's split into beats, so a re-record never wastes a split.

1. Run `python3 <launch-video-webapp skill dir>/scripts/review.py video`. It opens a
   browser page with the take on a timeline and blocks until the client submits:
   "Recording's ready to review — a page just opened in your browser. Mark anything too
   long, leave me notes where you want something changed, then send it back or mark it
   ready." When the command returns, `video/review.json` has their trims and notes.
2. If it's empty (`review.json` has no trims or notes, action "ready"): move on to step 4.
3. Otherwise, use `video/marks.json` to find which beat's time range each trim or note
   falls in (a beat runs from its own start mark to the next beat's start mark, or the end
   of the take for the last one), then act on it:
   - a note → do what it asks in that beat's flow (a different click, a longer pause to
     read something, a different screen, etc.).
   - a trim window that lines up with a `pause(...)` call (or a slow/redundant step) in
     that beat's flow → shorten or remove it there.
   - a trim window that *doesn't* line up with anything the flow controls — real page-load,
     network, or animation latency — run `python3 <launch-video-webapp skill dir>/scripts/
     apply_crops.py video` instead; it removes exactly that window from
     `video/recordings/full.mp4` and shifts `video/marks.json` to match. If unsure which
     case you're in, `ffmpeg -ss <t> -frames:v 1 out.png` a frame or two around the window
     to see what's actually happening on screen before deciding.
   If you edited any flow, re-run `record_web.py video` for a fresh take. Either way, go
   back to step 1 so the client can confirm the result. Repeat until the client marks it
   ready.
4. Run `python3 <launch-video-webapp skill dir>/scripts/split_beats.py video` to cut
   `video/recordings/beat-NN.mp4` from the approved take.

## Phase 2.6 — Review the split beats

One more look, now that each beat is its own clip — catches anything that only shows up
once a beat is isolated (an awkward start/end frame, a beat that reads wrong on its own).

1. Run `python3 <launch-video-webapp skill dir>/scripts/review_beats.py video`. It opens
   a browser page listing every beat clip: "The beats are split out — a page just opened
   in your browser. Watch each one, tick 'Looks good' or leave a note, then send it back
   or mark them all good." When it returns, `video/beats_review.json` has their per-beat
   notes.
2. If `action` is "ready": you're done.
3. Otherwise, for each beat with a note, fix it the same way as a Phase 2.5 note (edit
   that beat's flow, or `apply_crops.py` for real latency, then re-record and re-split).
   Go back to step 1 to confirm. Repeat until every beat is ticked good.

## Done

The beats are ready at `video/recordings/beat-NN.mp4` — silent clips, one per feature.
Tell the user where they are. Update `progress.md` to complete.

## Tone

Warm, brief, no cheerleading. Report what happened, give the next single action.
