# launch-video skills for Claude Code

Skills that turn an app repo into a launch video: AI presenter intro/outro,
real screen recordings of the app on a phone, one consistent voice, captions that
never cover the app, smooth cuts. Everything that can run from a terminal runs
automatically; the few manual parts are guided one step at a time.

`demo-video-app`/`demo-video-webapp` do just the screen-recording half — silent
per-feature beat clips, no AI presenter, no voice-over — for when that's all you need.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install launch-video@wovemind
```

All five skills ship in the one plugin, so they always sit side by side:
`launch-video-app`/`launch-video-webapp` call the setup skill's checker, and
`demo-video-app`/`demo-video-webapp` reuse the recording scripts from their
`launch-video-*` counterpart.

## Use

In Claude Code, inside the app's repo:

    /launch-video:launch-video-setup     first time only — checks and installs tools
    /launch-video:launch-video-app       full launch video, Android app
    /launch-video:launch-video-webapp    full launch video, web app (FastAPI, Django, Next.js, ...)
    /launch-video:demo-video-app         just the silent demo beats, Android app
    /launch-video:demo-video-webapp      just the silent demo beats, web app

Claude will ask you to do exactly one thing at a time and wait.

## Requirements

The setup skill installs or checks all of these:

- ffmpeg built with libass (for captions), Python 3.9+, pillow
- a free ElevenLabs account (voice-over)
- Android: Java, Android command-line tools + emulator (or a real phone), Maestro
- Web: Playwright + Chromium
- a free HeyGen or Synthesia account for the presenter clips (manual, guided)

The scripts are bash and run on macOS and Linux. On Windows, use WSL (Ubuntu);
Git Bash is not enough for the Android emulator.

## Environment variables and settings

- `ELEVENLABS_API_KEY`: your ElevenLabs API key. Read from the environment, or
  from `~/.launch-video/env` (a line `ELEVENLABS_API_KEY=<key>`). The setup skill
  writes that file for you with `chmod 600`. Configuration always lives in
  `~/.launch-video/`, never inside the plugin folder, so plugin updates keep it.

The plugin has no plugin settings.

## Opinionated defaults

Each run writes `video/script.md` first; edit it and re-run to change any of these.

| Default | Change it with |
|---|---|
| Vertical 9:16 video (a phone-sized browser for web apps) | `Format: landscape` in `video/script.md` |
| Voice-over in English, in a voice Claude picks from your ElevenLabs account | `Voice:` and `Language:` in `video/script.md` |
| ElevenLabs model `eleven_multilingual_v2` | not configurable |
| AI presenter intro and outro, demo beats in between | use `demo-video-app` / `demo-video-webapp` for the demo beats alone |
| Android only for native apps (no iOS recording) | not configurable |

## Example

Inside a FastAPI app's repo:

    /launch-video:launch-video-setup
    /launch-video:launch-video-webapp

Claude drafts `video/script.md`, records each feature with Playwright, generates
the voice-over, walks you through making the presenter clips on HeyGen or Synthesia, and
renders `video/out/launch.mp4`.

## Output

    video/script.md      your script (edit freely, then re-run)
    video/out/launch.mp4 the video
