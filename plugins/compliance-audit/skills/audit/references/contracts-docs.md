# Contracts and legal documents
last-reviewed: 2026-10-13
applies-when: always (every audit); B2B rows when answer = B2B/both; consumer rows when answer = B2C/both
sources:
- https://developer.apple.com/app-store/review/guidelines/
- https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
- https://support.google.com/googleplay/android-developer/answer/9858738
- https://play.google/developer-content-policy/
- https://eur-lex.europa.eu/eli/dir/2000/31/oj
- https://eur-lex.europa.eu/eli/dir/2011/83/oj
- https://eur-lex.europa.eu/eli/dir/1993/13/oj
- https://eur-lex.europa.eu/eli/reg/2022/2065/oj
- https://commission.europa.eu/business-economy-euro/doing-business-eu/contract-rules/digital-contracts/digital-contract-rules_en
- https://www.legislation.gov.uk/ukpga/2015/15/contents
- https://eur-lex.europa.eu/eli/reg/2016/679/oj
- https://railway.com/legal/dpa
- https://www.tmdn.org/tmview/
- https://tmsearch.uspto.gov/
- https://www.euipo.europa.eu/en

## Who it applies to and thresholds

| Scope point | Rule |
|---|---|
| Every product | Needs a privacy policy (law in every default jurisdiction + Apple 5.1.1(i) + Google Play User Data policy) and terms of use. |
| Native apps | Apple applies its Licensed Application EULA (stdeula) unless a custom EULA is entered in App Store Connect; Google Play has no default EULA — your own terms govern. |
| Consumers (B2C) | EU/UK consumer law overrides contract: statutory rights (conformity, withdrawal, unfair-terms control) cannot be waived. US: arbitration/class-waiver enforceable in principle, state law varies. |
| B2B | GDPR Art. 28 makes you a processor for customer data: you must offer a DPA and disclose sub-processors. |
| Content of the privacy policy | Jurisdiction-specific items live in privacy-gdpr-uk.md, privacy-us.md, privacy-israel-singapore.md; this module checks presence, linking and structure. |
| Ownership | Most rows are founder/lawyer work; engineer only wires links and pages. |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| Privacy policy published and linked in-app and in store metadata | GDPR Art. 13; Apple 5.1.1(i); Google Play User Data policy | `legal.privacy_policy_page`; grep settings/signup templates and `mobile.*` screens for the link | Page path; template file:line of link | Blocker if missing and `mobile.ios`/`mobile.android` (store rejection); Required otherwise | founder | Publish at a stable URL; link from signup, settings, store listing. |
| Privacy policy covers each jurisdiction's mandatory items | Cross-ref privacy modules | Grep policy for retention, rights, contact, vendors from signals (`ai.*`, `track.analytics.*`, `pay.*`) | Missing items list | Required | founder | Add missing sections; list each vendor detected by signals. |
| Terms of service / EULA | Contract law; Apple stdeula; Google Play | `legal.terms_page`; App Store Connect custom EULA answer | Page path or "not detected" | Required | founder | Publish terms; if using Apple stdeula, make your terms consistent with it and state Apple's position for iOS. |
| Acceptance captured at signup | Contract formation (clickwrap) | `auth.accounts` signup form: checkbox or "By signing up you agree" + links; store version accepted | Signup template file:line | Required | engineer | Add clickwrap with links; store `terms_version` + timestamp per user. |
| Acceptable use policy | Contract; DSA Art. 14 (terms must state content restrictions) if UGC/hosting | Answer: UGC/hosting present; `docs/legal/` | Terms section | Recommended (Required if users publish content) | founder | Add AUP section; describe moderation and appeal. |
| DPA offered to B2B customers | GDPR Art. 28(3) | Answer B2B; `/dpa` page or `docs/legal/dpa*` | Path or "not found" | Required (B2B only) | lawyer | Publish a DPA mirroring Art. 28(3) terms, with SCCs for exports. |
| Sub-processor page | GDPR Art. 28(2), 28(4) | Page listing vendors from `deploy.railway`, `pay.*`, `ai.*`, `comm.*`, `track.analytics.*` | Missing vendors | Required (B2B); Recommended (B2C, via privacy policy recipients) | founder | Publish list + change-notification mechanism (Railway itself gives 10 days' notice). |
| Cookie policy | ePrivacy Art. 5(3); PECR reg. 6 (clear and comprehensive information) | `web.cookies`, `track.analytics.*` present; `consent.banner` links to a cookie list | Banner/template file:line | Required when non-essential cookies used | founder | List each cookie/SDK, purpose, duration, provider; link from banner. |
| Refund / cancellation / withdrawal policy | CRD 2011/83 Art. 6, 9, 16(m); UK CCRs 2013; store refund rules | `pay.*` present; grep terms for `refund`, `cancel`, `withdrawal` | Terms section or "not found" | Required (B2C + `pay.stripe`/`pay.paddle`/`pay.lemonsqueezy` direct sales); Note for IAP-only (store handles refunds) | founder | State 14-day withdrawal right and the express-consent waiver for immediate digital supply; cancellation steps. |
| Auto-renewal disclosure | Cross-ref payments.md | `pay.*` present → run payments.md checks | Per payments.md | Required (see payments.md) | founder | Apply payments.md fixes. |
| Liability cap, warranty disclaimer, indemnity | Contract law; Unfair Terms Dir. 93/13; UK CRA 2015 Part 2, s.31, s.65 | Terms text | Clause present/absent | Recommended; Required to carve out non-excludable consumer liability (death/personal injury, statutory rights) | lawyer | Cap liability for B2B; for consumers add "nothing limits your statutory rights" carve-out. |
| Governing law and venue | Rome I Art. 6 (consumer keeps home-law protection); Brussels I Art. 18 | Terms text | Clause | Recommended | lawyer | Choose law/venue; add consumer-protection savings clause. |
| Arbitration / class waiver (US) | Federal Arbitration Act; state law | Terms text; answer US in markets | Clause | Recommended | lawyer | Decide with counsel; include opt-out window and mass-arbitration protocol if used. |
| IP ownership and licence grant to users | Contract; Apple stdeula §a | Terms text | Clause | Recommended | lawyer | Grant a limited, revocable, non-transferable licence; reserve IP. |
| User content licence | Contract; DSA Art. 14 if hosting | Answer UGC; upload routes (grep `UploadFile`, `multipart`) | Route file:line | Required when users upload content | lawyer | Take only the licence needed to run the service; state deletion behaviour. |
| Termination and suspension | Contract; DSA Art. 17 statement of reasons (hosting) | Terms text; `account.delete_endpoint` | Clause | Recommended | founder | State grounds, notice, data export window on termination. |
| Notice of changes to terms | Unfair Terms Dir. 93/13 Annex (j); UK CRA Sch. 2 | Terms text; `comm.email` for notification | Clause | Recommended | founder | Give advance notice of material changes by email/in-app; keep version history. |
| Company identity / imprint | E-Commerce Dir. 2000/31 Art. 5; CRD Art. 6(1)(b)–(c); DSA trader info (app-stores.md) | grep footer/about/contact templates for legal name, geographic address, email, registration no., VAT no. | Template file:line or "not found" | Required (EU/UK users); Blocker for EU store distribution without DSA trader status | founder | Publish imprint; match App Store Connect / Play Console trader details. |
| Israel/Singapore company identity | Local company law (see privacy-israel-singapore.md) | grep footer/imprint templates for company number (Israel ח.פ., Singapore UEN) | Footer | Recommended | founder | Add registration number to imprint and invoices. |
| Support/contact URL in store metadata | Apple App Store Connect (Support URL required); Google Play (contact email required) | Store metadata answer; `/support` or `/contact` route | Route/template file:line | Blocker for store submission if missing | founder | Publish a support page with working contact email. |
| Account deletion web URL | Google Play User Data policy (account deletion) | `account.delete_endpoint` reachable on web without the app | Route file:line | Blocker for Play distribution with `auth.accounts` (see app-stores.md) | engineer | Publish a web deletion page and enter it in Play Console Data safety. |
| Subscription terms link at point of sale | Apple 3.1.2(c) + DPLA Schedule 2; Google Play Subscriptions policy | `pay.storekit`/`pay.revenuecat`/`pay.playbilling` paywall screen links terms and privacy | Paywall file:line | Blocker for review if missing (see payments.md) | engineer | Add terms + privacy links and renewal wording on the paywall. |
| Age and eligibility clause | Contract; COPPA/GDPR Art. 8 (minors.md) | Terms text states minimum age; signup age gate if answer says under-16 users possible | Clause | Recommended | founder | State minimum age consistent with store age rating. |
| AI features disclosed in terms | Cross-ref ai-features.md | `ai.*` present; terms mention AI outputs, accuracy, user responsibility | Clause | Recommended | founder | Add AI section: no guarantee of accuracy, prohibited uses, output ownership. |
| DSA points of contact (intermediary services) | DSA Art. 11–12 | Answer UGC/hosting/messaging; contact page lists single point of contact for authorities and users | Page path | Required for intermediary services with EU users | founder | Publish electronic contact points and languages. |
| B2B order form / MSA and SLA | Contract | Answer B2B; `docs/legal/msa*`, `sla*` | Path or "not found" | Recommended (B2B only) | lawyer | Use an MSA + order form; keep SLA promises within what Railway's own terms support. |
| Trademark clearance before launch | Trade mark law (EUTMR, Lanham Act, UK TMA 1994) | Answer: search done? product name in `app.json`/`Info.plist`/`<title>` | Product name | Recommended | founder | Search TMview, USPTO, EUIPO for the name in your classes (9, 42); consider filing. |
| Open-source notices file | OSS licence attribution duties (licensing-sbom.md) | `NOTICE`, `THIRD-PARTY-LICENSES*`, in-app "Licences" screen in `mobile.*` | Path or "not found" | Required for distributed apps with Apache-2.0/BSD/MIT deps; Recommended for SaaS | engineer | Generate notices file from license_scan output; ship in app bundle. |
| Legal docs version-controlled | Accountability (GDPR Art. 5(2)) | `docs/legal/` exists with policy/terms sources | Path or "not found" | Recommended | founder | Keep sources in `docs/legal/` with change log. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2014-06-13 | Consumer Rights Directive (14-day withdrawal, pre-contract info) | in force |
| 2015-10-01 | UK Consumer Rights Act 2015 | in force |
| 2022-01-01 | Digital Content Directive 2019/770 (conformity of digital content/services) | in force |
| 2024-02-17 | DSA applies to all intermediary services (Art. 14 terms transparency) | in force |

## Needs a lawyer
- Final drafting of terms, liability cap and consumer carve-outs per market.
- Arbitration/class-waiver enforceability in target US states.
- Whether the product is an "intermediary/hosting service" under the DSA (UGC, messaging).
- DPA negotiation with enterprise customers; SCC module selection.
- Trademark conflicts found in clearance searches.
