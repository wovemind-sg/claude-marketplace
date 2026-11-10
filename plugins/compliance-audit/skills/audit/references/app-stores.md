# App stores — Apple App Store and Google Play
last-reviewed: 2026-10-13
applies-when: any `mobile.*` signal (`mobile.ios`, `mobile.android`, `mobile.capacitor`, `mobile.react_native`) or the user says the product ships an iOS/Android app; Apple rows only for iOS, Google rows only for Android
sources:
- https://developer.apple.com/app-store/review/guidelines/
- https://developer.apple.com/news/upcoming-requirements/
- https://developer.apple.com/documentation/bundleresources/privacy-manifest-files
- https://developer.apple.com/support/third-party-SDK-requirements/
- https://developer.apple.com/app-store/app-privacy-details/
- https://developer.apple.com/support/offering-account-deletion-in-your-app/
- https://developer.apple.com/documentation/apptrackingtransparency
- https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations
- https://developer.apple.com/help/app-store-connect/manage-compliance-information/manage-european-union-digital-services-act-trader-requirements/
- https://developer.apple.com/help/app-store-connect/reference/age-ratings-values-and-definitions
- https://developer.apple.com/help/app-store-connect/manage-app-accessibility/overview-of-accessibility-nutrition-labels
- https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
- https://support.google.com/googleplay/android-developer/answer/10787469
- https://support.google.com/googleplay/android-developer/answer/13327111
- https://support.google.com/googleplay/android-developer/answer/11926878
- https://support.google.com/googleplay/android-developer/answer/12253906
- https://support.google.com/googleplay/android-developer/answer/13634081
- https://developer.android.com/developer-verification
- https://support.google.com/googleplay/android-developer/answer/10144311
- https://support.google.com/googleplay/android-developer/answer/9888170
- https://support.google.com/googleplay/android-developer/answer/9799150
- https://support.google.com/googleplay/android-developer/answer/9047303
- https://support.google.com/googleplay/android-developer/answer/10158779
- https://developer.android.com/training/data-storage/shared/photopicker
- https://support.google.com/googleplay/android-developer/answer/6048248
- https://support.google.com/googleplay/android-developer/answer/16555673
- https://support.google.com/googleplay/android-developer/answer/9893335
- https://capacitorjs.com/docs/config

## Who it applies to and thresholds

