# launch-video skills for Claude Code

Skills that turn an app repo into a launch video: AI presenter intro/outro,
real screen recordings of the app on a phone, one consistent voice, captions that
never cover the app, smooth cuts. Everything that can run from a terminal runs
automatically; the few manual parts are guided one step at a time.

`demo-video-app`/`demo-video-webapp` do just the screen-recording half — silent
per-feature beat clips, no AI presenter, no voice-over — for when that's all you need.

## Install

Copy the folders into your repo's `.claude/skills/` (per project) or into
`~/.claude/skills/` (available in every project):

    .claude/skills/launch-video-setup/
    .claude/skills/launch-video-app/
    .claude/skills/launch-video-webapp/
    .claude/skills/demo-video-app/
    .claude/skills/demo-video-webapp/

Keep them side by side — `launch-video-app`/`launch-video-webapp` call the setup
skill's checker, and `demo-video-app`/`demo-video-webapp` reuse the recording scripts
from their `launch-video-*` counterpart.

## Use

In Claude Code, inside the app's repo:

    /launch-video-setup      first time only — checks and installs tools
    /launch-video-app        full launch video, Android app
    /launch-video-webapp     full launch video, web app (FastAPI, Django, Next.js, ...)
    /demo-video-app          just the silent demo beats, Android app
    /demo-video-webapp       just the silent demo beats, web app

Claude will ask you to do exactly one thing at a time and wait.

## What you need (the setup skill installs/checks all of it)

- ffmpeg, Python 3.9+, pillow
- a free ElevenLabs account (voice-over)
- Android: Java, Android command-line tools + emulator (or a real phone), Maestro
- Web: Playwright + Chromium
- a free HeyGen or Synthesia account for the presenter clips (manual, guided)

## Output

    video/script.md      your script (edit freely, then re-run)
    video/out/launch.mp4 the video
