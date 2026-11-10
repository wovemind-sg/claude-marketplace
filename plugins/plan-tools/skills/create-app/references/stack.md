# create-app stack reference

Canonical stack for native mobile apps produced by `/plan-tools:create-app`. The planner and every implementing session read this file. "Core" is always installed; "Menu" items are installed only when the feature list needs them.

## Versions

| Layer | Choice | Notes |
|---|---|---|
| Runtime | Node 26.7.0 (user's local install), npm | No `.nvmrc` / `.node-version` / `engines` pin — the machine's Node is the contract |
| Language | TypeScript 6.0 | `strict: true`; `tsconfig.json` extends `expo/tsconfig.base` |
| Framework | Expo SDK 57, React Native 0.86, React 19.2 | New Architecture on (Expo default). CNG/prebuild: `ios/` and `android/` are generated, **never committed** |
| Routing | `expo-router` | File-based under `app/`; typed routes on (`experiments.typedRoutes: true`) |
| State | `zustand` | One store per domain under `src/stores/`; no Redux, no Context for app state |
| Tests | Jest 29 + `jest-expo` | `"jest": { "preset": "jest-expo" }` in `package.json`; tests next to code as `*.test.ts(x)` |
| Native build | Xcode 16+ / CocoaPods (iOS); Gradle + JDK 17 (Android) | Invoked through `npx expo run:<platform>` locally |
| Distribution | EAS Build + EAS Submit | `eas.json` profiles `development`, `preview`, `production`; App Store Connect (TestFlight) and Play **alpha** track |

Pin exact versions with `npx expo install <pkg>` — it resolves the SDK-57-compatible version. Never hand-edit a React Native or Expo package version in `package.json`.

## Scaffold

```bash
npx create-expo-app@latest <app-name> --template default   # SDK 57, TypeScript, expo-router, tabs example
cd <app-name>
npx expo install react-native-reanimated react-native-worklets react-native-gesture-handler \
  react-native-screens react-native-safe-area-context expo-font expo-splash-screen
npm install zustand
npm install --save-dev jest@29 jest-expo @types/jest typescript@6
npx eas-cli init            # writes extra.eas.projectId into app.json
npx eas-cli build:configure # writes eas.json
```

Then:
- Delete the template's example tabs/components you don't need; keep `app/_layout.tsx` as the root layout with `GestureHandlerRootView`, `SafeAreaProvider`, font loading and splash hide.
- `app.json`: set `name`, `slug`, `scheme`, `ios.bundleIdentifier`, `android.package`, `newArchEnabled: true`, `plugins: ["expo-router", "expo-splash-screen", …]`, permission strings under `ios.infoPlist` and `android.permissions`.
- `babel.config.js`: `presets: ['babel-preset-expo']` — Reanimated 4's plugin is included via `react-native-worklets/plugin`; add it explicitly as the **last** plugin if animations don't run.
- `.gitignore`: `ios/`, `android/`, `.expo/`, `node_modules/`, `.env`, `*.jks`, `*.p8`, `*.p12`, `*.mobileprovision`, `google-service-account*.json`.
- Verify: `npx expo prebuild --clean`, then `npx expo run:ios` and/or `npx expo run:android` show the home screen.

## Project layout

```
<app-name>/
├── app/                      # expo-router routes only — thin, import screens from src/
│   ├── _layout.tsx           # root providers, fonts, splash
│   ├── (tabs)/               # tab group if the app has tabs
│   │   ├── _layout.tsx
│   │   └── index.tsx
│   └── modal.tsx
├── src/
│   ├── components/           # presentational, reusable
│   ├── features/<feature>/   # screens + hooks + feature-local components
│   ├── stores/               # zustand stores, one per domain
│   ├── db/                   # expo-sqlite: schema.ts (migrations), queries.ts
│   ├── lib/                  # pure helpers, typed wrappers around native modules
│   └── theme/                # colors, spacing, typography tokens from the design brief
├── modules/                  # local Expo Modules (see below)
├── assets/                   # fonts, images, splash, icon
├── app.json
├── eas.json
├── babel.config.js
├── tsconfig.json
├── package.json
├── .env / .env.example       # EXPO_PUBLIC_* only
└── .gitignore
```

## Menu — libraries

| Library | Include when | Notes |
|---|---|---|
| `expo-sqlite` | any local persistence beyond a few keys | Raw SQL via `openDatabaseAsync`; own migrations in `src/db/schema.ts` keyed by `PRAGMA user_version`. No ORM |
| `expo-media-library` | reading the photo/video library, deleting assets | Scan with paginated `getAssetsAsync`; delete with `deleteAssetsAsync` (OS confirmation dialog — cannot be bypassed). Needs `NSPhotoLibraryUsageDescription`, Android `READ_MEDIA_IMAGES`/`READ_MEDIA_VIDEO` (33+) |
| `expo-image` | any image rendering | Always over RN `<Image>`: caching, blurhash placeholders, `contentFit` |
| `expo-image-picker` | user picks/captures one or a few images | Not for library-wide access — that is `expo-media-library` |
| `expo-blur`, `expo-linear-gradient` | the design brief calls for them | Purely visual; skip if the design doesn't need them |
| `react-native-pager-view` | swipeable pages / onboarding / carousels | Pair with `react-native-tab-view` only if tabs-by-swipe is needed |
| `react-native-svg` | icons or vector illustrations beyond `@expo/vector-icons` | |
| `react-native-confetti-cannon` | a celebratory moment in the features | |

Always-on but worth knowing: `react-native-reanimated` 4 requires `react-native-worklets`; animations run on the UI thread — no `Animated` from RN core. `react-native-gesture-handler` wraps the root in `GestureHandlerRootView`. `react-native-screens` + `safe-area-context` are `expo-router` requirements.

## Menu — local Expo Modules (native code)

Use a local Expo Module when JS cannot do the job or is too slow: on-device ML, tight loops over thousands of photos, platform APIs with no maintained wrapper. Layout:

```
modules/<module-name>/
├── expo-module.config.json      # platforms, ios/android module class names
├── index.ts                     # typed JS API — the only thing app code imports
├── src/<ModuleName>.types.ts
├── ios/
│   ├── <ModuleName>Module.swift
│   └── <ModuleName>.podspec
└── android/
    ├── build.gradle
    └── src/main/java/<package>/<ModuleName>Module.kt
    └── src/main/assets/          # model files, if any
```

Create with `npx create-expo-module@latest <module-name> --local`. Autolinking picks up `modules/*` — no `app.json` entry needed. Every native change needs `npx expo prebuild` + `run:<platform>` again; hot reload does not cover Swift/Kotlin.

Reference modules (planned as their own sessions when needed):

| Module | Include when | iOS | Android |
|---|---|---|---|
| `modules/similarity-engine/` | grouping near-duplicate / similar images | Swift, Apple Vision `VNGenerateImageFeaturePrintRequest` → feature print; `computeDistance` for similarity | Kotlin, LiteRT (TensorFlow Lite) with `mobilenet_v3_small.tflite` from `assets/`; embed = penultimate layer, cosine distance |
| `modules/thumbnail-cache/` | showing many thumbnails fast (grids of library assets) | Swift, `PHImageManager.requestImage` at target size, disk cache in `Caches/` | Kotlin, `BitmapFactory` with `inSampleSize` (or `ImageDecoder` on 28+), disk cache in `cacheDir` |

API rules for every module: expose `async` functions returning plain JSON-able values; batch work (accept arrays of asset ids, return arrays) to avoid bridge chatter; surface progress via an Expo Modules event (`sendEvent`) rather than polling; never block the main thread on iOS — dispatch to a background queue.

## Conventions the sessions must keep

- **Screens are thin.** Files in `app/` only compose from `src/features/*`; logic lives in stores and `src/lib`.
- **Permissions are explicit UX.** Ask via the library's `requestPermissionsAsync` at the moment of need, handle `denied` with an inline explanation and a button to `Linking.openSettings()` — a denied permission must never look like "nothing happened".
- **Deletion goes through the OS.** `expo-media-library` deletion shows the system confirmation; design the flow around one batched confirm, not one per asset.
- **Safe areas and gestures** — every screen inside `SafeAreaView`/`useSafeAreaInsets`; every gesture through gesture-handler, never `PanResponder`.
- **Tests** — `jest-expo` for stores, `src/lib`, SQL queries (use the in-memory `:memory:` DB); native modules mocked in `jest.setup.ts`. No snapshot tests of whole screens.
- **EAS** — `development` profile with `developmentClient: true` + internal distribution; `preview` internal; `production` store. `eas submit` config: `ios.ascAppId` + API key, `android.track: "alpha"` + `serviceAccountKeyPath`. Bump `version` in `app.json`; let `autoIncrement` handle build numbers.
- **Never commit** `ios/`, `android/`, credentials, or model files larger than a few MB without asking (Git LFS or download-at-build-time script).
