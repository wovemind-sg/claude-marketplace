---
name: create-app
description: End-to-end bootstrap of a brand-new native mobile app (iOS/Android only, no web) on Expo SDK 57 + React Native 0.86 + expo-router + TypeScript — gather features, design reference and target platforms, pick only the needed Expo/RN libraries and local native modules, collect env and store credentials, clear toolchain blockers, plan with a subagent, split the plan into .planning/ sessions, then hand off to implementing subagents. Use whenever the user wants to start, bootstrap, kick off, or build a new mobile app, iOS app, Android app, React Native app, or Expo app from scratch and wants it planned and implemented end to end — even if they only say "new app", "build me an iPhone app that…", or "start a mobile project for…". Not for web apps or web apps wrapped as mobile (use create-webapp for those).
argument-hint: [optional one-line app idea]
---

You are orchestrating the birth of a new native mobile app: from a feature list to a running, committed implementation that builds through EAS. You do not write app code yourself — you gather what the subagents need, remove everything that would stall them, then delegate planning and implementation.

Everything downstream is only as good as the inputs collected here. A subagent with a vague feature list, a missing Apple credential, or an uninstalled JDK will either stop and wait or invent something. Native toolchains fail late and loudly — spend the effort up front.

If the user actually wants a web app that also ships to the stores, stop and point them at `/plan-tools:create-webapp` — that flow wraps a server-rendered app in Capacitor. This skill is for apps whose UI is native React Native.

## 1. Gather inputs

Use `$ARGUMENTS` as the seed if given. Ask for everything below in as few rounds as possible (AskUserQuestion, grouping related questions). Skip anything the user already stated.

1. **App name** (kebab-case) and **display name**. Default: current directory name. Confirm the current directory is the intended project root — if it is not empty, stop and ask.
2. **Platforms** — iOS, Android, or both. Drives toolchain checks, native module work and store setup.
3. **Bundle identifier / package name** (`com.example.app`) — needed for `app.json`, EAS and both stores. Propose one from the app name if the user has no preference.
4. **Features** — a list of what the app must do. Push for concrete user-facing behaviour ("scan the photo library, group near-duplicate photos, let the user delete a group in one tap"), not categories ("media", "ML"). Ask about anything ambiguous now; the planner cannot ask the user. Specifically probe for: offline/local-only vs. backend, on-device ML, access to photos/camera/contacts/location, background work, purchases.
5. **Design reference** (optional) — a URL, a screenshot/image path, an existing app to imitate, or a few words of direction ("dark, playful, big thumbnails"). If none, the planner picks a restrained default and writes it down.
6. **Distribution** — EAS Build + Submit to App Store Connect (TestFlight) and Play alpha track is the default. Confirm, and ask whether store submission is in scope now or just internal builds.
7. **Planning model** — default `sonnet`.
8. **Implementing model** — default `sonnet`. Options: `sonnet`, `opus`, `haiku`, `fable`.

## 2. Decide the stack slice

Read `references/stack.md` — it is the canonical stack (versions, scaffold commands, project layout, conventions, and the menu of libraries and native modules). The core is fixed; the menu is not. Every library added is a native dependency the prebuild must compile and the implementer must configure, so include only what the feature list needs. Decide each item, then confirm the table with the user in one message.

**Always**: Expo SDK 57 (CNG/prebuild — `ios/` and `android/` generated, never committed), React Native 0.86, React 19.2, TypeScript 6.0, expo-router, zustand, `react-native-screens`, `react-native-safe-area-context`, `react-native-gesture-handler`, `react-native-reanimated` 4 + worklets, `expo-font`, `expo-splash-screen`, Jest 29 + `jest-expo`, EAS (`eas.json`).

**From the menu, when the features call for it** (details and the "include when" column in `references/stack.md`): `expo-sqlite`, `expo-media-library`, `expo-image`, `expo-image-picker`, `expo-blur`, `expo-linear-gradient`, `react-native-pager-view`, `react-native-svg`, `react-native-confetti-cannon`, and **local Expo Modules** (Swift on iOS, Kotlin on Android) for anything JS cannot do — on-device similarity via Apple Vision / LiteRT, fast thumbnail generation via `PHImageManager` / `BitmapFactory`, etc. A native module is a whole extra skill set for the implementer; add one only when no maintained Expo/RN library covers the need.

