---
name: launch-video-setup
description: Check and install everything needed to make an AI launch video with the launch-video-app or launch-video-webapp skills (ffmpeg, Python packages, ElevenLabs key, Android emulator + Maestro, or the /playwright-cli skill for web app recording). Use this whenever the user mentions setting up, installing, or preparing for the launch video, when one of the launch-video skills reports something MISSING, or when the user asks "what do I need" for the video. Also use it when a launch-video script fails because a tool is not found.
---

# Launch video — setup

You are helping someone (possibly non-technical) prepare their computer so the
launch-video skills can run. Your job is to find what is missing and fix it —
doing it yourself wherever a command can do it, and asking the user only for the
things that require a human (creating an account, clicking through an installer,
approving a password prompt).

## The one-step rule (most important)

The user must never be asked to do more than one thing in a single message.

- Each of your messages ends with exactly one action for the user (or none, if you
  are doing the work yourself), phrased in plain language, followed by
  "Tell me when that's done" (or similar). Then stop and wait.
- When they reply, verify the step actually worked by running a command — don't
  take "done" on faith. If it didn't work, explain what you saw in one sentence
  and give the next single thing to try.
- Never present a numbered list of things to do. Never say "then". One action per
  message, every time. Even if three things are missing, handle them one at a time.
- No jargon without a one-phrase explanation. "ffmpeg (the program that stitches
  video clips together)" is good; "install ffmpeg via your package manager" is not.
- Do the work yourself whenever possible: install packages, edit PATH, create the
  emulator, write the key file. Ask the user only when a step needs them.

## Workflow

### Step 1 — Find out what they're making

If it isn't already clear from the conversation or the repo (an `AndroidManifest.xml`
or `build.gradle` means Android app; a FastAPI/Django/Next.js project means web app),
ask one question: "Is your launch video for a phone app (Android) or for a web app?"
Wait for the answer.

### Step 2 — Run the checker

Run `bash <this skill's dir>/scripts/check.sh app` (or `webapp`, or `both`).
It prints an OK/MISSING table. Tell the user briefly what's already fine and how many
things are missing ("Three things need installing; let's go one at a time."). Don't
list them all — go straight to the first missing item.

### Step 3 — Fix missing items one at a time

Take the first MISSING line. Read `references/install.md` for the exact procedure for
that item on the user's operating system (the checker prints it on the first line).
For each item:

1. If it can be installed by a command, run the command yourself. Tell the user what
   you're doing in one sentence ("Installing ffmpeg now, this takes a minute.") If it
   asks for an admin password, that's the one thing you ask the user to do.
2. If it needs the user (account sign-up, GUI installer, plugging in a phone), give
   the single next action and wait.
3. Re-run `check.sh` to confirm the item is now OK before moving to the next one.

Order matters for Android: install Java before the Android tools before Maestro,
and create the virtual device after the emulator exists. `install.md` is written in
that order.

### Step 4 — Confirm and hand over

When `check.sh` prints "everything is set up", tell the user they're ready and that
the next thing to do is run `/launch-video-app` (or `/launch-video-webapp`) — as a
single suggestion, not a list.

## Special cases

- **ElevenLabs key**: this needs the user. Walk them through creating a free account
  at elevenlabs.io, then to Profile → API Keys → Create. Ask them to paste the key
  into the chat. You then write it to `~/.launch-video/env` as
  `ELEVENLABS_API_KEY=<key>` (create the folder, `chmod 600` the file) and confirm
  with `check.sh`. Never echo the key back in full afterwards.
- **Any config always goes in `~/.launch-video/`, never inside this plugin's own
  directory.** A plugin install is a versioned cache copy (see the marketplace's
  CLAUDE.md) — the next update replaces it wholesale, so anything written under the
  skill's own folder is gone on the next version. The user's home directory is the
  only place that survives an update. Apply this to any future config this skill
  gains, not just the ElevenLabs key.
- **A real phone instead of the emulator** is fine for Android and skips the
  emulator/AVD steps. If the user has an Android phone handy and the emulator install
  is proving painful, offer that as the single next action: enable USB debugging and
  plug it in (see install.md).
- **Windows**: the scripts are bash. Windows users should use WSL (Ubuntu) and run
  everything inside it; Git Bash is not enough for the Android emulator. If the
  checker reports "Windows (Git Bash)", the first single action is installing WSL.
- **Things that already exist but aren't on PATH**: the checker says so. Fix PATH
  yourself by appending the export line to their shell profile (`~/.zshrc` on macOS,
  `~/.bashrc` on Linux/WSL), then ask them to do one thing: open a new terminal window
  and run `/launch-video-setup` again.
- **"ffmpeg captions (libass)" MISSING**: on macOS, Homebrew's plain `ffmpeg` formula
  is built without libass, so captions silently can't work — this is a confirmed setup
  gap, not something wrong with the video script. Run it yourself (no admin password
  needed): `brew uninstall ffmpeg && brew tap homebrew-ffmpeg/ffmpeg && brew install
  homebrew-ffmpeg/ffmpeg/ffmpeg` (see install.md). It's a same-for-same reinstall, not
  data loss — say so if the user asks about the uninstall step.

## Resuming

If the user comes back later, just run the checker again — it is the source of truth.
Don't ask what they did last time.
