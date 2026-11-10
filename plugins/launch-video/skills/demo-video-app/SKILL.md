---
name: demo-video-app
description: Record just the screen-demo beats for an Android app — silent, per-feature screen recordings with no AI presenter and no voice-over, cut into clean beat-NN.mp4 clips. Automates writing the flows, screen recording (emulator + Maestro), client review/trims, and splitting into per-beat clips, walking the user through the few manual parts one step at a time. Use when the user wants raw demo footage or beat clips for an Android app without narration. For a full launch video with an AI presenter and voice-over use launch-video-app instead. For web apps use demo-video-webapp.
---

# Demo video beats — Android app

You are recording the screen-demo beats for the Android app in this repository: silent,
per-feature clips only — no AI presenter, no voice-over, no assembled final video. The
user may be non-technical. You do everything that can be done from the terminal; the user
does only what needs a human (a test login, reviewing the take) — and always one thing at
a time.

Read the repo before anything else: manifest/`applicationId`, screens, strings, README,
onboarding flow.

## The one-step rule (most important)

The user must never be asked to do more than one thing in a single message.

- Each of your messages ends with exactly one action for the user, in plain language,
  then "Tell me when that's done". Then stop and wait.
- Verify their step with a command before moving on. Don't trust "done" on its own.
- Never present a to-do list. No "first… then…". If a phase has several manual steps,
  that is several messages.
- No jargon without a one-phrase gloss. Never show commands or code to the user unless
  they ask; run them yourself and report the outcome in a sentence.
- Do everything you can yourself. Building the app, starting the emulator, writing the
  flows, recording — all yours.

## Files

    video/script.md          the shot list (one line per beat, doubles as the flow spec)
    video/beats.json         parsed script (generated)
    video/flows/beat-NN.yaml Maestro flows, one per beat (you write)
    video/recordings/        full.mp4 (the whole take) + beat-NN.mp4 (silent, cut from it)
    video/marks.json         each beat's start time in full.mp4 (generated)
    video/review.json        the client's trims/notes on the take (generated)
    video/progress.md        your checklist — update after every completed step

Scripts live in the sibling `launch-video-app` skill's `scripts/` folder (run with the
repo as working directory): `parse_script.py`, `record_app.sh`, `review.py`,
`apply_crops.py`, `split_beats.py`. Read their docstrings if unsure. The output clips have
no audio track — nothing here writes voice-over or avatar files.

## Resuming

If `video/progress.md` exists, read it and continue from the first unchecked item.
Don't re-ask things already answered there. Otherwise create it from the phase list below.

## Phase 0 — Check the tools

Run `bash <launch-video-setup skill dir>/scripts/check.sh app` (the setup skill is a
sibling of `launch-video-app`; if it isn't installed, check `ffmpeg`, `python3 -c "import
PIL"`, `adb` and `maestro` yourself — the ElevenLabs key isn't needed here). If anything
is MISSING, stop and give the user one action: run `/launch-video-setup`. Don't continue
until the check passes.

## Phase 1 — Plan the beats

1. Learn the app from the repo. Identify the 2–4 things a first-time viewer must see.
2. Write `video/script.md` following `assets/script-template.md`: a header, then one
   `## N. Title (demo)` section per beat, in order — no avatar sections, this skill only
   produces raw footage. One short line per beat describing what happens on screen; it's
   the spec for the flow file you write next, not spoken text. Set `Format: vertical`
   unless the app is landscape-only.
3. Run `python3 <launch-video-app skill dir>/scripts/parse_script.py video` to validate.

## Phase 2 — Record the demo beats

All yours, no user actions unless something needs a login or a real phone. Pace the flows
for a human watching for the first time.

1. Read `<launch-video-app skill dir>/references/maestro-cheatsheet.md`.
2. Build a debug APK (find the gradle module; use the wrapper). Start the emulator
   (`emulator -avd launch-video …`, or use the connected device), wait for boot, install.
3. Put the app into the state the first beat expects (fresh install, or a seeded test
   account). If a test login is required and none is in the repo, that is a single user
   action: "I need a test account to sign in with during the recording. What phone number
   / email and password should I use? (Nothing real, please.)"
4. Write `video/flows/beat-NN.yaml` for every beat, in order, from the line in
   `script.md` (pace it ~2 s per action; only beat 1's flow should `launchApp`). Then
   record the whole demo in one pass: `bash <launch-video-app skill dir>/scripts/record_app.sh
   video`. It runs every beat's flow back-to-back against the same running app while one
   screen recording captures the whole session, and writes `video/recordings/full.mp4`
   plus `video/marks.json` (each beat's start time in the take). It does **not** split
   into per-beat clips yet — that happens after the client reviews the take, in Phase 2.5.
   If a flow fails, inspect with `maestro hierarchy`, fix it, and re-run the same command
   (it re-records the whole take, which is short).

## Phase 2.5 — Review and split

The client watches the full take and either sends back edits or marks it ready — before
it's split into beats, so a re-record never wastes a split.

1. Run `python3 <launch-video-app skill dir>/scripts/review.py video`. It opens a browser
   page with the take on a timeline and blocks until the client submits: "Recording's
   ready to review — a page just opened in your browser. Mark anything too long, leave me
   notes where you want something changed, then send it back or mark it ready." When the
   command returns, `video/review.json` has their trims and notes.
2. If it's empty (`review.json` has no trims or notes, action "ready"): move on to step 4.
3. Otherwise, use `video/marks.json` to find which beat's time range each trim or note
   falls in (a beat runs from its own start mark to the next beat's start mark, or the end
   of the take for the last one), then act on it:
   - a note → do what it asks in that beat's flow (a different tap, a longer pause to read
     something, a different screen, etc.).
   - a trim window that lines up with an `extendedWaitUntil` pseudo-sleep (or a slow/
     redundant step) in that beat's flow → shorten or remove it there.
   - a trim window that *doesn't* line up with anything the flow controls — real app/OS
     animation or network latency — run `python3 <launch-video-app skill dir>/scripts/
     apply_crops.py video` instead; it removes exactly that window from
     `video/recordings/full.mp4` and shifts `video/marks.json` to match. If unsure which
     case you're in, `ffmpeg -ss <t> -frames:v 1 out.png` a frame or two around the window
     to see what's actually happening on screen before deciding.
   If you edited any flow, re-run `record_app.sh video` for a fresh take. Either way, go
   back to step 1 so the client can confirm the result. Repeat until the client marks it
   ready.
4. Run `python3 <launch-video-app skill dir>/scripts/split_beats.py video` to cut
   `video/recordings/beat-NN.mp4` from the approved take.

## Done

The beats are ready at `video/recordings/beat-NN.mp4` — silent clips, one per feature.
Tell the user where they are. Update `progress.md` to complete.

## Tone

Warm, brief, no cheerleading. Report what happened, give the next single action.