**Anything not on the menu** (a backend, auth provider, payments, analytics) is allowed but must be named explicitly in the plan with its env vars and setup steps, because nothing in `references/stack.md` covers it.

## 3. Collect env values and credentials, write the files

Mobile apps have fewer env vars than servers but more credentials. Derive from the stack slice and features — only what is needed:

| Item | When | How to get the value |
|---|---|---|
| `EXPO_PUBLIC_*` vars | any API URL / public key the app reads at runtime | ask; goes in `.env` (Expo inlines `EXPO_PUBLIC_*` at build time) |
| Server-side secrets | never in the app bundle | if a feature needs one, it needs a backend — flag it, do not put it in `.env` |
| Expo account | always (EAS) | `eas whoami` — if not logged in, user runs `eas login` (interactive; suggest `! eas login`) |
| EAS project | always | `eas init` creates it and writes `extra.eas.projectId` into `app.json` |
| Apple Developer team + App Store Connect API key | iOS, submission in scope | user creates the key in App Store Connect; `eas credentials` or `eas submit` prompts for it |
| Google Play service account JSON | Android, submission in scope | user creates it in Play Console; path goes in `eas.json` `submit.production.android.serviceAccountKeyPath`, file gitignored |
| ML model files (e.g. `mobilenet_v3_small.tflite`) | on-device ML module | user provides or approves download; placed under `modules/<name>/android/src/main/assets/` |

Then:

1. `git init` if the directory is not already a repository.
2. Write `.env` with any collected `EXPO_PUBLIC_*` values and `.env.example` with the same keys and placeholders. Never echo secret values back into the conversation after this point.
3. Ensure `.gitignore` covers `.env`, `ios/`, `android/`, `node_modules/`, `.expo/`, `*.jks`, `*.p8`, `*.p12`, `*.mobileprovision`, `google-service-account*.json`. Verify with `git check-ignore .env ios android`.

## 4. Clear blockers

The implementing subagents run unattended. Anything they cannot do themselves must be done now. Check, don't assume — actually run each check and report pass/fail in a short checklist:

