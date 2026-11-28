# Test areas

The catalogue the plan skill picks test items from. Keep only what the app has: an area with nothing to test in this app gets "n/a" and the reason in the coverage matrix, never invented items. Each item you write traces to a flow, a screen or a source file.

"Applies to" uses: **web** (runs in a browser: web only, or the web build of a Capacitor or Expo app), **capacitor** (web code in a native shell), **native** (React Native, Expo, Swift, Kotlin). Test every UI item on every platform copy, at every chosen size and orientation, unless the row says otherwise.

## Logic

| Check | Applies to | What to test |
|---|---|---|
| User flows end to end | all | Every `UF-NNN`, or every flow found in the code: precondition, steps, the assertable outcome. |
| Existing suites | all | Run the project's unit and integration tests and `make test-user-flows` when present; a failure is a bug. |
| Validation | all | Required fields, formats, lengths and ranges, server-side checks behind client-side ones, the messages shown. |
| Permissions and roles | all | Each role sees and does only what it may; direct URLs and API calls to forbidden pages and actions are refused. |
| Data create / read / update / delete | all | Each record type: created, listed, shown, edited, deleted; the change persists after a reload; related data stays consistent. |
| Errors and edge cases | all | Server errors, not-found, empty and maximum inputs, special characters and emoji, time zones and dates, zero and many items. |
| Concurrency | all | Double submit (double click, Enter twice), the same record edited in two tabs or devices, actions racing a background job. |
| Session expiry | all | Expired or revoked session mid-flow: the user is sent to log in and lands back where they were; no data is lost silently. |

## UI

| Check | Applies to | What to test |
|---|---|---|
| Layout, overflow and clipping | all | Nothing cut off, overlapping or scrolling sideways; containers hold their content. |
| Breakpoints and each configured size | web, capacitor | Each chosen size (desktop 1440x900, tablet 820x1180, phone 390x844, small phone 360x640), and the widths just either side of each CSS breakpoint. |
| Device sizes | native | Each chosen device class: phone, small phone and tablet simulators or emulators. |
| Portrait, landscape and rotation mid-flow | all, when landscape is chosen | Each screen in both orientations; rotate during a form, a modal, a video and a scroll: state, input and scroll position survive. |
| Typography and truncation | all | Font loading, line height, heading levels; long words and names wrap or truncate with an ellipsis, never overflow. |
| Color, contrast and dark mode | all; dark mode when confirmed | Brand colors used consistently; text contrast; in dark mode every screen, including modals, inputs and images with transparent backgrounds. |
| Images and icons | all | Loaded, sharp on high-density screens, right aspect ratio, alt text, broken-image fallback. |
| States | all | Empty, loading, error, success and disabled states of every list, form, button and data view. |
| Forms | all | Validation messages beside the field, keyboard type per field on mobile (email, number, phone), autofill and password managers, inputs at least 16px on iOS (smaller zooms the page on focus), submit with Enter. |
| Navigation, back and deep links | all | Every menu and link, browser and hardware back, the iOS swipe back, deep links and shared URLs opening the right screen, logged in and out. |
| Modals, sheets and toasts | all | Open and close (button, Escape, tap outside, back), focus stays inside, background does not scroll, toasts do not cover controls. |
| Scrolling and sticky elements | all | Long pages and lists, infinite scroll and pagination, sticky headers and footers, scroll position after going back. |
| Touch targets and gestures | phone and tablet sizes, native | Targets at least 44x44pt, spacing between them, swipe, pull to refresh, long press, pinch where used. |
| Hover, focus and active | web | Each interactive element shows hover, visible focus and pressed states; nothing depends on hover on touch screens. |
| Animation and transitions | all | Smooth, not janky; no layout jump at the end; they do not block input. Record these, since a still image cannot show them. |
| Long content, RTL and languages | all; RTL and languages when confirmed | Long text and many items; in RTL, mirrored layout and icons; in each language, longer strings, dates, numbers and currency. |
| Cross-browser | web | Each browser copy: Chromium and WebKit, plus Firefox when supported. Compare the same screens across them. |
| Visual consistency | all | Spacing, alignment, components and colors match across screens and platforms. |

## Native shell

Applies to capacitor and native.

| Check | What to test |
|---|---|
| Safe areas and notch | Content clear of the notch, Dynamic Island, home indicator and rounded corners, in both orientations. |
| Status bar | Readable over each screen's background, in light and dark mode. |
| Keyboard overlap | The focused input and the submit button stay visible above the keyboard; the keyboard closes when it should. |
| Splash screen | Shown on cold start, no white flash, hands over to the first screen cleanly. |
| Permission prompts and denial | Each prompt (camera, location, notifications, ...) appears with its purpose text; a denial shows a message with a way to Settings, never a silent no-op; a later grant works. |
| Background and resume | Leave the app mid-flow and return; after a long background; after the OS kills it. State and session survive. |
| Offline and slow network | Airplane mode and a throttled network: clear message, no lost input, recovery when the network returns. |
| Tablet layouts | iPad and Android tablet use the room (not a stretched phone layout), split view and slide over on iPad where supported. |

## Accessibility

| Check | Applies to | What to test |
|---|---|---|
| Keyboard | web | Every action reachable and usable with the keyboard alone; no keyboard trap. |
| Screen-reader labels | all | Buttons, icons, images and inputs have names (VoiceOver, TalkBack, or the accessibility tree in the browser). |
| Focus order | all | Focus moves in reading order and lands sensibly after a modal, a route change or an error. |
| Contrast | all | Text and controls meet WCAG AA contrast, in every theme. |
| Text scaling | all | Browser zoom to 200%, iOS Dynamic Type and Android font scale at the largest size: nothing clipped or overlapping. |
| Reduced motion | all | With reduced motion on, large animations are toned down or off. |

## Performance

| Check | Applies to | What to test |
|---|---|---|
| Load and interaction time | all | First load and each main screen; the response to taps and clicks; note the times. |
| Slow network | all | A throttled network (for example Slow 4G): loading states shown, no timeouts on normal actions. |
| Large data sets | all | Lists and tables with many records: scrolling, search, pagination stay usable. |
| Memory on mobile | capacitor, native, web at phone size | A long session through many screens: no growing slowness, no crash, no reload by the OS. |
