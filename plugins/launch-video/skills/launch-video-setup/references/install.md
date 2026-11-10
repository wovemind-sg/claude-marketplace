# Installation procedures

Each section: what the tool is (say this to the user in plain words), then the
command(s) per operating system, then how to verify. Run the commands yourself;
only hand a step to the user where marked **USER**.

Detect the shell profile file: `~/.zshrc` on macOS, `~/.bashrc` on Linux/WSL.
After adding anything to PATH, the user has to open a new terminal — that is a
**USER** step and the whole reason to add all PATH lines for one tool at once.

---

## ffmpeg — "the program that cuts and stitches video clips"

- macOS: needs Homebrew. If `brew` is missing, that is its own single step first:
  run `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
  — it prompts for the user's Mac password (**USER**). Then `brew install ffmpeg`.
- Ubuntu/Debian/WSL: `sudo apt-get update && sudo apt-get install -y ffmpeg` (password prompt = **USER**)
- Fedora: `sudo dnf install -y ffmpeg-free`
- Verify: `ffmpeg -version | head -1`

### Captions need libass — plain `brew install ffmpeg` doesn't have it

Homebrew's core `ffmpeg` formula is built **without** `libass`, so the `subtitles` filter
`assemble.py` uses to burn in captions doesn't exist at all — captions silently fail (the
checker catches this as "ffmpeg captions (libass)" MISSING). This is a real, confirmed gap
in the default macOS install, not a script bug. Fix on macOS:
```
brew uninstall ffmpeg
brew tap homebrew-ffmpeg/ffmpeg
brew install homebrew-ffmpeg/ffmpeg/ffmpeg
```
(`libass` is a required dependency of that formula, no extra flag needed.) Verify:
`ffmpeg -filters | grep -w subtitles` should print a line.

Ubuntu/Debian/Fedora's normal `ffmpeg` packages already include libass, so this is a
macOS-only gotcha — but if the checker reports it missing on Linux too, reinstall
`ffmpeg` from the distro repo rather than a manually-built binary.

## Python 3.9+ — "the language the helper scripts are written in"

- macOS: `brew install python`
- Ubuntu/WSL: `sudo apt-get install -y python3 python3-pip python3-venv`
- Verify: `python3 --version`

## Python packages

- `python3 -m pip install --user pillow` (image library, draws the phone frame)
- If pip refuses with "externally-managed-environment" (newer Ubuntu), add `--break-system-packages`.
- Verify: `python3 -c "import PIL"`

## playwright-cli — "drives the browser for web app recording"

Web app only. The `/playwright-cli` skill drives Chromium directly — no pip install needed.

- Needs Node.js: macOS `brew install node`, Ubuntu/WSL `sudo apt-get install -y nodejs npm`.
- Install: `npm install -g @playwright/cli@latest` (or use it via `npx playwright-cli` without a global install).
- Verify: `playwright-cli --version` (or `npx --no-install playwright-cli --version`).
- If the first `playwright-cli open` reports no browser found, fall back to
  `npx playwright install chromium` once.

## ElevenLabs API key — "the voice that reads the script"

Entirely **USER**, one action at a time:
1. "Go to elevenlabs.io and create a free account (the free plan is enough). Tell me when you're signed in."
2. "Click your profile picture in the bottom-left, choose 'API Keys', then 'Create API Key'. Copy the key and paste it here."
3. You write it:
   ```
   mkdir -p ~/.launch-video
   printf 'ELEVENLABS_API_KEY=%s\n' '<key>' > ~/.launch-video/env
   chmod 600 ~/.launch-video/env
   ```
4. Verify: `curl -s -H "xi-api-key: <key>" https://api.elevenlabs.io/v1/user | head -c 200` should return JSON, not an error.
   Then run check.sh.

Free-tier limits: ~10,000 characters/month — enough for several drafts of a 90-second script. Mention this only if the user asks or hits the limit.

---

# Android app recording

## Java 17+ — "needed by the Android tools"

- macOS: `brew install --cask temurin@17`
- Ubuntu/WSL: `sudo apt-get install -y openjdk-17-jdk`
- Verify: `java -version`

## Android command-line tools + platform-tools (adb) + emulator

Prefer the command-line route (no Android Studio needed). If the user already has
Android Studio, the SDK is usually at `~/Library/Android/sdk` (macOS) or
`~/Android/Sdk` (Linux) — just fix PATH (below) instead of reinstalling.

- macOS:
  ```
  brew install --cask android-commandlinetools
  ```
  SDK root becomes `/opt/homebrew/share/android-commandlinetools` (Apple Silicon) or
  `/usr/local/share/android-commandlinetools` (Intel).
- Linux/WSL:
  ```
  mkdir -p ~/Android/Sdk/cmdline-tools && cd ~/Android/Sdk/cmdline-tools
  curl -Lo tools.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
  unzip -q tools.zip && rm tools.zip && mv cmdline-tools latest
  ```
  SDK root is `~/Android/Sdk`. (If the version number in the URL is stale, search "commandlinetools linux latest zip" and use the current one.)

Then, with `SDK=<sdk root>`:
```
yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null
"$SDK/cmdline-tools/latest/bin/sdkmanager" "platform-tools" "emulator" "platforms;android-34" "system-images;android-34;google_apis;<arch>"
```
`<arch>` is `arm64-v8a` on Apple Silicon Macs, `x86_64` everywhere else. This download is ~1.5 GB; warn the user it takes several minutes.

Add to the shell profile (all at once):
```
export ANDROID_HOME="<sdk root>"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
```
Then **USER**: open a new terminal and run `/launch-video:launch-video-setup` again.

Verify: `adb --version`, `emulator -version`.

WSL note: the emulator needs hardware acceleration, which WSL2 usually has, but it is the flakiest part of this whole setup. If `emulator` fails to boot on WSL, the pragmatic single next step is a real phone (below).

## Android virtual device (AVD) — "a pretend phone on your computer"

```
echo no | avdmanager create avd -n launch-video -k "system-images;android-34;google_apis;<arch>" -d pixel_7
```
Make it look like a clean phone: append to `~/.android/avd/launch-video.avd/config.ini`:
```
hw.keyboard=yes
hw.lcd.density=420
```
Verify: `emulator -list-avds` shows `launch-video`.
Boot test (optional, ~1 min): `emulator -avd launch-video -no-snapshot-load -no-boot-anim &` then `adb wait-for-device`.

## Real phone instead of emulator (alternative)

**USER**, one at a time:
1. "On your phone, open Settings → About phone and tap 'Build number' seven times until it says you're a developer."
2. "Go to Settings → System → Developer options and switch on 'USB debugging'."
3. "Plug the phone into the computer with a cable and tap 'Allow' on the phone if it asks."
Verify: `adb devices` shows the phone with `device` (not `unauthorized`).

## Maestro — "the robot that taps through the app while we record"

```
curl -fsSL "https://get.maestro.mobile.dev" | bash
```
It installs to `~/.maestro/bin`. Add to the shell profile: `export PATH="$HOME/.maestro/bin:$PATH"`, then **USER** opens a new terminal.
Verify: `maestro --version`.

---

# Uninstall / cleanup (only if the user asks)

- Maestro: `rm -rf ~/.maestro`
- AVD: `avdmanager delete avd -n launch-video`
- Key file: `rm ~/.launch-video/env`
