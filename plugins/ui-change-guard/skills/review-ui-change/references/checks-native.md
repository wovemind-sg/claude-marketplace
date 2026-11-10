# UI change review — native app check catalog

For React Native / Expo, SwiftUI / UIKit, Jetpack Compose / Android Views, Flutter, and Capacitor/Ionic hybrids. Same format as `checks.md` (**Signal · Verify · Severity**); sections 2, 7, 9, 10, 13 of `checks.md` (parity, behavioral semantics, tests, scope, shared components) apply to native unchanged — read them too. This file holds what is different on native.

Contents: N1 API/data contract · N2 Parity (native specifics) · N3 Performance · N4 Permissions, privacy & store compliance · N5 Security · N6 Accessibility · N7 Layout, devices & input · N8 Navigation, state & lifecycle wiring · N9 Platform project files · N10 Assets · N11 Capacitor / hybrid webview

---

## N1. API / data contract (view → view-model → API)

On native the "form" is a view-model or state object serialized to JSON. The analog of "deleted a form field" is a removed binding whose value the request body still needs.

| Signal | Verify | Severity |
|---|---|---|
| REMOVED input (`TextField`/`TextInput`/`OutlinedTextField`/`TextFormField`) or its binding (`$phone`, `value={phone}`, `vm.phone`, `controller`) | grep the view-model / store / request DTO (`Codable` struct, `data class`, `interface`, `freezed` class, `zod` schema) for the field; then the API client call. If the DTO still sends it, it now sends a default/empty/null; if the backend requires it, the request fails | Blocker if sent to API; Note if truly local |
| Binding RENAMED but DTO key unchanged (or vice versa) | Compare `CodingKeys`/`@SerialName`/`@JsonKey`/object literal keys against the backend schema | Blocker |
| Input `keyboardType`/`inputType`/`textContentType`/`autofillHints` changed | Value format the API parses (phone, number with locale separators) | Warning |
| Picker/segmented/dropdown option *values* changed (labels are fine) | Backend enum | Blocker if mismatch |
| Toggle/switch default changed (`@State var marketing = true`, `useState(true)`, `remember { mutableStateOf(true) }`) | Consent/billing semantics (§7 of checks.md) | Blocker for consent/legal |
| Submit action now calls a different VM method / endpoint / passes fewer args | Trace the call to the API client | Blocker |
| Client-side validation removed (`validator:`, `.disabled(!isValid)`, `enabled = isValid`, zod/yup schema) | Does the API validate? Error shown to user on 4xx? | Blocker if API trusts client or error swallowed |
| Error-state display removed (`if let error`, `errorText`, `snackbar`, `Alert.alert(err)`) | API failures now silent | Blocker |
| Optimistic update added without rollback on failure | | Warning |
| Offline/pending-sync UI removed where app supports offline | | Blocker |

## N2. Functional parity — native specifics

In addition to §2 of `checks.md`:

| Signal | Verify | Severity |
|---|---|---|
| Removed swipe action, long-press, context menu, pull-to-refresh, drag reorder, pinch/zoom, shake, 3D/haptic touch | Any other way to do the action? | Blocker if only path; Warning otherwise |
| Removed toolbar/nav-bar/tab-bar item, app-bar action, FAB, bottom-sheet action, menu entry | | Blocker |
| Removed `NavigationLink`/`navigate(...)`/`Navigator.push`/`router.push` | Destination now unreachable? grep other entry points and deep links | Blocker |
| Removed confirmation (`confirmationDialog`, `Alert.alert` with cancel, `AlertDialog`, `showDialog`) on destructive/paid action | | Blocker |
| Removed `.alert`/dialog/snackbar for *results* (success/failure feedback) | | Warning |
| Removed empty/loading/skeleton/error state view | | Warning |
| Platform-conditional block removed (`#if os(iOS)`, `Platform.OS === 'android'`, `if (Platform.isIOS)`, `Build.VERSION.SDK_INT`) | Feature lost on one platform | Blocker |
| Role/entitlement conditional removed (`if user.isAdmin`, `isPremium &&`, `hasEntitlement`) with block still rendered | Shows paid/admin controls to everyone; backend will 403 or, worse, honor it | Blocker (security) |
| Removed share sheet / export / copy / open-in-browser / call / mail intents | | Warning (Blocker if core) |
| Removed keyboard-return/`onSubmitEditing`/`imeOptions=actionDone` submit path | User must tap button; forms with no visible button become dead | Warning |
| Widget / watch / CarPlay / Live Activity / app-shortcut entry changed with the view | Separate target still compiles and renders? | Blocker |
| Removed back/close/cancel in modal or full-screen cover; `interactiveDismissDisabled` added without a close button | User trapped | Blocker |