- **Node + npm** — `node --version` (expected 26.x, the user's local install — do not add `.nvmrc`/`.node-version`), `npm --version`.
- **Expo/EAS CLI** — `npx expo --version`, `npx eas-cli --version`, `eas whoami` returns an account.
- **iOS** (if targeted) — `xcodebuild -version` (Xcode 16+), `xcrun simctl list devices available | head`, `pod --version`. Xcode license accepted (`sudo xcodebuild -license accept` if the check complains).
- **Android** (if targeted) — `java -version` is 17, `ANDROID_HOME` set, `adb version`, `sdkmanager --list_installed | grep -E 'platforms;android-3[5-6]|build-tools'`, at least one emulator (`emulator -list-avds`) or a device.
- **Apple / Play accounts** (if submission in scope) — user confirms the app record exists in App Store Connect / Play Console with the chosen bundle id; you cannot test this.
- **Model files** (if on-device ML) — file present at the agreed path, size sane (`ls -l`).
- **Design reference readable** — image path exists / URL fetches.
- **Anything feature-specific** — third-party APIs, backend availability, paid accounts the features imply. Read the feature list once more with this lens.

Present failures as a numbered list, one line each, then wait for the user to fix them. Re-test after they say done. Do not move on with a known-broken toolchain — the implementer will hit it in session 1 at `npx expo prebuild`.

## 5. Plan

Spawn one subagent with `subagent_type: Plan` and `model:` the planning model. The Plan agent is read-only, which is what you want here. Its prompt must carry, verbatim, everything gathered above: app name, bundle id, platforms, feature list, design reference, distribution scope, the stack-slice table, the env/credential inventory, and the blocker results. Also give it the absolute path of this skill's `references/stack.md`. Then instruct it to:

1. Read `references/stack.md` in full and treat it as the source of truth for versions, scaffold commands, project layout and conventions. Only the parts in the stack slice get installed; the plan must list the exact `npx expo install …` lines per session.
2. Load `capacitor-core:capacitor-best-practices` **only if** the user explicitly wants a WebView somewhere (if the `capacitor-core` plugin is not installed, skip it and say so in the report) — otherwise ignore Capacitor entirely; this is a React Native app.
3. If a design reference was given, look at it (Read for images, WebFetch for URLs) and write a short design brief: palette, typography (which `expo-font` faces), spacing scale, navigation shape (tabs / stack / modal — expressed as an `expo-router` file tree), component look. If none, choose a restrained default and write it down anyway — every session must render the same app.
4. For each local native module in the slice, plan it as its own vertical slice: module skeleton via `npx create-expo-module@latest --local`, the JS API surface first with a stub implementation, then Swift, then Kotlin, each verified on a simulator/emulator before moving on. Model files, permissions (`NSPhotoLibraryUsageDescription`, `READ_MEDIA_IMAGES`, …) and `app.json` plugin config belong to that slice.
5. Produce a complete implementation plan: scaffolding first (a runnable `npx expo run:ios` / `run:android` showing the home screen is the first milestone), then features as vertical slices, each ending in a working committable state with `jest-expo` tests for logic and stores, the `eas.json` profiles (development, preview, production) and — if in scope — the submit configuration as the final slice. Return the plan as markdown.

Follow `/plan-tools:plan-helper` while planning. The Plan agent cannot ask the user anything itself, so tell it: when it has open decisions, end its run with those questions as its final report (plain English, 2–4 options each, recommendation first) instead of guessing. Ask the user with AskUserQuestion in plain English, then send the answers to that same Plan subagent with SendMessage so it continues with its context intact; repeat until it returns the finished plan.

Save the returned plan to `.planning/SPEC.md` (create `.planning/`). Show the user a one-screen summary and get a go-ahead before splitting — a wrong plan multiplied across sessions is expensive to unwind.

## 6. Split

Invoke `/plan-tools:split-plan` pointing at `.planning/SPEC.md`, with output directly under `.planning/` (its default) — not a subdirectory. Two outcomes:

- **Split** — `.planning/progress.md`, `.planning/CLAUDE.md`, `.planning/sessions/session-NN.md` now exist.
- **Not split** — split-plan judged the whole plan fits one session. `.planning/SPEC.md` stays the single source.

## 7. Implement

First, ask the user one question: **approve committing after every session (or at the end, if not split) without further confirmation?** The implementers commit as they go; without this approval they would stop after every session. Do not start until answered.

Then:

- **If split** — spawn one subagent (`subagent_type: general-purpose`, `model:` the implementing model) whose prompt is: invoke `/plan-tools:plan-split-implment` from this directory, with commit-per-session pre-approved by the user, and report back the final progress state and any session that stopped. That skill handles branching, per-session subagents, CLAUDE.md polish and plan archiving.
- **If not split** — spawn one subagent (`subagent_type: general-purpose`, `model:` the implementing model) instructed to: read `.planning/SPEC.md` in full and `references/stack.md` (absolute path) for conventions; implement the plan exactly, installing only the stack slice; verify (`npx expo prebuild --clean` succeeds, `npx expo run:ios` / `run:android` boots for each targeted platform, `npx jest` passes, each feature works on a simulator/emulator); write the project root CLAUDE.md; commit (pre-approved) with a semantic message; report back what was built and what, if anything, was left undone. If it ends with a question for the user instead of finishing, ask the user with AskUserQuestion in plain English, then send the answer to that same subagent with SendMessage so it continues.

Relay the implementer's report to the user as-is. Then list the obvious next steps only if they exist: unresolved blockers, deferred items, and — if submission was out of scope — that `eas build --profile production` + `eas submit` is the next step.
