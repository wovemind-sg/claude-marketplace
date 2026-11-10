# Getting the avatar clips (the presenter on camera)

This is the one part that can't be automated on a free plan. The user makes one short
clip per `(avatar)` beat in a browser tool and saves it into `video/avatar/`.
Guide them **one action per message**, and verify each file with ffprobe when they say done.

Two ways to do it; recommend the first because the voice then matches the demo
voice-over exactly:

## Option A (recommended): upload our audio, let the avatar lip-sync

`tts.py` already produced `video/voice/beat-NN.mp3` for the avatar beats. The avatar
tool lip-syncs to that file, so the whole video has one consistent voice.

HeyGen (free plan: 3 videos/month, up to 1 minute each, watermarked) — walk through
these as separate messages:

1. "Go to app.heygen.com and sign in (or create a free account). Tell me when you're in."
2. "Click **Create video**, then **Avatar video** (sometimes labelled 'Start with an avatar'). Tell me when you see the editor."
3. "Pick any presenter you like from the avatar list. A plain, simple background is best. Tell me when you've chosen one."
4. "Set the video size: click the aspect-ratio / orientation button and choose **9:16 portrait**" (or **16:9 landscape** if `Format: landscape`). "Tell me when done."
5. "In the script area on the right, switch from 'Text' to **Upload audio** (it might be under a microphone icon) and upload this file: `<absolute path to video/voice/beat-01.mp3>`. Tell me when it's uploaded."
6. "Click **Submit** / **Generate** in the top-right. It takes a few minutes. Tell me when it says the video is ready."
7. "Click **Download**, choose the highest quality offered, and save the file as `<absolute path to video/avatar/beat-01.mp4>`. Tell me when it's saved."
   (If their browser insists on its own filename, have them download anywhere, then you move/rename it yourself — ask for the download location as the single action.)
8. Verify: `ffprobe video/avatar/beat-01.mp4` must show a video **and** an audio stream. Then start again from step 5 for the next avatar beat (same avatar, same settings — remind them to pick the same presenter).

If HeyGen's free plan hides audio upload, fall back to Option B.

Synthesia (free plan, no card) is an equivalent alternative if HeyGen isn't working:
Create video → choose avatar → script panel → the audio upload is under "Script" → "Upload audio".
Same flow, same one-step guidance.

## Option B: paste the text, use the tool's own voice

`tts.py` also wrote `video/avatar/PASTE-beat-NN.txt` with the exact text. Same steps as
Option A, but at step 5 the user pastes that text into the script box and picks a voice.
Ask them to note the voice's name so every avatar clip uses the same one. The demo
voice-over will be a different voice — acceptable, but mention it once so it isn't a surprise.

## Things to tell the user once, before starting

- Free plans put a small watermark in the corner. That's fine for testing; if they want it gone they can pay for one month later and regenerate the same clips.
- Keep each avatar beat under about 55 seconds of speech (free-plan limit is 1 minute).
- Same avatar, same background, same orientation for every clip — otherwise the cuts look wrong.

## When the clips look bad

- Robotic or rushed: the text has long sentences. Shorten them in `script.md`, rerun tts.py for that beat with `--only`, and regenerate the clip.
- Avatar talks but the file is silent: they downloaded without audio; redo the download.
- Wrong orientation: the clip gets letterboxed on dark bars. Regenerate with the right aspect ratio.