## N3. Performance

| Signal | Verify | Severity |
|---|---|---|
| Virtualized list → eager: `FlatList/SectionList/FlashList` → `ScrollView` + `.map`; `LazyColumn` → `Column` + `forEach`; `List/LazyVStack` → `VStack` + `ForEach` inside `ScrollView`; `ListView.builder` → `ListView(children: list.map(...))`/`Column` | Realistic data size; frame drops on scroll | Blocker over ~50 items, Warning otherwise |
| Timer/polling: `Timer.publish(every:)`, `setInterval`, `LaunchedEffect { while(true) { delay } }`, `Timer.periodic` | Interval < 5 s; runs in background/when view off-screen (no `onDisappear`/cleanup)? | Warning; Blocker if measured battery/CPU or request storm |
| Work on main/UI thread: sync file/network/JSON decode in `body`/`build()`/composable/render; heavy loops in `useMemo`-less render | | Blocker |
| Re-render storms: new object/closure/array literal passed as prop each render (RN), `@Published` on a huge object, whole-screen `@State` for one field, Compose unstable params/lambdas without `remember`, Flutter `setState` on root for a leaf change | Profile: RN perf monitor / Flipper, Compose recomposition counts, Flutter DevTools rebuild stats, SwiftUI `Self._printChanges()` | Warning; Blocker if visibly janky |
| JS-thread animations (RN `Animated` without `useNativeDriver: true`, `setState` per frame) instead of Reanimated/native driver | | Warning |
| Images: full-resolution assets for thumbnails, no `resizeMode`/`contentScale`/`cacheWidth`, no caching lib, decode on main thread, remote images without placeholder/size → layout jump | | Warning |
| Blur/shadow/`backdrop-filter`-style effects (`.blur`, `BlurView`, `Modifier.blur`, `BackdropFilter`, `.shadow` per list row, `elevation` per row) | | Warning |
| Heavy new dependency (maps, charts, lottie, large icon packs) for a small need | Bundle/app size delta | Warning |
| Startup path touched: new work in `App`/`MainActivity`/`AppDelegate`/`main()`/root layout `useEffect` | Cold-start time | Warning |
| Removed pagination / `onEndReached` / `LoadState` / `.task(id:)` cancellation | Loads everything or leaks requests | Blocker |
| Missing cleanup: `useEffect` without return, `DisposableEffect` without `onDispose`, `.onDisappear` missing for timers/observers, Flutter `dispose()` not cancelling controllers | Leaks, duplicate timers after navigating back | Warning |
| Measured: dropped frames / jank on a mid-tier device, > 2 s screen open, memory growth on back-and-forth navigation | Xcode Instruments / Android Profiler / RN perf monitor / Flutter DevTools, or Maestro flow timing | Warning; Blocker if order of magnitude vs base |

## N4. Permissions, privacy & store compliance

