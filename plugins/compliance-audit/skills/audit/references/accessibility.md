# Accessibility — EAA / EN 301 549, ADA, UK Equality Act, store labels
last-reviewed: 2026-10-13
applies-when: EU/EEA in markets and (size answer is not micro or the user opts in), or US in markets with a public-facing B2C product; UK rows only when UK in markets
sources:
- https://www.w3.org/TR/WCAG21/
- https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf
- https://eur-lex.europa.eu/eli/dir/2019/882/oj
- https://commission.europa.eu/strategy-and-policy/policies/justice-and-fundamental-rights/disability/union-equality-strategy-rights-persons-disabilities-2021-2030/european-accessibility-act_en
- https://www.ada.gov/resources/web-guidance/
- https://www.ada.gov/resources/2024-03-08-web-rule/
- https://www.legislation.gov.uk/ukpga/2010/15/contents
- https://developer.apple.com/accessibility/
- https://developer.apple.com/help/app-store-connect/manage-app-accessibility/overview-of-accessibility-nutrition-labels
- https://developer.android.com/guide/topics/ui/accessibility
- https://github.com/dequelabs/axe-core
- https://developer.chrome.com/docs/lighthouse/overview

## Who it applies to and thresholds

| Scope point | Rule |
|---|---|
| EU — EAA | Directive 2019/882, applied from 28 Jun 2025 to consumer e-commerce services (website/app sales to consumers), e-books, consumer banking, e-communications, transport ticketing. Presumption of conformity via EN 301 549 (which embeds WCAG 2.1 AA). Microenterprise service providers (<10 staff, ≤€2M) exempt (Art. 4(5)); B2B-only out. Transition: service contracts concluded before 28 Jun 2025 may continue unchanged until 28 Jun 2030. |
| EU — default | Micro entity → every row below is Recommended (opt-in). Non-micro B2C e-commerce → Required. |
| US — ADA Title III | Courts in most circuits treat consumer websites/apps of businesses open to the public as covered; no DOJ rule for private entities. Thousands of web-accessibility suits per year, mostly NY/CA/FL; demand letters reach small businesses. WCAG 2.1 AA is the de facto target. Severity: Recommended. |
| US — ADA Title II | DOJ 2024 rule (WCAG 2.1 AA) binds state/local governments only; interim final rule of 20 Apr 2026 moved compliance to 26 Apr 2027 (≥50k population) and 26 Apr 2028 (smaller). Relevant only if you sell to public entities (they will push it into contracts). |
| UK | Equality Act 2010 s.20, s.29: service providers must make reasonable adjustments, no size exemption; no fixed technical standard (WCAG 2.2 AA is the usual benchmark). Public Sector Bodies Regulations 2018 apply only to public bodies. |
| Stores | Apple Accessibility Nutrition Labels (App Store Connect, launched 2025) are voluntary now; Apple says they will become required for new apps and updates over time. Google Play has no equivalent label. |
| Reuse | Web checks below map to the a11y catalog in the ui-change-guard plugin (`skills/review-ui-change/references/checks.md` §5). Use those signals when reviewing templates; this table adds the legal mapping. |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| Form inputs have accessible names | WCAG 1.3.1, 3.3.2, 4.1.2; EN 301 549 9.x | `<input>`/`<select>`/`<textarea>` without `<label for>`, `aria-label` or `aria-labelledby` (placeholder only) | Template file:line | Required (EAA non-micro) / Recommended | engineer | Add visible `<label>` bound by `for`/`id`. |
| Text alternatives for images | WCAG 1.1.1 | `<img>` without `alt`; icon-only buttons without accessible name | Template file:line | Required / Recommended | engineer | Meaningful `alt`; `alt=""` for decorative; `aria-label` on icon buttons. |
| Colour contrast | WCAG 1.4.3 (4.5:1 text, 3:1 large), 1.4.11 (3:1 UI) | CSS tokens: light grey on white, text on images | CSS file:line + computed ratio | Required / Recommended | engineer | Adjust tokens to meet ratios; check dark mode too. |
| Not colour alone | WCAG 1.4.1 | Error/success shown only by red/green | Template/CSS line | Required / Recommended | engineer | Add icon or text. |
| Visible focus | WCAG 2.4.7 | `outline: none`/`outline: 0` without `:focus-visible` style | CSS file:line | Required / Recommended | engineer | Provide a visible `:focus-visible` ring. |
| Keyboard operable, no traps | WCAG 2.1.1, 2.1.2 | `<div>`/`<span>` with click handlers, positive `tabindex`, modals without focus trap/Escape/return | Template/JS file:line | Required / Recommended | engineer | Use `<button>`/`<a>`; manage focus in dialogs (`aria-modal`, Escape, restore focus). |
| Headings, landmarks, language | WCAG 1.3.1, 2.4.1, 2.4.6, 3.1.1 | Missing `<h1>`, skipped levels, no `<main>`/skip link, missing `<html lang>` | Base template line | Required / Recommended | engineer | One `<h1>`, ordered headings, landmarks, skip link, `lang`. |
| Error identification and suggestions | WCAG 3.3.1, 3.3.3, 4.1.3 | Form errors not tied to fields (`aria-describedby`), async results without `aria-live` | Template/JS line | Required / Recommended | engineer | Inline error text linked to the field; status region for async messages. |
| Reflow and zoom | WCAG 1.4.4, 1.4.10; iOS input zoom | `user-scalable=no` or `maximum-scale=1` in viewport; text inputs with `font-size` < 16px (class or inline `style=`) | Template/CSS line | Required / Recommended | engineer | Allow zoom; inputs ≥16px; layouts reflow at 320px width. |
| Reduced motion | WCAG 2.3.3 (AAA, best practice), 2.2.2 | Animations without `prefers-reduced-motion` guard; autoplaying carousels without pause | CSS/JS line | Recommended | engineer | Wrap motion in `@media (prefers-reduced-motion: no-preference)`; add pause controls. |
| Touch target size | WCAG 2.5.8 (2.2 AA, 24px); platform guidance 44pt/48dp | Small icon buttons | CSS line | Recommended | engineer | Minimum 44×44 px hit area. |
| Captions and transcripts | WCAG 1.2.2, 1.2.3 | `<video>`/audio without `<track kind="captions">` | Template line | Required / Recommended | founder | Caption prerecorded video; transcript for audio. |
| Native screen-reader labels | EN 301 549 ch. 11; WCAG 4.1.2 | iOS: `accessibilityLabel`; Android: `contentDescription`; RN: `accessibilityLabel`/`accessible`; Capacitor: the web rows above apply inside the WebView | Screen file:line | Required / Recommended | engineer | Label every interactive element; test with VoiceOver and TalkBack. |
| Dynamic Type / font scaling | WCAG 1.4.4; EN 301 549 11.7 | iOS fixed font sizes without `UIFontMetrics`/Dynamic Type; Android `dp` for text instead of `sp`; RN `allowFontScaling={false}`; Capacitor viewport locks | File:line | Recommended | engineer | Support system text size up to 200% without loss of content. |
| Accessibility statement / service information | EAA Art. 13, Annex V; UK reasonable adjustments | Page listing conformance level, known gaps, contact for alternative access (grep `accessibility` route/template) | Page path or "not detected" | Required (EAA non-micro) / Recommended | founder | Publish an accessibility statement with contact channel and date. |
| Accessible alternative channel | Equality Act 2010 s.20; ADA Title III | Support email/phone published | Contact page path | Recommended | founder | Offer an alternative channel for users who cannot complete a flow. |
| Accessibility Nutrition Labels | App Store Connect | Console-only | Answer | Note | founder | Declare only features actually supported (VoiceOver, Voice Control, Larger Text, Dark Interface, Sufficient Contrast, Reduced Motion, Captions). |
| Page titles | WCAG 2.4.2 | `<title>` missing or identical across pages | Template line | Required / Recommended | engineer | Unique, descriptive `<title>` per page/route. |
| Link purpose | WCAG 2.4.4 | Links reading "click here"/"more" without context | Template line | Recommended | engineer | Descriptive link text or `aria-label`. |
| Input purpose (autofill) | WCAG 1.3.5 | Login/signup/checkout inputs without `autocomplete` (`email`, `current-password`, `one-time-code`) | Template line | Required / Recommended | engineer | Add correct `autocomplete` tokens. |
| Orientation not locked | WCAG 1.3.4 | `orientation` locked in `capacitor.config.*`/`app.json`/Info.plist `UISupportedInterfaceOrientations` without need | Config line | Recommended | engineer | Support both orientations unless essential. |
| Timeouts adjustable | WCAG 2.2.1 | Short session/OTP expiry without warning or extension | Auth code file:line | Recommended | engineer | Warn before timeout and allow extension. |
| Accessible authentication | WCAG 3.3.8 (2.2 AA) | Image/puzzle CAPTCHA, paste blocked on password/OTP fields (`onpaste`) | Template/JS line | Recommended | engineer | Allow paste and password managers; use non-cognitive bot checks. |
| Dragging alternatives | WCAG 2.5.7 (2.2 AA) | Drag-only reordering/sliders | JS/component line | Recommended | engineer | Provide buttons or keyboard alternative. |
| Consistent help | WCAG 3.2.6 (2.2 A) | Help/contact link in different places across pages | Templates | Recommended | founder | Keep help link in the same place on every page. |
| Instructions not sensory-only | WCAG 1.3.3 | Copy like "tap the green button on the right" | Template/string line | Recommended | founder | Refer to labels, not colour/position alone. |
| Language of parts | WCAG 3.1.2 | Mixed-language content (e.g. Hebrew/English) without `lang` on the element; RTL without `dir` | Template line | Recommended | engineer | Set `lang`/`dir` on passages in another language. |
| Documents and PDFs | EN 301 549 ch. 10; WCAG 1.1.1, 1.3.1 | Downloadable PDFs (invoices, terms) generated without tags | Generator code line | Recommended | engineer | Generate tagged PDFs or offer HTML equivalents. |
| Automated + manual testing in CI | Good practice (supports EN 301 549 conformity evidence) | `axe-core`/`@axe-core/playwright`/`pa11y`/Lighthouse in `package.json` or CI | File path or "not detected" | Recommended | engineer | Add axe checks to Playwright/CI; manual VoiceOver/TalkBack pass before release; Xcode Accessibility Inspector, Android Accessibility Scanner. |
| Overlay widgets are not compliance | ADA case law; EAA | Third-party overlay scripts (grep `accessibe`, `userway`, `audioeye`) | Script tag line | Recommended | founder | Fix the underlying markup; overlays do not prevent suits. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2010-10-01 | UK Equality Act 2010 service-provider duties | in force |
| 2025-06-28 | EAA applies to new products and services (non-micro service providers) | in force |
| 2026-04-20 | DOJ interim final rule moving Title II dates | in force |
| 2027-04-26 | ADA Title II web/mobile rule: public entities ≥50k population | upcoming (public entities only) |
| 2028-04-26 | ADA Title II: smaller public entities and special districts | upcoming (public entities only) |
| 2030-06-28 | EAA transition ends for service contracts concluded before 28 Jun 2025 | upcoming |

## Needs a lawyer
- Whether the B2C service is in EAA scope (e-commerce service definition) and whether the microenterprise exemption applies.
- Disproportionate-burden claims under EAA Art. 14 and the notification they require.
- US demand letters or ADA complaints: response strategy and settlement.
- Accessibility clauses demanded by public-sector or enterprise customers (Title II, Section 508 VPAT).
