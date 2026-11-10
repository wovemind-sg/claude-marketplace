---
name: launch-video-app
description: Produce a launch/promo video for an Android app — an AI presenter introduces the app, then the app is demonstrated on a phone with voice-over and captions. Automates the script, the screen recordings (emulator + Maestro), the voice-over (ElevenLabs), and the final edit (ffmpeg), and walks the user through the few manual parts one step at a time. Use whenever the user asks for a launch video, promo video, demo video, app trailer, explainer, or "video for the Play Store / social media" for an Android app, even if they don't say "AI" or "avatar". For web apps use launch-video-webapp instead.
---

# Launch video — Android app

You are producing a launch video for the Android app in this repository. The user may
be non-technical. You do everything that can be done from the terminal; the user does
only what needs a human (reviewing the script, downloading avatar clips, watching the
result) — and always one thing at a time.

Read the repo before anything else: manifest/`applicationId`, screens, strings, README,
onboarding flow. The whole point of running inside the repo is that you already know
what the app does and what the screens are called.

## The one-step rule (most important)

The user must never be asked to do more than one thing in a single message.

- Each of your messages ends with exactly one action for the user, in plain language,
  then "Tell me when that's done". Then stop and wait.
- Verify their step with a command (file exists, ffprobe shows audio, etc.) before
  moving on. Don't trust "done" on its own.
- Never present a to-do list. No "first… then…". If a phase has five manual steps, that
  is five messages.
- No jargon without a one-phrase gloss. Never show commands or code to the user unless
  they ask; run them yourself and report the outcome in a sentence.
- Do everything you can yourself. Building the app, starting the emulator, writing the
  flows, generating audio, assembling — all yours.

## Files

Everything lives in `video/` inside the repo (add it to `.gitignore` except `script.md`
and `flows/`):

```
video/script.md          the script (starts as a rough draft, worded for real once recorded)
video/beats.json         parsed script (generated)
video/flows/beat-NN.yaml Maestro flows, one per demo beat (you write)
video/recordings/        full.mp4 (the whole take) + beat-NN.mp4 (cut from it)
video/marks.json         each beat's start time in full.mp4 (generated)
video/review.json        the client's trims/notes on the take (generated)
video/voice/             voice-over mp3 + timing json
video/avatar/            avatar clips the user downloads, beat-NN.mp4
video/out/launch.mp4     the result
video/progress.md        your checklist — update after every completed step
```

Scripts in this skill's `scripts/` folder (run with the repo as working directory):
`parse_script.py`, `tts.py`, `record_app.sh`, `review.py`, `apply_crops.py`, `split_beats.py`,
`assemble.py`. Read their docstrings if unsure.

Any credential or setting this skill needs (the ElevenLabs key, or anything added later)
belongs in `~/.launch-video/`, never in this skill's own directory — a plugin update
replaces the installed skill folder wholesale, so config stored there would vanish.

## Resuming

If `video/progress.md` exists, read it and continue from the first unchecked item.
Don't re-ask things already answered there. Otherwise create it from the phase list below.

## Phase 0 — Check the tools

Run `bash <launch-video-setup skill dir>/scripts/check.sh app` (the setup skill is a
sibling of this one; if it isn't installed, check `ffmpeg`, `python3 -c "import PIL"`,
`adb`, `maestro` and `~/.launch-video/env` yourself). If anything is MISSING, stop and
give the user one action: run `/launch-video-setup`. Don't continue until the check passes.

## Phase 1 — Plan the beats

The screen recording sets each demo beat's length, not the other way around — a demo
paced for a human (digest pauses, deliberate typing) rarely lands on exactly the word
count a first-guess sentence would take to read. So plan the *content* now; the exact
wording of demo beats comes later, once you know how long each one actually runs.

1. Learn the app from the repo. Identify the 2–4 things a first-time viewer must see.
   Also note its design language — theme/colors resource files, brand colors, logo,
   primary button/accent color — you'll use it for `Background:` below so the space
   behind the phone matches the app instead of a generic default.