| Signal | Verify | Severity |
|---|---|---|
| New permission request (camera, mic, photos, location, contacts, notifications, Bluetooth, tracking) without the matching usage string (`Info.plist` `NS…UsageDescription`, `app.json` `infoPlist`/`permissions`, `AndroidManifest` `<uses-permission>`) | iOS crashes on request without the string; store rejects vague strings | Blocker |
| Usage-description text removed/changed to something generic | App Review rejects | Warning |
| Permission denied path removed: denial looks identical to cancel (no re-prompt). Pre-flight check *and* re-check in `catch` both needed; denial UI must link to Settings (`openSettings`, `NativeSettings.open`) | Read the handler for the denied branch | Blocker (silent no-op) |
| Permission requested at launch instead of at point of use | Store guidance; conversion | Warning |
| Tracking/analytics SDK added without ATT prompt (iOS) / privacy manifest entry / Play Data Safety update | | Blocker |
| Privacy-manifest-required API newly used (UserDefaults, file timestamps, boot time) without `PrivacyInfo.xcprivacy` reason | Upload rejected | Blocker |
| Account-deletion entry removed/hidden (required by both stores for apps with accounts) | | Blocker |
| Login-with-Apple removed while other social logins remain (iOS requirement) | | Blocker |
| Purchase flow changed: external payment link, price text hard-coded, restore-purchases button removed, subscription terms text removed | Store policy | Blocker |
| Background modes / `foregroundServiceType` added | | Needs engineer |

## N5. Security

| Signal | Verify | Severity |
|---|---|---|
| Sensitive value moved from Keychain/Keystore/`SecureStore`/`EncryptedSharedPreferences` to `UserDefaults`/`AsyncStorage`/`SharedPreferences`/`shared_preferences` | | Blocker |
| Secret/API key/internal URL hard-coded in view code | | Blocker |
| New `WebView`/`WKWebView` loading remote content with JS enabled, `allowNavigation` widened, universal link handling loosened | | Needs engineer (Blocker if untrusted URL from user input) |
| Deep-link/route added that opens an authenticated screen without checking auth state | Test the URL cold | Blocker |
| `print`/`console.log`/`Log.d` of tokens, PII, request bodies left in | | Warning (Blocker for tokens) |
| Screenshot/recording protection removed (`FLAG_SECURE`, `isSecureTextEntry`, `privacySensitive`) on sensitive screens | | Warning |
| Password field lost `secureTextEntry`/`PasswordVisualTransformation`/`obscureText`; autofill hints removed | | Blocker / Warning |
| Clipboard copy of sensitive data added | | Warning |
| Certificate pinning / ATS exception / `usesCleartextTraffic` changed | | Needs engineer |

## N6. Accessibility

| Signal | Verify | Severity |
|---|---|---|
| Icon-only control lost `accessibilityLabel` / `contentDescription` / `semanticLabel` / `.accessibilityLabel()` | VoiceOver/TalkBack reads nothing or "button" | Warning (Blocker for primary actions) |
| Tappable `View`/`Box`/`Container` with gesture instead of `Pressable`/`Button`/`clickable` with role → not announced as button, no focus | | Warning |
| Decorative image not hidden (`accessibilityElementsHidden`, `importantForAccessibility="no"`, `excludeFromSemantics`, `.accessibilityHidden`) | | Warning |
| Dynamic Type / font scaling broken: fixed `fontSize` without `allowFontScaling`, `.font(.system(size:))` without `relativeTo`, `sp` → `dp` for text, Compose `fontScale` ignored, fixed heights that clip at larger text | Test at largest accessibility text size | Warning (Blocker if content clipped/unreachable) |
| Touch target < 44×44 pt (iOS) / 48×48 dp (Android); `hitSlop`/`minimumInteractiveComponentSize` removed | | Warning |
| Color-only state, contrast drop, removed `prefers-reduced-motion`/`accessibilityReduceMotion`/`isReduceMotionEnabled` guard on animations | | Warning |
| Modal/sheet without focus move / `accessibilityViewIsModal` / `importantForAccessibility` on background | | Warning |
| Removed `accessibilityHint`/`stateDescription`/`accessibilityValue` on sliders, toggles, custom controls | | Warning |
| Grouping removed (`MergeSemantics`, `.accessibilityElement(children: .combine)`, `mergeDescendants`) → list rows read as many fragments | | Warning |
| Removed `testID`/`accessibilityIdentifier`/`testTag`/`Key` used by UI tests | grep Detox/Maestro/XCUITest/Espresso/integration tests | Warning (test will fail; must be updated, not weakened) |
| Removed haptic/sound/visual feedback trio — feedback now only one channel | | Note |

