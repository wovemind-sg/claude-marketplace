# Writing Maestro flows for demo beats

One flow per demo beat at `video/flows/beat-NN.yaml`. Claude writes these; the user never
edits them. `record_app.sh` runs every beat's flow back-to-back against the SAME running
app while a single screen recording captures the whole session, then cuts it into
`beat-NN.mp4` clips afterwards. That means only beat 1's flow should `launchApp` — beat 2
onward starts exactly on the screen where the previous beat left off, and a splash screen
only really shows up once. A later beat's flow just needs the `appId:` header and picks up
straight from its first `tapOn`/etc.; don't `launchApp` again unless the story genuinely
restarts the app.

## Skeleton

Beat 1 (the only beat that launches the app):

```yaml
appId: com.example.myapp        # from AndroidManifest.xml / build.gradle applicationId
---
- launchApp:
    clearState: true               # start from a fresh install so the demo is repeatable
- waitForAnimationToEnd
- extendedWaitUntil:
    visible: "Welcome"
    timeout: 10000
- tapOn: "New invoice"
- waitForAnimationToEnd
- tapOn:
    id: "customer_field"          # resource id, when text is unreliable
- inputText: "Tan Ah Kow"
- hideKeyboard
- tapOn: "Amount"
- inputText: "120"
- hideKeyboard
- tapOn: "Save"
- waitForAnimationToEnd
```

Beat 2 onward (no `launchApp` — the app is already open where beat 1 left it):

```yaml
appId: com.example.myapp
---
- tapOn: "Invoices"
- waitForAnimationToEnd
- tapOn: { text: "Tan Ah Kow", index: 0 }
- waitForAnimationToEnd
```

## Making it look like a real demo, not a test

The recording is what the viewer sees, so pace it for a human:

- Put `- waitForAnimationToEnd` after every tap, and add explicit pauses so each screen is visible for ~1.5–2.5 s before the next action. Every screen is one the viewer is seeing for the first time — give them a moment to read it before the demo moves on. Maestro has no plain sleep; use
  ```yaml
  - extendedWaitUntil:
      notVisible: "some text that is definitely not on screen zzz"
      timeout: 1500
  ```
  as a 1.5 s pause. Define it once and reuse.
- Type slowly is not possible; instead pause 1 s before and after `inputText` so the viewer registers the field.
- Never show real customer data, phone numbers, or secrets. Use obviously fictional names.
- Dismiss system dialogs (permissions, "Set as default") in the flow before the interesting part, or grant permissions up front:
  ```yaml
  - launchApp:
      permissions: { all: allow }
  ```

## Finding element names

- `maestro hierarchy` dumps the current screen's elements (text, resource ids). Run it with the app open on the right screen instead of guessing.
- `maestro studio` opens an interactive inspector in the browser — helpful when a tap misses.
- Prefer visible text (`tapOn: "Save"`) for readability; use `id:` when text changes or repeats.
- For a list item: `tapOn: { text: "Tan Ah Kow", index: 0 }`.

## Test data

If the beat needs an account or existing records, get the app into that state before
recording — either seed it (a debug endpoint, a fixture, `adb shell` commands) or ask the
user for a single test login. Put credentials in `video/flows/env.yaml` and reference them:
```yaml
- inputText: ${TEST_PHONE}
```
run with `maestro test -e TEST_PHONE=+6581234567 flow.yaml` (record_app.sh passes `MAESTRO_ARGS` through if you export it).

## Emulator tips

- Boot: `emulator -avd launch-video -no-snapshot-load -no-boot-anim &` then `adb wait-for-device && adb shell 'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 1; done'`
- Install the debug build: `./gradlew assembleDebug && adb install -r app/build/outputs/apk/debug/app-debug.apk` (path varies; check the module name).
- Disable animations for crisper recordings? No — keep them on; they look natural. Do turn off "Show taps" if it's on: `adb shell settings put system show_touches 0`.
- Portrait only: `adb shell settings put system accelerometer_rotation 0`.