2. Write `video/script.md` following `assets/script-template.md`: a header, then
   `## N. Title (avatar)` / `(demo)` beats. Structure: avatar intro (the problem + what
   the app is, ≤ 25 words) → 2–4 demo beats (each one thing the viewer can watch happen)
   → avatar outro (call to action). Conversational, short sentences, no feature lists,
   present tense, one idea per beat. For each demo beat, write a first-draft sentence
   describing what happens — it doubles as the spec for the flow you write in Phase 2,
   and you'll resize it to fit the real recording in Phase 3, so don't overthink the
   wording yet.
   Set `Format: vertical` unless the app is landscape-only. Set `Voice:` to a voice from
   the user's ElevenLabs account (run `tts.py` once with no voice to list them, and
   pick a natural one; the user can change it). Set `Zoom: none` on every demo beat —
   any other value crops the recording before it's composited onto the phone frame in
   Phase 6, so it no longer fills the frame right. Set `Background:` to three hex colors
   (dark, darker, glow accent) drawn from the app's own design language from step 1 —
   never the template's generic placeholder — so the space behind the phone in Phase 6
   feels like it belongs to this app.
3. Run `parse_script.py video` to validate.

## Phase 2 — Record the demo beats

All yours, no user actions unless something needs a login or a real phone. Pace the
flows for a human watching for the first time — don't rush them to hit a word count;
Phase 3 fits the words to whatever this actually takes.

1. Read `references/maestro-cheatsheet.md`.
2. Build a debug APK (find the gradle module; use the wrapper). Start the emulator
   (`emulator -avd launch-video …`, or use the connected device), wait for boot, install.
3. Put the app into the state the first demo beat expects (fresh install, or a seeded
   test account). If a test login is required and none is in the repo, that is a single
   user action: "I need a test account to sign in with during the recording. What phone
   number / email and password should I use? (Nothing real, please.)"