## N7. Layout, devices & input

| Signal | Verify | Severity |
|---|---|---|
| Safe-area handling removed (`SafeAreaView`, `useSafeAreaInsets`, `.ignoresSafeArea` misuse, `WindowInsets`, `SafeArea` widget) | Content under notch/home indicator/status bar | Blocker if controls covered |
| Keyboard avoidance removed (`KeyboardAvoidingView`, `.scrollDismissesKeyboard`, `imePadding()`, `resizeToAvoidBottomInset`) | Keyboard covers input/submit button | Blocker |
| Fixed pixel/pt dimensions replacing flexible; hard-coded widths from a design-tool frame (375/390) | Small phones, tablets, foldables, landscape | Warning |
| Orientation/size-class branches removed (`horizontalSizeClass`, `WindowSizeClass`, `useWindowDimensions`, `MediaQuery`) | Tablet/landscape layout | Warning (Blocker if unreachable) |
| Dark-mode support dropped: hard-coded colors replacing semantic/theme colors (`Color.primary`, `MaterialTheme.colorScheme`, `Theme.of(context)`, `useColorScheme`) | View in dark mode | Warning |
| RTL broken: `left/right` replacing `leading/trailing`/`start/end`, `I18nManager` ignored, directional icons not mirrored | | Warning |
| Scroll inside scroll (nested same-axis scroll views), `flex: 1` removed causing content cut off, `overflow: hidden` clipping | | Warning |
| Text truncation: `numberOfLines`/`lineLimit`/`maxLines` added where full text matters (addresses, amounts) | | Warning |
| Status-bar / navigation-bar style no longer set per screen | | Note |
| Haptics/sounds added on every interaction | | Note |

## N8. Navigation, state & lifecycle wiring

| Signal | Verify | Severity |
|---|---|---|
| Route name / screen param changed (`navigate('Billing', {id})`, `NavigationLink(value:)`, `composable("billing/{id}")`, `GoRoute(path:)`) | grep all callers *and* deep-link config (`linking`, `app.json` `scheme`, `Info.plist` URL types, `intent-filter`, `.well-known`) | Blocker |
| Screen removed from navigator/`NavHost`/`NavigationStack`/router while still navigated to | Runtime crash or no-op | Blocker |
| State moved from shared store/VM to local `@State`/`useState`/`remember` (or vice versa) | Other screens that read it; survives rotation/background (Compose `rememberSaveable`, Android process death)? | Blocker if other consumers |
| Form state lost on navigation/rotation/background (no `rememberSaveable`, no `@SceneStorage`, no persistence) | Rotate mid-form | Warning |
| Lifecycle hooks removed: `onAppear`/`useEffect`/`LaunchedEffect`/`initState` that loaded data; `onDisappear`/cleanup that saved or cancelled | Screen now empty, or saves lost | Blocker |
| Back behavior: `BackHandler`/`onBackPressed`/`WillPopScope`/`PopScope` removed on screens with unsaved changes or custom back | | Warning |
| Tab/stack reset on re-select changed; modal presentation style changed (`pageSheet` → `fullScreen`) losing swipe-dismiss | | Warning |
| Async task not cancelled on dismiss (`.task` → manual `Task {}` without cancellation; `useEffect` without abort) | Set-state-after-unmount, stale results | Warning |
| Event name / `NotificationCenter` key / EventEmitter name / `SharedFlow` changed | grep listeners | Blocker |
| Hot-reload-only behavior (works via Fast Refresh, breaks on cold start: state initialized in render, missing `key`) | Cold start the app | Blocker |

