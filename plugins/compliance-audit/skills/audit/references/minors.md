# Minors — COPPA, store kids rules, GDPR Art. 8, UK Children's Code, age-verification laws
last-reviewed: 2026-10-13
applies-when: B2C product and the minors answer is "yes" or "unlikely, not enforced" (no age gate); also when the app is in a Kids/Families store category
sources:
- https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-312
- https://eur-lex.europa.eu/eli/reg/2016/679/oj
- https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/
- https://www.legislation.gov.uk/ukpga/2023/50/contents
- https://developer.apple.com/app-store/kids-apps/
- https://developer.apple.com/app-store/review/guidelines/
- https://support.google.com/googleplay/android-developer/answer/9893335
- https://capitol.texas.gov/BillLookup/History.aspx?LegSess=89R&Bill=SB2420
- https://mgaleg.maryland.gov/mgawebsite/Legislation/Details/hb0603?ys=2024RS
- https://www.cooley.com/news/insight/2026/2026-03-30-netchoice-v-bonta-ninth-circuit-narrows-injunction-against-californias-ageappropriate-design-code-act

## Who it applies to and thresholds

| Scope point | Rule |
|---|---|
| COPPA (US, under 13) | Applies to services directed to children (subject matter, visuals, ads, audience) or with **actual knowledge** that they collect personal information from a child under 13. No size threshold. Amended Rule published 22 Apr 2025, effective 23 Jun 2025, **compliance date 22 Apr 2026**. Civil penalties > $53,000 per violation (inflation-adjusted). |
| Mixed audience | Child-directed but not primarily for children → may age-screen neutrally and apply COPPA only to users under 13 (amended Rule codifies "mixed audience"). |
| GDPR Art. 8 | Consent-based processing of information-society services offered directly to a child requires parental authorisation below the national age: 16 by default; member states set 13–16 (e.g. 13 BE/DK/FI/SE/PT, 14 AT/ES/IT, 15 FR/CZ/GR, 16 DE/NL/IE/PL). UK: 13. |
| UK Children's Code (AADC) | ICO statutory code (since 2 Sep 2021) for online services **likely to be accessed** by under-18s in the UK — not just child-directed services. 15 standards. |
| UK Online Safety Act | Only user-to-user (UGC, chat between users, comments) and search services. Children's risk assessment + Protection of Children Codes from 25 Jul 2025; "highly effective age assurance" where primary priority content (porn, self-harm, suicide, eating disorders) can appear. Pure tools without UGC: out of scope. |
| US state laws | CA AADC (Ninth Circuit 12 Mar 2026 partly narrowed the injunction; parts may be enforceable — confirm via source); MD Kids Code (in force 1 Oct 2024, litigation pending — confirm via source); Texas SB 2420 App Store Accountability Act (effective 1 Jan 2026; district-court injunction 23 Dec 2025 stayed by Fifth Circuit mid-2026, so enforceable — confirm via source); Utah app-store law duties delayed to 6 May 2027 (HB 498). Several states require teen opt-in for sale/targeted ads (see privacy-us.md). |
| Singapore / Israel | Singapore: PDPC Advisory Guidelines on Children's Personal Data (2024) — under-13s need parental consent; children's data treated as sensitive, higher security. Israel: no statutory digital-consent age; minors (<18) act with guardian consent under the Legal Capacity Law → Needs a lawyer. |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| Neutral age screen (no default age, no "you must be 13+" hint before entry) for general/mixed-audience services | COPPA 16 CFR 312.2 (mixed audience), FTC guidance | Grep signup screens/routes for `birth`, `dob`, `date_of_birth`, `age`, `year_of_birth` | Signup file:line or "not detected" | Required when minors answer is "unlikely, not enforced"; Blocker for mixed-audience/child-directed with no screen | engineer | Ask birth date neutrally; block or route under-13 to a parental-consent flow; set a cookie/flag to prevent back-button retries. |
| Verifiable parental consent (VPC) before collecting PI from under-13s | COPPA 312.5 | Child flow: grep for parental email/consent tables | file:line or "not found" | Blocker if child-directed and PI collected without VPC | founder | Use an approved VPC method (card transaction, ID + face match, knowledge-based, text-plus) or do not collect PI. |
| **Separate** VPC for disclosing children's PI to third parties (e.g. targeted ads, data sale) | COPPA 312.5(a)(2) (amended Rule) | Ad SDKs (grep `admob`, `google-mobile-ads`, `applovin`, `facebook-audience`, `unity-ads`) + `track.analytics.*` in child flows | SDK file:line | Blocker for child users | engineer | Disable third-party disclosure for children unless separate consent obtained; use contextual ads only. |
| Direct notice to parents + online notice listing third-party recipients by name/category and purposes | COPPA 312.4 (amended) | `legal.privacy_policy_page` children's section | Notice text | Required | founder | Add children's section and parent notice template. |
| Written data-retention policy published in the online notice; delete when no longer needed; no indefinite retention | COPPA 312.10 (amended) | Notice text + `retention.job` | Notice + job file:line | Required | founder | Publish retention periods for children's data; purge job. |
| Written information security program for children's PI (designated coordinator, annual risk assessment) | COPPA 312.8 (amended) | `docs/` security program | Path or "not found" | Required | founder | Write a short program document; apply security-baseline.md. |
| Biometric identifiers are personal information | COPPA 312.2 (amended definition) | `perm.biometrics`, face/voice templates, `perm.camera` with face detection | Feature file:line | Required | engineer | Treat as PI: VPC, minimise, delete. |
| Persistent identifiers for support of internal operations only, with notice | COPPA 312.5(c)(7) | `track.analytics.*` config in child mode | SDK init file:line | Required | engineer | Turn off ad IDs, IDFA/AAID, cross-app tracking for children (e.g. Firebase `setAnalyticsCollectionEnabled(false)` or child-directed treatment flags). |
| Child-directed treatment flags in ad/analytics SDKs | Google `tagForChildDirectedTreatment`, `tag_for_under_age_of_consent`; Play Families | Grep for those flags | file:line or "not found" | Required when children may use the app | engineer | Set flags when the user is a child or the app targets children. |
| Apple Kids Category rules: no third-party analytics/ads except permitted, parental gate before links out/purchases/requests for personal data | Apple App Review 1.3, 5.1.4 | `mobile.ios` + Kids category answer; grep for parental gate component | SDK + gate file:line | Blocker (store rejection) in Kids Category | engineer | Remove third-party trackers/ads, add parental gate. |
| Apple 5.1.4: apps for kids must comply with COPPA/GDPR-K; no sharing of children's data with third parties | Apple App Review 5.1.4 | As above | As above | Blocker (store rejection) | engineer | As above. |
| Google Play Families policy: target-audience declaration; only Families Self-Certified ad SDKs; no AAID/location from children; content suitable | Google Play Families policy | `mobile.android` + target audience includes under-13 | Ad SDK list + manifest permissions | Blocker (store rejection) | engineer | Declare audience accurately; use certified ad SDKs or none; remove `ACCESS_FINE_LOCATION` and ad ID for children. |
| App-store age signals for state laws (request age range, obtain parental consent via store for minors) | Texas SB 2420 (effective 1 Jan 2026; enforceable after Fifth Circuit stay — confirm via source); Utah (from 6 May 2027) | `mobile.ios`/`mobile.android`: grep `DeclaredAgeRange`, `AgeRangeService`, Play `AgeSignals` | file:line or "not detected" | Required (Texas users) — date-sensitive; Note for Utah | engineer | Integrate Apple Declared Age Range and Play Age Signals APIs; apply minor restrictions when signalled. |
| GDPR Art. 8 parental authorisation below national age when relying on consent | GDPR Art. 8; UK GDPR Art. 8 (13) | Consent-based features (analytics/marketing consent) + no age gate | Consent code file:line | Required (EU/UK in markets and minors possible) | engineer | Age gate + parental authorisation, or do not rely on consent for under-age users (disable consent-based processing). |
| UK Children's Code: high-privacy defaults, geolocation off by default, no nudge techniques, profiling off by default, DPIA, age-appropriate application | ICO Age Appropriate Design Code standards 2, 7, 10, 12, 13 | Default settings; `perm.location` default; streak/notification nudges; profiling flags | Settings defaults file:line | Required (UK users likely <18) | engineer | Defaults to private; location off unless needed; remove dark nudges; run a DPIA. |
| UK Online Safety Act: children's access assessment, children's risk assessment, age assurance where primary priority content possible | OSA 2023 ss.11–12, 35–37; Ofcom Protection of Children Codes (from 25 Jul 2025) | UGC signals: user-to-user messaging, comments, uploads | Feature file:line | Required when UGC + UK users; Note otherwise | founder | Do the Ofcom assessments; content moderation; age assurance if needed. |
| US state kids codes (CA AADC parts; MD Kids Code) — DPIA, high-privacy defaults, no profiling of children | CA Civ. Code §1798.99.28 ff.; MD Comm. Law §14-4801 ff. | As UK Children's Code row | As above | Recommended (litigation pending — confirm via source) | founder | Reuse UK Children's Code work. |
| Teen sale/targeted-ad opt-in | CCPA §1798.120(c); CT, OR, MD, NJ, MN, DE | Ad SDKs + teen users | SDK file:line | Required (see privacy-us.md) | engineer | Default no targeted ads for under-16/18. |
| Singapore children's data | PDPC Advisory Guidelines on Children's Personal Data (2024) | Age gate + parental consent for under-13 | Signup file:line | Required (SG users) | founder | Parental consent under 13; high-privacy defaults; heightened security. |
| AI vendor age limits | Anthropic/OpenAI terms (18+, or 13–17 with supervision where permitted) | `ai.*` + minors | Feature file:line | Required (see ai-features.md) | founder | Gate AI features by age per vendor terms. |
| No unsolicited contact from strangers; chat/DM off by default for minors | ICO Children's Code std. 7; OSA codes; Play Families | User-to-user messaging defaults | Settings file:line | Required when UGC + minors | engineer | Default DMs off/friends-only for minors; block and report tools. |
| No engagement nudges at night / streak pressure / notification spam for children | ICO Children's Code std. 13 (nudge techniques); several US state laws on minors' notifications — confirm via source | `comm.push` scheduling, streak features | Push job file:line | Recommended | engineer | Quiet hours for minor accounts; no loss-aversion streaks. |
| In-app purchases by children: parental approval and clear pricing | Apple 3.1.1/Ask to Buy; Play Families; FTC (unauthorised kids' charges cases) | `pay.*` + minors | Purchase flow file:line | Required | engineer | Parental gate before purchases in kids flows; no "coins" pricing that hides real cost. |
| Parental review and deletion of child's data on request | COPPA 312.6 | Parent dashboard or support process | Route or process doc | Required (child users) | engineer | Let parents review, refuse further collection and delete. |
| Education / school use | COPPA school-authorisation guidance; FERPA (US); Play "Teacher Approved" | Product sold to schools answer | Answer | Needs a lawyer when schools are customers | lawyer | School contracts with data-use limits; no ads to students. |
| Geolocation from minors | COPPA PI (precise geolocation); ICO std. 10; Play Families | `perm.location` + minors | Manifest/Info.plist + usage | Required | engineer | Off by default; coarse only if needed; no sharing. |
| Account deletion for minors without friction | Apple 5.1.1(v); Play account deletion | `account.delete_endpoint` | Route file:line | Required (see app-stores.md) | engineer | Same deletion path, no extra hurdles. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2021-09-02 | UK Children's Code enforced | in force |
| 2024-10-01 | Maryland Kids Code | in force (litigation pending — confirm via source) |
| 2025-06-23 | COPPA amended Rule effective | in force |
| 2025-07-25 | UK OSA Protection of Children Codes; highly effective age assurance | in force |
| 2026-01-01 | Texas SB 2420 app-store age verification (enforceable after Fifth Circuit stay — confirm via source) | in force |
| 2026-04-22 | COPPA amended Rule compliance date | in force |
| 2027-05-06 | Utah app-store age-verification duties (HB 498 delay) | future |

## Needs a lawyer
- Whether the service is "directed to children" or has actual knowledge of under-13 users (COPPA scope).
- Choice of verifiable parental consent method and FTC safe-harbor participation.
- Current enforceability of CA AADC, MD Kids Code, Texas SB 2420 provisions for this product.
- Israeli rules for minors' consent and parental involvement.
- UK Online Safety Act categorisation if the product has any user-to-user features.
- Which age-assurance method meets Ofcom's "highly effective" standard if UK user-to-user features exist.
- Validity of parental authorisation across EU member states with different Art. 8 ages.
- Whether teen-specific state laws (e.g. New York SAFE for Kids Act / Child Data Protection Act) apply — confirm via source.