4. Write `video/flows/beat-NN.yaml` for every demo beat, in order, from the draft
   sentence in `script.md` (every sentence should correspond to something visible
   happening; pace it ~2 s per action; only beat 1's flow should `launchApp`). Then
   record the whole demo in one pass: `bash <skill>/scripts/record_app.sh video`. It
   runs every beat's flow back-to-back against the same running app while one screen
   recording captures the whole session — so a splash screen and any transitions only
   ever happen once, for real — and writes `video/recordings/full.mp4` plus
   `video/marks.json` (each beat's start time in the take). It does **not** split into
   per-beat clips yet — that happens after the client reviews the take, in Phase 2.5. If
   a flow fails, inspect with `maestro hierarchy`, fix it, and re-run the same command
   (it re-records the whole take, which is short).

## Phase 2.5 — Review the take

The client watches the full take and either sends back edits or marks it ready — before
it's split into beats, so a re-record never wastes a split.

1. Run `python3 <skill>/scripts/review.py video`. It opens a browser page with the take on
   a timeline and blocks until the client submits, so there's nothing to ask them
   separately — just tell them once: "Recording's ready to review — a page just opened in
   your browser. Mark anything too long, leave me notes where you want something changed,
   then send it back or mark it ready." When the command returns, `video/review.json` has
   their trims and notes.
2. If it's empty (`review.json` has no trims or notes, action "ready"): move on to step 4.
3. Otherwise, use `video/marks.json` to find which beat's time range each trim or note
   falls in (a beat runs from its own start mark to the next beat's start mark, or the end
   of the take for the last one), then act on it:
   - a note → do what it asks in that beat's flow (a different tap, a longer pause to read
     something, a different screen, etc.).
   - a trim window that lines up with an `extendedWaitUntil` pseudo-sleep (or a slow/
     redundant step) in that beat's flow → shorten or remove it there. This is the
     root-cause fix: the footage is only slow because the flow told it to wait, so make the
     flow not wait as long.
   - a trim window that *doesn't* line up with anything the flow controls — real app/OS
     animation or network latency (`waitForAnimationToEnd` waiting out a real transition,
     for example) — there's nothing to shorten in the flow, so shortening the footage means
     cutting it. Run `python3 <skill>/scripts/apply_crops.py video` instead; it removes
     exactly that window from `video/recordings/full.mp4` and shifts `video/marks.json` to
     match. Safe at this stage: no voice-over or captions exist yet to fall out of sync. If
     unsure which case you're in, `ffmpeg -ss <t> -frames:v 1 out.png` a frame or two around
     the window to see what's actually happening on screen before deciding.
   If you edited any flow, re-run `record_app.sh video` for a fresh take (this also
   supersedes any `apply_crops.py` cuts from this round — they applied to the take you're
   replacing). Either way, go back to step 1 so the client can confirm the result. Repeat
   until the client marks it ready.
4. Run `python3 <skill>/scripts/split_beats.py video` to cut `video/recordings/beat-NN.mp4`
   from the approved take.
5. Note each demo beat's duration: `ffprobe -v error -show_entries format=duration -of
   csv=p=0 video/recordings/beat-NN.mp4`. You'll size that beat's spoken text to it next.

## Phase 3 — Write the script for real

1. For each demo beat, rewrite its sentence to *almost* fill its recording's duration —
   speech runs roughly 2.3–2.5 words/second, so target `duration × 2.3` words, a touch
   under rather than over (silence at the end reads as polish; a voice-over that outlasts
   its footage is the actual bug you're avoiding). Keep the same idea from the Phase 1
   draft — describe more or less of what's happening on screen, don't invent new visuals.
   The avatar intro/outro aren't tied to a recording; keep them close to the Phase 1
   draft unless the user wants changes.
2. Run `parse_script.py video` to validate.
3. **User action**: "I've written the script at `video/script.md`. Please open it, read
   it out loud once, and change anything that doesn't sound like you. Tell me when
   you're happy with it (or paste your changes here)." Wait. Re-parse after edits;
   iterate until they approve. Explain any parse error in one sentence and fix it
   yourself.

## Phase 4 — Voice-over

Run `python3 <skill>/scripts/tts.py video`. It writes `video/voice/beat-NN.mp3` for
every beat plus timings for captions. Because each demo beat's text was sized to its
recording in Phase 3, lengths should already be close — spot-check with `ffprobe` on a
beat or two; if a voice-over noticeably outruns or undershoots its recording, trim or
pad that beat's sentence and rerun `tts.py --only beat-NN --force` rather than
re-recording.

Optional single user action: "Want to hear the voice before we go on? Play
`video/voice/beat-01.mp3` and tell me if it's fine or you'd like a different voice."
If they want another, list 3–4 names and ask them to pick one. Rerun with `--force`.

## Phase 5 — Avatar clips (manual, guided)

Read `references/avatar-instructions.md` and follow it literally — one HeyGen/Synthesia
step per message, verify each downloaded file with `ffprobe` (must have audio), same
avatar and orientation for all clips. Print absolute paths when telling the user where
to save a file.

## Phase 6 — Assemble

Run `python3 <skill>/scripts/assemble.py video` (add `--preview` first if the machine is
slow). It composites recordings onto a phone frame — set against a gradient in the
script's `Background:` colors with a soft glow behind the phone — adds captions in the
bottom band where they can't cover the app, crossfades between scenes, and writes
`video/out/launch.mp4`. Report length and path.

**User action**: "The video is ready: `video/out/launch.mp4`. Watch it once all the way
through and tell me the first thing you'd change (or that it's good)."

## Phase 7 — Iterate

Handle one piece of feedback at a time; after each fix, re-assemble and ask them to watch
again. Map feedback to the smallest change:

- wording too long/short for the footage → trim or expand that beat's sentence in
  `script.md`, `tts.py --only beat-NN --force`, re-assemble. The recording is the anchor
  now; reach for a re-record only if the *pacing of the demo itself* is the problem (too
  rushed or too slow to follow), not just a word-count mismatch.
- can't see what's tapped → adjust the flow to pause on the tap target longer or slow
  the gesture, then re-record that beat. Don't use `Zoom:` for this — it breaks the
  phone-frame fit; keep it `none` on every beat.
- screen disappears too early → raise `Hold:` on that beat.
- captions wrong → they come from the voice timings; regenerate that beat's audio.
- background feels generic or clashes with the app → adjust `Background:`'s three hex
  colors in `script.md`, re-assemble (no re-record needed).
- ugly cut → adjust the flow so the beat ends on a settled screen, then re-record the
  whole take (`record_app.sh video` — it's one continuous session) and re-run
  `split_beats.py video` (no need to go through `review.py` again post-launch).

When they say it's good, tell them where the file is and one sentence about the
watermark trade-off (free avatar plans watermark; paying for one month and re-downloading
the same clips removes it). Update `progress.md` to complete.

## Tone

Warm, brief, no cheerleading. Report what happened, give the next single action.