## N9. Platform project files (always Needs engineer, plus listed severities)

| Signal | Verify | Severity |
|---|---|---|
| `Info.plist`, `Entitlements`, `*.xcodeproj`/`*.pbxproj`, `Podfile`/`Package.swift` | Capabilities, signing, SDKs | Needs engineer |
| `AndroidManifest.xml`, `build.gradle(.kts)`, `proguard-rules`, `gradle.properties` | Permissions, SDK versions, shrinking | Needs engineer |
| `app.json`/`app.config.*`, `eas.json`, `expo-module.config`, `metro.config`, `babel.config` | Plugins, scheme, permissions, bundle ids | Needs engineer |
| `pubspec.yaml`, `capacitor.config.*`, `ionic.config` | | Needs engineer |
| New native module / `pod install` / `prebuild` required for a UI change | Does the dev build still run without rebuild? | Needs engineer |
| Version/build number bumped or changed | | Note |

## N10. Assets

| Signal | Verify | Severity |
|---|---|---|
| Image added to one density/scale only (`@1x` only, no `drawable-xxhdpi`/vector, no `2.0x`/`3.0x`) | Blurry on most devices | Warning |
| Asset catalog entry (`Assets.xcassets`), `drawable` name, `pubspec` asset path, `require('./img.png')` path renamed with stale references | Runtime crash or blank image | Blocker |
| Custom font added without registration (`UIAppFonts`, `expo-font` loading, `pubspec` fonts, `res/font`) or used before loaded | Fallback font or crash | Blocker |
| App icon / splash changed outside the generator (`app.json` `icon`/`splash`, `AppIcon` set incomplete, adaptive icon layers) | Missing sizes → store rejection | Warning |
| Large binaries committed (video, uncompressed PNG, Lottie JSON > 1 MB) | App size | Warning |
| SVG via library on RN without `react-native-svg` transformer configured | | Blocker |
| Hard-coded strings replacing `Localizable.strings`/`strings.xml`/`intl`/i18n lookups | | Warning |

## N11. Capacitor / Ionic / hybrid webview apps

Apply `checks.md` fully (it is a web app) **plus**:

| Signal | Verify | Severity |
|---|---|---|
| Native gate written as `Capacitor.isNativePlatformAvailable` (does not exist) — only `isNativePlatform()` is real | Native-only path is permanently dead with zero errors; every fallback "half-works" | Blocker |
| Native plugin call (`Camera.getPhoto`, `Share.share`, `Haptics`, `PushNotifications`) removed in favor of web API, or vice versa | Web API behaves differently inside WKWebView (file inputs, `getUserMedia`, `window.open`) | Warning (Blocker if feature dead on device) |
| Permission denied handling: pre-flight `checkPermissions()` **and** re-check in `catch`; denial UI links to OS Settings via `NativeSettings.open()` | Denied looks like cancel otherwise | Blocker |
| `server.allowNavigation` / `appendUserAgent` / `scheme` changes; OAuth redirect hosts removed | Login escapes to system browser | Blocker |
| Text-entry control `font-size` < 16px (class or inline) | iOS zooms page on focus | Warning |
| Safe-area CSS (`env(safe-area-inset-*)`, `viewport-fit=cover`) removed; status-bar overlay changes | | Warning |
| Keyboard plugin behavior (`resize`, `scroll`) assumptions changed by layout (fixed footers, `100vh`) | Keyboard covers inputs | Blocker |
| `target="_blank"`/external links without `Browser.open` → opens inside webview with no back | | Warning |
| Back button (Android hardware) handling removed for modals/routes | | Warning |
| Live-update (Capgo/CodePush) bundle includes native-plugin changes that need a store build | | Needs engineer |
