#!/usr/bin/env bash
# Check everything the launch-video skills need and print a plain status table.
#
# Usage:  scripts/check.sh [app|webapp|both]      (default: both)
#
# Exit code 0 = everything present, 1 = something missing.
# Lines starting with "MISSING" are what still needs doing.
TARGET="${1:-both}"
MISSING=0

ok()      { printf "  OK       %-22s %s\n" "$1" "$2"; }
missing() { printf "  MISSING  %-22s %s\n" "$1" "$2"; MISSING=1; }

OS="$(uname -s 2>/dev/null || echo unknown)"
case "$OS" in
  Darwin) OS_NAME="macOS" ;;
  Linux)  if grep -qi microsoft /proc/version 2>/dev/null; then OS_NAME="Windows (WSL)"; else OS_NAME="Linux"; fi ;;
  MINGW*|MSYS*|CYGWIN*) OS_NAME="Windows (Git Bash)" ;;
  *) OS_NAME="$OS" ;;
esac
echo "System: $OS_NAME"
echo
echo "== Always needed =="

if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then
  ok ffmpeg "$(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}')"
  if ffmpeg -filters 2>/dev/null | grep -qw subtitles; then
    ok "ffmpeg captions (libass)" "subtitles filter present"
  else
    missing "ffmpeg captions (libass)" "this ffmpeg build has no 'subtitles' filter, so assemble.py can't burn in captions — see install.md to reinstall a libass-enabled ffmpeg"
  fi
else missing ffmpeg "video assembly tool"; fi

if command -v python3 >/dev/null; then
  PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
  if python3 -c 'import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)'; then ok python3 "$PYV"; else missing python3 "found $PYV, need 3.9 or newer"; fi
else missing python3 "needed for the helper scripts"; fi

if python3 -c 'import PIL' 2>/dev/null; then ok "python: pillow" "image library"; else missing "python: pillow" "python3 -m pip install pillow"; fi

ENVF="$HOME/.launch-video/env"
if [ -n "${ELEVENLABS_API_KEY:-}" ] || ( [ -f "$ENVF" ] && grep -q '^ELEVENLABS_API_KEY=.\+' "$ENVF" ); then
  ok "ElevenLabs key" "$ENVF"
else missing "ElevenLabs key" "voice-over; free account at elevenlabs.io"; fi

if [ "$TARGET" = "app" ] || [ "$TARGET" = "both" ]; then
  echo
  echo "== Android app recording =="
  if command -v java >/dev/null; then ok java "$(java -version 2>&1 | head -1 | sed 's/.*"\(.*\)".*/\1/')"; else missing java "needed by Android tools and Maestro"; fi

  if command -v adb >/dev/null; then ok adb "$(adb --version 2>/dev/null | head -1)"
  else
    for c in "$ANDROID_HOME/platform-tools/adb" "$ANDROID_SDK_ROOT/platform-tools/adb" "$HOME/Library/Android/sdk/platform-tools/adb" "$HOME/Android/Sdk/platform-tools/adb"; do
      if [ -x "$c" ] 2>/dev/null; then missing adb "installed at $(dirname "$c") but not on PATH"; c=""; break; fi
    done
    [ -n "${c:-x}" ] && missing adb "Android platform-tools"
  fi

  if command -v emulator >/dev/null || [ -x "${ANDROID_HOME:-/nonexistent}/emulator/emulator" ] || [ -x "$HOME/Library/Android/sdk/emulator/emulator" ] || [ -x "$HOME/Android/Sdk/emulator/emulator" ]; then
    ok emulator "Android emulator"
    AVDS=$( (command -v emulator >/dev/null && emulator -list-avds 2>/dev/null) || ls "$HOME/.android/avd" 2>/dev/null | sed 's/\.avd$//' | grep -v '\.ini$')
    if [ -n "$AVDS" ]; then ok "virtual device" "$(echo "$AVDS" | tr '\n' ' ')"; else missing "virtual device" "no Android virtual device (AVD) created yet"; fi
  else
    if adb devices 2>/dev/null | awk 'NR>1 && $2=="device"' | grep -q .; then ok "physical device" "a real phone is connected via adb"; else missing emulator "Android emulator (or connect a real phone with USB debugging)"; fi
  fi

  if command -v maestro >/dev/null; then ok maestro "$(maestro --version 2>/dev/null | tail -1)"
  elif [ -x "$HOME/.maestro/bin/maestro" ]; then missing maestro "installed in ~/.maestro/bin but not on PATH"
  else missing maestro "drives the app during recording"; fi
fi

if [ "$TARGET" = "webapp" ] || [ "$TARGET" = "both" ]; then
  echo
  echo "== Web app recording =="
  if command -v node >/dev/null; then ok node "$(node --version)"; else missing node "needed to run the /playwright-cli skill"; fi

  if command -v playwright-cli >/dev/null; then
    ok playwright-cli "$(playwright-cli --version 2>/dev/null | tail -1)"
  elif npx --no-install playwright-cli --version >/dev/null 2>&1; then
    ok playwright-cli "available via npx"
  else missing playwright-cli "npm install -g @playwright/cli@latest"; fi
fi

echo
if [ $MISSING -eq 0 ]; then echo "RESULT: everything is set up."; else echo "RESULT: some items are MISSING (see above)."; fi
exit $MISSING