| Scope point | Rule |
|---|---|
| Size | No size threshold. Store rules bind every developer account; breach = rejection or removal, not a fine. |
| Capacitor / RN | `mobile.capacitor` ships a native shell: both `ios/` and `android/` projects are audited, and the web content shown inside the app is subject to the same store rules as native UI (payments, account deletion, UGC, kids). `mobile.react_native` (Expo): manifests live in `app.json`/`app.config.*` (`ios.infoPlist`, `ios.privacyManifests`, `android.permissions`) as well as generated native dirs. |
| Where to look | iOS: `ios/App/App/Info.plist`, `**/PrivacyInfo.xcprivacy`, `Podfile`/`Package.swift`. Android: `android/app/src/main/AndroidManifest.xml`, `android/variables.gradle` or `app/build.gradle` (`targetSdkVersion`). Store-console settings (privacy labels, Data safety, trader status) are not in the repo: ask or mark "confirm in console". |
| EU availability | DSA trader rows apply whenever the app is offered on any EU storefront (default when EU in markets). |
| Evidence limits | Console-only items never become Blocker without evidence; report them as Required "confirm in App Store Connect / Play Console". |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| Privacy manifest present | Apple: required-reason APIs (since 1 May 2024); Guideline 5.1.1 | `mobile.ios.privacy_manifest` present when `mobile.ios`; open it for `NSPrivacyAccessedAPITypes`, `NSPrivacyTracking`, `NSPrivacyTrackingDomains`, `NSPrivacyCollectedDataTypes` | File path or "not detected" + use of `UserDefaults`, file timestamps, disk space, boot time APIs in app-target code (SDKs such as Capacitor ship their own manifest inside the framework) | Blocker if app-target code uses a required-reason API with no app manifest declaring it (upload rejected, ITMS-91053); Required if the app manifest is missing or its `NSPrivacyCollectedDataTypes` does not match the data the app collects | engineer | Add `PrivacyInfo.xcprivacy` to the app target with an approved reason per API used. |
| Third-party SDK manifests and signatures | Apple third-party SDK requirements | `Podfile`/`Package.swift`/`package.json` for listed SDKs (Firebase, Capacitor, Alamofire, OneSignal, Flutter, Lottie, SDWebImage…); versions old enough to lack manifests | SDK + version | Required (Blocker if upload rejected) | engineer | Upgrade listed SDKs to versions shipping a privacy manifest and signature. |
| App Privacy "nutrition label" matches the code | Apple App Privacy details; Guideline 5.1.1, 2.3 | Compare `track.analytics.*`, `ai.*`, `pay.*`, `comm.*`, `perm.*`, `auth.accounts` with the label answers (ask) | Signal list vs declared data types | Required | founder | Re-answer the questionnaire in App Store Connect from the detected SDK list; include third-party SDK collection. |
| In-app account deletion | Apple 5.1.1(v) (since 30 Jun 2022) | `auth.accounts` + `account.delete_endpoint`; UI entry (grep templates/screens for `delete account`) | Route file:line + UI file:line, or "not detected" | Blocker if accounts exist and no deletion path found in code | engineer | Add Settings → Delete account that deletes (not just deactivates) the account; revoke Sign in with Apple tokens. |
| Login service equivalent to Sign in with Apple | Apple 4.8 | Any `auth.oauth.*` other than `auth.oauth.apple` (Google, Facebook, GitHub, Microsoft) on iOS | OAuth provider file:line | Blocker if third-party social login and no `auth.oauth.apple` or other privacy-preserving login (limits to name/email, hide-email, no ad tracking) | engineer | Add Sign in with Apple. Exempt: own accounts only, enterprise/education, government ID, client for a specific third-party service. |
| App Tracking Transparency prompt | Apple 5.1.2(i); ATT framework | `track.analytics.*` or ad SDKs that track across apps/sites; `NSUserTrackingUsageDescription` + `requestTrackingAuthorization` call | SDK init file:line + Info.plist key | Blocker if tracking SDK and no ATT prompt; Note for first-party analytics only | engineer | Request ATT before any cross-app tracking; disable IDFA collection otherwise. |
| Permission usage strings | Apple 5.1.1(ii); Info.plist `NS*UsageDescription` | For each `perm.*` (location, camera, mic, contacts, biometrics `NSFaceIDUsageDescription`, health) the matching key with specific purpose text | Info.plist line per permission | Blocker if a used permission has no key (crash/rejection); Required if text is generic | engineer | Add a specific, user-facing purpose string per key. |
| In-app purchase for digital goods | Apple 3.1.1 | `pay.stripe`/`pay.paddle`/`pay.lemonsqueezy` reachable inside the iOS app for digital content | Payment UI file:line | Required (see payments.md) | founder | Apply payments.md: IAP or a permitted link-out (US storefront rules). |
| Privacy policy URL in App Store Connect and in app | Apple 5.1.1(i) | `legal.privacy_policy_page` reachable from app settings | Template/screen file:line | Blocker if no policy page anywhere | founder | Link the policy in-app and in App Store Connect (see contracts-docs.md). |
| EULA choice | Apple standard EULA (Licensed Application EULA) | `legal.terms_page`; custom EULA entered in App Store Connect? | Terms page path | Recommended | lawyer | Use Apple's standard EULA or upload a custom one that contains Apple's minimum terms. |
| Export compliance declaration | US EAR; `ITSAppUsesNonExemptEncryption` | Key present in Info.plist (`false` when only HTTPS/OS crypto); `security.encryption` custom crypto | Info.plist line or "not detected" | Required (each upload otherwise prompts) | engineer | Set the key; if custom/non-exempt crypto, file the annual self-classification report. |
| DSA trader status declared (EU storefronts) | DSA Art. 30–31 via Apple | Console-only: ask whether trader status set; public contact (address, phone, email) | Answer | Blocker if EU in markets and trader status not provided (apps removed since 17 Feb 2025) | founder | Declare trader/non-trader in App Store Connect → Business; use a business address and dedicated support phone/email. |
| Age rating questionnaire answered | Apple age ratings (13+/16+/18+, since 31 Jan 2026) | Console-only; cross-check UGC, chat, `ai.*`, medical/wellness features | Answer | Required (updates blocked until answered) | founder | Answer the updated questionnaire; minors.md for Kids category (Guideline 1.3). |
| Remote/OTA code and wrapper apps | Apple 2.5.2, 4.2, 4.7 | `mobile.capacitor`: `server.url` in `capacitor.config.*` (whole app loaded remotely); live-update plugins (`@capgo`, `@capacitor/live-updates`, `expo-updates`) | Config file:line | Required (rejection risk under 4.2 minimum functionality if app is a website wrapper) | engineer | Bundle web assets; add native value (push, offline, native nav); OTA only for bug fixes that do not change the app's purpose. |
| Navigation scope | Capacitor `server.allowNavigation`; Apple 4.2/2.5.2 | `allowNavigation` entries; wildcards (`*`) | Config file:line | Recommended | engineer | Restrict to own domains plus required auth hosts; open others in the system browser. |
| Accessibility Nutrition Labels | Apple App Store Connect (voluntary since 2025, Apple states it will become mandatory) | Console-only | Answer | Note | founder | Declare supported features (VoiceOver, Larger Text, contrast) honestly; see accessibility.md. |
| Build SDK and minimum OS | Apple upcoming requirements | Xcode 26 / iOS 26 SDK for uploads (since 28 Apr 2026); deployment target ≥ iOS 13 (since 9 Sep 2026) | `IPHONEOS_DEPLOYMENT_TARGET`, CI Xcode version | Blocker if CI pins older Xcode (upload rejected) | engineer | Bump Xcode in CI; Capacitor/RN versions that support it. |
| Data safety form matches the code | Google Play User Data policy; Data safety section | Compare `track.analytics.*`, `ai.*`, `pay.*`, `comm.*`, `perm.*`, `auth.accounts` and SDK collection with the form (ask) | Signal list vs form | Required (enforcement: update rejection or removal) | founder | Re-answer Data safety from the detected SDK list; disclose encryption in transit and deletion option. |
| Account deletion in-app and via web link | Google Play account deletion requirement (since 2024) | `account.delete_endpoint` reachable both in app and on web without the app; URL entered in Data safety | Route file:line + public URL | Blocker if accounts exist and no deletion path found in code | engineer | Add in-app deletion and a public web page that accepts deletion requests; enter the URL in Play Console. |
| Target API level | Google Play target API requirement | `targetSdkVersion` in `android/variables.gradle` / `build.gradle` / `app.json` | File:line + value | Blocker if < 36 for new apps/updates after 31 Aug 2026 (extension to 1 Nov 2026); existing apps < 35 lose discoverability | engineer | Raise `targetSdkVersion` to 36 and test runtime-permission and edge-to-edge changes. |
| Developer verification and app registration | Play Console requirements; Android developer verification | Console-only: identity verified (individual: government ID; organisation: D-U-N-S) and app registered | Answer | Required (unregistered apps risk removal since 30 Sep 2026; install blocks in BR/ID/SG/TH, global 2027+) | founder | Complete verification and register every package name in Play Console. |
| Sensitive permission declarations | Play Permissions policy | Manifest: `ACCESS_BACKGROUND_LOCATION`, `READ_SMS`/`READ_CALL_LOG`, `QUERY_ALL_PACKAGES`, `MANAGE_EXTERNAL_STORAGE` | Manifest line | Blocker if declared without a qualifying core use and console declaration | engineer | Remove or justify in the Permissions declaration form with video. |
| Photo and video permissions | Play photo/video permissions policy | `READ_MEDIA_IMAGES`/`READ_MEDIA_VIDEO` in manifest (Capacitor camera plugin adds them) | Manifest line | Required | engineer | Use the Android photo picker unless photos are core functionality; remove the permissions. |
| Prominent disclosure and consent | Play User Data policy | In-app disclosure screen before collecting personal/sensitive data not expected from the app's function (location, contacts, `perm.*`) | Screen file:line or "not detected" | Required | engineer | Show an in-app disclosure stating data, purpose and use, then request consent. |
| Advertising ID | Play Advertising ID policy | `com.google.android.gms.permission.AD_ID` in manifest; linking ad ID to PII or persistent IDs | Manifest line + SDK init | Required | engineer | Declare AD_ID only if used; never link to PII without consent; respect opt-out; not for child users. |
| Health data | Play Health Content and Services; Health Connect | `perm.health` | Manifest/plugin line | Required (Health apps declaration form) | founder | Complete the Health apps declaration; request only needed Health Connect data types; privacy policy covers health data. |
| Families policy | Play Families policy | Target audience includes children | Answer | Required (see minors.md) | founder | Apply minors.md (Families SDKs only, no ad ID for kids). |
| Play Billing for digital goods | Play Payments policy | `pay.stripe` etc. for digital content in Android app | Payment UI file:line | Required (see payments.md) | founder | Apply payments.md (Play Billing or user-choice/alternative billing where available). |
| DSA trader status (EU) | DSA Art. 30–31 via Play Console | Console-only: trader declaration and public contact details | Answer | Required (confirm in Play Console; enforcement date not verified from a Google primary page) | founder | Declare trader status in Play Console account details. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2022-06-30 | Apple in-app account deletion (5.1.1(v)) | in force |
| 2024-05-01 | Apple required-reason API declarations in privacy manifests | in force |
| 2024-05-31 | Google Play account deletion (in-app + web) after extension | in force |
| 2024-10-16 | Apple: trader status required to submit updates for EU | in force |
| 2025-02-17 | Apple: apps without trader status removed from EU storefronts | in force |
| 2026-01-31 | Apple: new age rating questionnaire answered | in force |
| 2026-04-28 | Apple: uploads built with Xcode 26 / iOS 26 SDK | in force |
| 2026-08-31 | Google Play: new apps/updates target API 36; existing apps ≥ 35 | in force (extension to 2026-11-01 on request) |
| 2026-09-09 | Apple: uploads must target iOS 13 or later | in force |
| 2026-09-30 | Google Play: apps registered for developer verification; installs blocked in BR/ID/SG/TH for unregistered apps | in force |
| 2026-11-01 | Google Play: end of target-API extension | upcoming |
| 2027-01-27 | Google Play: Contact Picker for non-core contacts use; location button recommended; `READ_CALL_LOG` no longer for phone-call verification | upcoming |

## Needs a lawyer
- Whether the company is a "trader" under the DSA (individual hobby developers can declare non-trader); what address to publish.
- Custom EULA versus Apple's standard EULA; consumer-law terms that the standard EULA does not cover.
- Export classification if the app ships custom or non-standard cryptography.
- Steering/link-out rules for digital goods per storefront (US, EU DMA, Japan, Korea) — see payments.md.
