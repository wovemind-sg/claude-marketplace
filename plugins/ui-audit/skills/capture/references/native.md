# Native capture: Capacitor and Expo / React Native

**Status: untested.** The commands below follow the documented `xcrun simctl`, `adb` and Expo behavior, but this path has not been run against a real Capacitor or Expo app yet. Treat the first real run as a trial: run each command once, confirm its output, and fix this file when something differs. Tell the user the native capture is untested on the first run.

Platform ids: `capacitor-ios`, `capacitor-android`, `expo-ios`, `expo-android`. The device, app id and build commands live in `config.native` (shape below). The output layout is the same as for web: `$WORK/<side>/<screen>/<viewport>/<state>.png`, with the viewport named after the device, for example `iphone-15` or `pixel-8`.

## Which tool captures what

- Capacitor: the web layer is the same app as the web build. If the change is only in web UI, capture it with Playwright (`references/web.md`) and say so. Use a simulator or emulator for anything the browser cannot show: the native shell, safe areas and notch, status bar, keyboard, native plugins, permission sheets, splash screen.
- Expo / React Native: everything is native; use the simulator or emulator.
- If only the platform shell changed (Info.plist, AndroidManifest, splash, icons), capture just the screens the change touches.

## Config

`config.native` is filled in during the first-run interview when a native platform is enabled:

```json
"native": {
  "ios": {"device": "iPhone 15", "runtime": "iOS 17.5", "app_id": "com.example.app", "scheme": "exampleapp",
          "build": "npx cap sync ios && xcodebuild -workspace ios/App/App.xcworkspace -scheme App -sdk iphonesimulator -derivedDataPath $OUT build",
          "app_path": "$OUT/Build/Products/Debug-iphonesimulator/App.app"},
  "android": {"avd": "Pixel_8_API_34", "app_id": "com.example.app",
              "build": "npx cap sync android && (cd android && ./gradlew assembleDebug)",
              "apk": "android/app/build/outputs/apk/debug/app-debug.apk"},
  "expo": {"client": "dev-client", "start": "npx expo start --dev-client --port 8081"}
}
```

Screens use `route` as a deep link (`exampleapp://settings`, or `https://...` for universal links). When a screen has no deep link, use `nav_steps` (taps by accessibility label).

## iOS simulator

```bash
xcrun simctl list devices available            # find the device name/UDID
xcrun simctl boot "iPhone 15"                  # error "already booted" is fine
open -a Simulator                              # only if a visible window is needed
xcrun simctl bootstatus "iPhone 15" -b         # waits until the device is ready
xcrun simctl status_bar booted override --time 9:41 --batteryState charged --batteryLevel 100 --wifiBars 3 --cellularBars 4
xcrun simctl install booted "$APP_PATH"
xcrun simctl launch booted "$APP_ID"
xcrun simctl openurl booted "exampleapp://settings"     # deep link to a screen
sleep 2                                                  # let the screen settle
xcrun simctl io booted screenshot "$WORK/head/settings/iphone-15/default.png"
xcrun simctl io booted recordVideo --codec=h264 "$WORK/head/settings/iphone-15/menu-open.mov" &   # stop with: kill -INT $!
xcrun simctl status_bar booted clear
xcrun simctl terminate booted "$APP_ID"; xcrun simctl uninstall booted "$APP_ID"   # reset between base and head
```

The status bar override is what keeps stills stable (clock and battery). `recordVideo` writes `.mov`; convert to `.webm` with `ffmpeg -i in.mov out.webm` when ffmpeg is available, otherwise pass the `.mov` (the report page plays what the browser supports; tell the user if it does not). A screen reached without a deep link: use the simulator accessibility actions through the tool the project already uses (Maestro, Detox, `xcrun simctl` has no tap command); if none exists, ask the user how to reach the screen and save the answer as a recipe.

## Android emulator

```bash
emulator -list-avds
emulator -avd Pixel_8_API_34 -no-snapshot -no-audio -no-boot-anim &   # add -no-window on CI
adb wait-for-device
adb shell 'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 1; done'
adb shell settings put global sysui_demo_allowed 1      # stable status bar (demo mode)
adb shell am broadcast -a com.android.systemui.demo -e command enter
adb shell am broadcast -a com.android.systemui.demo -e command clock -e hhmm 0941
adb shell am broadcast -a com.android.systemui.demo -e command battery -e level 100 -e plugged false
adb shell am broadcast -a com.android.systemui.demo -e command network -e wifi show -e level 4
adb install -r "$APK"
adb shell am start -a android.intent.action.VIEW -d "exampleapp://settings" "$APP_ID"   # deep link
sleep 2
adb exec-out screencap -p > "$WORK/head/settings/pixel-8/default.png"
adb shell screenrecord --time-limit 5 /sdcard/clip.mp4 & sleep 6; adb pull /sdcard/clip.mp4 "$WORK/head/settings/pixel-8/menu-open.mp4"
adb shell am broadcast -a com.android.systemui.demo -e command exit
adb uninstall "$APP_ID"                                  # reset between base and head
```

Taps when no deep link exists: `adb shell input tap X Y` or `adb shell input text`, and `uiautomator dump` to find element bounds by accessibility label. `screenrecord` has a 3 minute cap and needs the clip kept short anyway.

## Expo / React Native specifics

- Dev client or release-like build: install a development build (`eas build --profile development --platform ios|android --local`, or `npx expo run:ios|android`), then point it at the Metro server for the commit being captured. Expo Go works only when the app uses no custom native code.
- Deep links: `xcrun simctl openurl booted "exp+<slug>://expo-development-client/?url=<metro url>"` loads the bundle, then open the screen deep link. On Android use `adb shell am start -a android.intent.action.VIEW -d ...` the same way.
- Check the `expo:eas-simulator` skill for the project's existing simulator conventions before inventing commands.
- Wait for the bundle to load (the first load after a base/head switch is slow) before the screenshot; a red error screen or the loading splash in a capture means the wait was too short.

## Base vs head

1. `git worktree add "$WORK/base-src" <base_sha>`; install dependencies if the lockfile differs from head (`npm ci`), then build.
2. Build base and head into separate output directories so neither build clobbers the other. Native builds are slow, so build base only for the screens and device you will capture.
3. Use the same device, OS version, orientation, locale, text size and seed data for both sides. Uninstall and reinstall the app for each side so state does not leak. Seed the data through the app's own mechanism (`web.seed`-style command, a debug deep link, or a fixture backend).
4. Capture base completely, then head, then remove the worktree.

## Questions and limits

- Platform question: when several native platforms are enabled, the skill asks which to capture (step 2 of SKILL.md). iOS and Android renders differ, so base and head are only ever compared on the same platform and device.
- Interactions go through deep links or accessibility-driven taps, replayed from the manifest recipes, never coordinates, except as a last resort (then record the device in the recipe).
- Motion clips: only under the same rule as web (diff touches transitions, animations, gestures, or ripple reasoning flags it). Keep clips under 5 seconds.
- Stills are device resolution; if a diff is noisy from scaling, compare at the native size and do not resize.
- Permission sheets and the keyboard are system UI: pre-grant permissions (`xcrun simctl privacy booted grant all "$APP_ID"`, `adb shell pm grant`) unless the permission sheet is what changed.
