---
name: launch-video-webapp
description: Produce a launch/promo video for a web app (FastAPI, Django, Next.js, any site) — an AI presenter introduces the product, then it is demonstrated in a phone-sized browser with voice-over and captions. Automates the script, the screen recordings (Playwright), the voice-over (ElevenLabs), and the final edit (ffmpeg), and walks the user through the few manual parts one step at a time. Use whenever the user asks for a launch video, promo video, demo video, product trailer, explainer, or "video for the landing page / Product Hunt / social media" for a website or web app, even if they don't say "AI" or "avatar". For Android apps use launch-video-app instead.
---

# Launch video — web app

You are producing a launch video for the web app in this repository. The user may
be non-technical. You do everything that can be done from the terminal; the user does
only what needs a human (reviewing the script, downloading avatar clips, watching the
result) — and always one thing at a time.

Read the repo before anything else: routes, templates/pages, README, how the app is
started locally, onboarding flow. The whole point of running inside the repo is that you already know
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
- Do everything you can yourself. Starting the app locally, writing the flows,
  generating audio, assembling — all yours.

## Files

Everything lives in `video/` inside the repo (add it to `.gitignore` except `script.md`
and `flows/`):

```
video/script.md          the script (starts as a rough draft, worded for real once recorded)
video/beats.json         parsed script (generated)
video/flows/beat-NN.py   Playwright flows, one per demo beat (you write)
video/recordings/        full.mp4 (the whole take) + beat-NN.mp4 (cut from it)
video/marks.json         each beat's start time in full.mp4 (generated)
video/review.json        the client's trims/notes on the take (generated)
video/voice/             voice-over mp3 + timing json
video/avatar/            avatar clips the user downloads, beat-NN.mp4
video/out/launch.mp4     the result
video/progress.md        your checklist — update after every completed step
```

Scripts in this skill's `scripts/` folder (run with the repo as working directory):
`parse_script.py`, `tts.py`, `record_web.py`, `review.py`, `apply_crops.py`, `split_beats.py`,
`review_beats.py`, `assemble.py`. Read their docstrings if unsure.

Any credential or setting this skill needs (the ElevenLabs key, or anything added later)
belongs in `~/.launch-video/`, never in this skill's own directory — a plugin update
replaces the installed skill folder wholesale, so config stored there would vanish.

## Resuming

If `video/progress.md` exists, read it and continue from the first unchecked item.
Don't re-ask things already answered there. Otherwise create it from the phase list below.

## Phase 0 — Check the tools

Run `bash <launch-video-setup skill dir>/scripts/check.sh webapp` (the setup skill is a
sibling of this one; if it isn't installed, check `ffmpeg`, `python3 -c "import PIL, playwright"`
and `~/.launch-video/env` yourself). If anything is MISSING, stop and
give the user one action: run `/launch-video-setup`. Don't continue until the check passes.

## Phase 1 — Plan the beats

The screen recording sets each demo beat's length, not the other way around — a demo
paced for a human (digest pauses, deliberate typing) rarely lands on exactly the word
count a first-guess sentence would take to read. So plan the *content* now; the exact
wording of demo beats comes later, once you know how long each one actually runs.

1. Learn the app from the repo. Identify the 2–4 things a first-time viewer must see.
   Also note its design language — CSS variables, Tailwind config, brand colors, logo,
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
   Set `Format: vertical` (phone-sized browser) unless the product is desktop-only, then
   `Format: landscape`. Set `Base URL:` to where the app will run locally. Set `Voice:` to a voice from
   the user's ElevenLabs account (run `tts.py` once with no voice to list them, and
   pick a natural one; the user can change it). Set `Background:` to three hex colors
   (dark, darker, glow accent) drawn from the app's own design language from step 1 —
   never the template's generic placeholder — so the space behind the phone in Phase 6
   feels like it belongs to this app.
3. Run `parse_script.py video` to validate.

## Phase 2 — Record the demo beats

All yours, no user actions unless something needs credentials you can't find. Pace the
flows for a human watching for the first time — don't rush them to hit a word count;
Phase 3 fits the words to whatever this actually takes.

1. Read `references/playwright-cheatsheet.md`.
2. Start the app locally in the background (uvicorn / npm run dev / docker compose — the
   repo tells you) with whatever database, Redis or `.env` it needs, and confirm the
   `Base URL` answers. If a value is needed that isn't in the repo (an API key, a test
   login), that is a single user action: "To record I need a test account to sign in
   with. What email/phone and password should I use? (Not a real customer's.)"
3. Seed the data each beat needs (fixtures, a debug endpoint, direct DB inserts) so the
   screens aren't empty. Fictional names only.
4. Write `video/flows/beat-NN.py` for every demo beat, in order, from the draft sentence
   in `script.md` (every sentence should correspond to something visible happening; pace
   ~2 s per action, type with `press_sequentially`). Then record the whole demo in one
   pass: `python3 <skill>/scripts/record_web.py video`. It runs every beat's flow
   back-to-back in one continuous browser page — so logins, splash screens and
   transitions only ever happen once, for real — and writes `video/recordings/full.mp4`
   plus `video/marks.json` (each beat's start time in the take). It does **not** split
   into per-beat clips yet — that happens after the client reviews the take, in Phase 2.5.
   If a beat's flow fails, look at the `<beat-id>-error.png` screenshot it saves, fix the
   selector, and re-run the same command (it re-records the whole take, which is short).

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
   - a note → do what it asks in that beat's flow (a different click, a longer pause to
     read something, a different screen, etc.).
   - a trim window that lines up with a `pause(...)` call (or a slow/redundant step) in
     that beat's flow → shorten or remove it there. This is the root-cause fix: the footage
     is only slow because the flow told it to wait, so make the flow not wait as long.
   - a trim window that *doesn't* line up with anything the flow controls — real page-load,
     network, or animation latency (a modal's own entrance animation, for example) — there's
     no `pause()` to shorten, so shortening the footage means cutting it. Run `python3
     <skill>/scripts/apply_crops.py video` instead; it removes exactly that window from
     `video/recordings/full.mp4` and shifts `video/marks.json` to match. Safe at this stage:
     no voice-over or captions exist yet to fall out of sync. If unsure which case you're in,
     `ffmpeg -ss <t> -frames:v 1 out.png` a frame or two around the window to see what's
     actually happening on screen before deciding.
   If you edited any flow, re-run `record_web.py video` for a fresh take (this also
   supersedes any `apply_crops.py` cuts from this round — they applied to the take you're
   replacing). Either way, go back to step 1 so the client can confirm the result. Repeat
   until the client marks it ready.
4. Run `python3 <skill>/scripts/split_beats.py video` to cut `video/recordings/beat-NN.mp4`
   from the approved take.
5. Note each demo beat's duration: `ffprobe -v error -show_entries format=duration -of
   csv=p=0 video/recordings/beat-NN.mp4`. You'll size that beat's spoken text to it next.

## Phase 2.6 — Review the split beats

One more look, now that each beat is its own clip — catches anything that only shows up
once a beat is isolated (an awkward start/end frame, a beat that reads wrong on its own).

1. Run `python3 <skill>/scripts/review_beats.py video`. It opens a browser page listing
   every beat clip; tell the client once: "The beats are split out — a page just opened
   in your browser. Watch each one, tick 'Looks good' or leave a note, then send it back
   or mark them all good." When it returns, `video/beats_review.json` has their per-beat
   notes.
2. If `action` is "ready": move on to Phase 3.
3. Otherwise, for each beat with a note, fix it the same way as a Phase 2.5 note (edit
   that beat's flow, or `apply_crops.py` for real latency, then re-record and re-split).
   Go back to step 1 to confirm. Repeat until every beat is ticked good.

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

Confirm the voice before spending any generation on it — ElevenLabs' voice list already
includes a free sample clip per voice (`preview_url`), no TTS credits needed to hear it.

1. Get the account's ElevenLabs key the same way `tts.py` does (`ELEVENLABS_API_KEY` env
   var, else `~/.launch-video/env`), then `curl -s -H "xi-api-key: $KEY"
   https://api.elevenlabs.io/v1/voices` and find the voice named in `script.md`'s `Voice:`
   line. Download its `preview_url` to `video/voice/preview.mp3` (`curl -s -o
   video/voice/preview.mp3 "<preview_url>"`).
2. **User action**: "Here's a free sample of the voice I'll use: `video/voice/preview.mp3`.
   Play it and tell me if it's good, or say a different voice/style and I'll find one."
   Wait. If they want another, pull the voice list from the same `/v1/voices` response
   (name + gender + accent), offer 3–4, download that one's `preview_url` too, and repeat
   until they approve. Update `Voice:` in `script.md` and re-run `parse_script.py video`
   if it changed.
3. Run `python3 <skill>/scripts/tts.py video`. It writes `video/voice/beat-NN.mp3` for
   every beat plus timings for captions. Because each demo beat's text was sized to its
   recording in Phase 3, lengths should already be close — spot-check with `ffprobe` on a
   beat or two; if a voice-over noticeably outruns or undershoots its recording, trim or
   pad that beat's sentence and rerun `tts.py --only beat-NN --force` rather than
   re-recording.

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
- can't see what's clicked → set `Zoom:` on that beat, re-assemble (no re-record needed).
  Every preset crops ~17% off each edge (top/center/bottom only shift the vertical
  window; the horizontal crop is always centered), so it slices off anything full-width —
  a header, a bottom nav bar. Frame-grab the result (`ffmpeg -ss <t> -frames:v 1
  out.png` on the assembled beat) before trusting a preset on an edge-to-edge screen; if
  it clips something, that beat needs `Zoom: none` instead.
- screen disappears too early → raise `Hold:` on that beat.
- captions wrong → they come from the voice timings; regenerate that beat's audio.
- background feels generic or clashes with the app → adjust `Background:`'s three hex
  colors in `script.md`, re-assemble (no re-record needed).
- ugly cut → adjust the flow so the beat ends on a settled screen, then re-record the
  whole take (`record_web.py video` — it's one continuous session) and re-run
  `split_beats.py video` (no need to go through `review.py` again post-launch).

When they say it's good, tell them where the file is and one sentence about the
watermark trade-off (free avatar plans watermark; paying for one month and re-downloading
the same clips removes it). Update `progress.md` to complete.

## Tone

Warm, brief, no cheerleading. Report what happened, give the next single action.
