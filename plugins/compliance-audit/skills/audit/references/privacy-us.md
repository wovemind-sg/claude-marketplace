# Privacy — United States (state comprehensive laws, FTC, COPPA, CAN-SPAM, TCPA)
last-reviewed: 2026-10-13
applies-when: US in markets (answer), or US users reachable (`auth.accounts` + no geo-block); state-law rows only when a threshold below is met or the size answer is "unsure"
sources:
- https://iapp.org/resources/article/us-state-privacy-legislation-tracker/
- https://cppa.ca.gov/regulations/cpi_adjustment.html
- https://cppa.ca.gov/regulations/
- https://oag.ca.gov/privacy/ccpa
- https://oag.ca.gov/privacy/databreach/reporting
- https://globalprivacycontrol.org/
- https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-312
- https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-316
- https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-318
- https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-64/subpart-L/section-64.1200
- https://iapp.org/resources/article/state-data-breach-notification-chart/

## Who it applies to and thresholds

There is no federal comprehensive privacy law. 20 state comprehensive laws are in effect in 2026 (CA, VA, CO, CT, UT, TX, OR, MT, IA, DE, NH, NE, NJ, TN, MN, MD, IN, KY, RI, plus FL's narrow $1B-revenue law). Each applies per state of residence of the consumer, not the company's seat. Thresholds count consumers resident in that state per calendar year, usually excluding payment-only data.

| State law | Applies when (any one) | Notes |
|---|---|---|
| California CCPA/CPRA | Annual gross revenue > $26,625,000 (CPI-adjusted 1 Jan 2025; next adjustment 1 Jan 2027 — confirm via source); or buys/sells/shares PI of ≥100,000 CA consumers/households; or ≥50% revenue from selling/sharing PI | Covers employees and B2B contacts too. Regulations on ADMT, risk assessments, cybersecurity audits finalised 2025, phased from 2026. |
| Connecticut CTDPA | ≥35,000 consumers, or any sensitive data, or sells personal data (SB 1295 amendments from 1 Jul 2026; previously 100,000) — confirm via source | |
| Rhode Island RIDTPPA (1 Jan 2026) | ≥35,000 consumers, or ≥10,000 and >20% revenue from sale | |
| Montana MCDPA | ≥25,000 consumers, or ≥15,000 and >25% revenue from sale (SB 297, from 1 Oct 2025) | |
| Texas TDPSA, Nebraska NDPA | No numeric threshold; applies to anyone doing business in the state who is not an SBA-defined small business. Sale of sensitive data needs consent even for small businesses. | Micro SaaS usually = SBA small business → exempt except sensitive-data sale. |
| Minnesota MCDPA | 100,000 consumers or 25,000 + >25% revenue from sale; SBA small businesses exempt except the sensitive-data-sale consent rule | |
| Maryland MODPA | 35,000 consumers, or 10,000 + >20% revenue from sale; strict data minimisation, no sale of sensitive data at all | |
| Delaware, New Hampshire | 35,000 consumers (or 10,000 + >20% revenue from sale) | |
| VA, CO, UT, OR, IA, NJ, TN, IN, KY | Typically 100,000 consumers, or 25,000 (varies) + revenue-share-of-sale; UT and TN also require $25M revenue | Look up the exact row in the IAPP tracker. |

Micro-entity default: a company with fewer than 35,000 users in any single state and under $26.6M revenue is usually below every numeric threshold. Report as **Note** with the threshold stated, unless it sells/shares data or processes sensitive data (TX/NE/MN/CT rules still bite). Federal laws below (FTC Act, COPPA, CAN-SPAM, TCPA, HBNR, breach laws) have no size threshold.

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| Privacy notice accurate and complete (categories, purposes, sale/share, rights, how to exercise, retention per category for CA) | CCPA §1798.100, .130; CA CalOPPA (any site collecting PII from CA residents, no threshold); state laws | `legal.privacy_policy_page`; compare listed vendors with `track.analytics.*`, `ai.*`, `pay.*`, `comm.*` signals | Page path + undisclosed vendors | Blocker if no page and `auth.accounts` (CalOPPA has no threshold); Required if incomplete | founder | Publish one US section covering categories, sources, purposes, disclosures, rights, contact, effective date. |
| Notice does not misdescribe practices | FTC Act §5 (deception) | Notice says "we never share/sell" but `track.analytics.*`/ad SDKs present | Notice line vs SDK init file:line | Blocker when a statement is contradicted by code (deception, no threshold) | founder | Make notice match code or remove the SDK. |
| Honour Global Privacy Control as opt-out of sale/share/targeted ads | CCPA regs §7025; CO, CT, TX, OR, MT, NJ, MN, MD, DE, NH laws | `web.cookies`/`track.analytics.*` present: grep for `Sec-GPC`, `navigator.globalPrivacyControl` | file:line or "not detected" | Required when threshold met and ad/cross-context tracking exists; else Note | engineer | Read `Sec-GPC: 1` / `navigator.globalPrivacyControl` and suppress ad/sharing SDKs; show "opt-out honoured" status. |
| "Do Not Sell or Share My Personal Information" / "Your Privacy Choices" link | CCPA §1798.120, .135 | Footer template grep `Do Not Sell`, `Privacy Choices` | Template or "not found" | Required if CA threshold met and any sale/share (incl. ad pixels) | engineer | Add link + opt-out flow, or stop sharing for cross-context ads. |
| Sensitive data: consent (most states) or "Limit use" link (CA) | CCPA §1798.121; VA/CO/CT/TX etc. | `perm.health`, `perm.biometrics`, `perm.location` (precise), `track.analytics.*` near those screens | Permission + storage file:line | Required (TX/NE/MN apply even to small businesses when selling sensitive data) | founder | Opt-in consent before collecting; avoid sending to analytics/ads. |
| Consumer rights requests (access, delete, correct, opt-out, portability) within 45 days | CCPA §1798.130; state laws (45 days + 45 extension) | `account.export_endpoint`, `account.delete_endpoint`; contact method in notice | Routes or "not detected" | Required when threshold met; else Recommended | engineer | Self-serve export/delete, plus an email/web form; log requests 24 months (CA). |
| Appeal process for denied requests | VA, CO, CT, TX and most non-CA laws | Notice describes appeal | Notice text | Required when threshold met | founder | Add appeal instructions and 45/60-day response SLA. |
| Processor/service-provider contracts | CCPA §1798.100(d), .140(ag); state laws (processor contract terms) | Vendors from signals (`deploy.railway`, `ai.*`, `pay.*`, `comm.*`, `track.analytics.*`) | Vendor list → DPA signed | Required when threshold met; else Recommended | founder | Sign vendor DPAs that include CCPA service-provider terms (see contracts-docs.md). |
| Data protection assessment for targeted ads, sale, sensitive data, profiling | CO, VA, CT, TX, OR etc.; CCPA risk-assessment regs | Triggers from signals above | Signals | Recommended; Required when threshold met and trigger present | founder | Write a short assessment per risky activity; keep on file. |
| Children's data (under 13) | COPPA 16 CFR 312 (amended Rule, compliance 22 Apr 2026) | Answer on minors; age gate grep | Per minors.md | Required (see minors.md) | founder | Apply minors.md fixes. |
| Teens (13–15/17) sale/targeted-ad consent | CCPA §1798.120(c) (under 16 opt-in); CT, OR, MD, NJ, MN, DE (under 16–18) | Answer + ad SDKs | Per minors.md | Required (see minors.md) | founder | Default teens to no sale/no targeted ads. |
| Commercial email: accurate headers/subject, identify as ad, valid physical postal address, working unsubscribe honoured within 10 business days, no fee/login to opt out | CAN-SPAM 15 U.S.C. 7704; 16 CFR 316 | `comm.email`: open marketing templates; grep `unsubscribe`, postal address in footer | Template file:line | Required | engineer | Add footer with postal address (PO box OK) + one-click unsubscribe; suppress within 10 business days; keep suppression list across vendors. |
| Marketing SMS / autodialed or prerecorded calls: prior express written consent, STOP honoured, quiet hours 8am–9pm recipient local time, DNC list scrub | TCPA 47 U.S.C. 227; 47 CFR 64.1200 (opt-out via any reasonable means honoured within 10 business days since 11 Apr 2025) | `comm.sms`: grep signup for SMS consent checkbox text; STOP/HELP handling in webhook | Form + webhook file:line | Blocker if marketing SMS sent without written-consent capture (statutory damages $500–1,500 per message); Required otherwise | engineer | Unticked consent checkbox with TCPA disclosure, store timestamp+IP+text; process STOP keywords; send window 8am–9pm local; scrub National DNC Registry. |
| Transactional vs marketing separation | CAN-SPAM; TCPA | `comm.email`/`comm.sms` templates mixing promos into OTP/receipts | Template file:line | Recommended | engineer | Keep promotional content out of transactional messages. |
| Health data from apps: breach notice to users + FTC within 60 days (≥500 people: FTC at same time) | FTC Health Breach Notification Rule, 16 CFR 318 (2024 amendments cover health/fitness apps) | `perm.health`, HealthKit/Health Connect use, health fields in models; unauthorised sharing to analytics counts as breach | Permission + analytics on health screens | Required when `perm.health` and not a HIPAA entity | founder | Do not send health data to analytics/ads; add HBNR breach runbook. |
| Washington My Health My Data / Nevada SB 370 consumer health data | WA RCW 19.373 (no revenue threshold, private right of action) | `perm.health`, fitness, period, location near health services | Signals | Required when WA users + health data | lawyer | Separate consumer-health privacy policy and consent; Needs a lawyer. |
| Dark patterns in consent/cancel flows | FTC Act §5; CCPA regs §7004; CO rules | Consent/cancel UI asymmetry (pre-ticked boxes, hidden decline) | Template file:line | Required | engineer | Symmetric choices, no pre-ticked boxes, no confirmshaming. |
| Data breach notification to residents (and AG in many states) | All 50 states + DC, PR, VI (see IAPP breach chart) | `docs/` incident runbook with state AG list; CA requires sample notice to AG if >500 CA residents | Runbook path or "not found" | Required | founder | Extend the GDPR breach runbook (privacy-gdpr-uk.md) with a US state-notice step; most states: "without unreasonable delay", some 30–60 days. |
| Reasonable security | CCPA §1798.150 (private action on breach); NY SHIELD; MA 201 CMR 17 | security-baseline.md rows | Per security-baseline.md | Required (see security-baseline.md) | engineer | Apply security-baseline.md fixes. |
| Accessibility of the web app/site | ADA Title III (case law; no federal web rule for private entities) | — | — | Recommended (see accessibility.md) | engineer | Apply accessibility.md (WCAG 2.1/2.2 AA). |
| Privacy policy updated at least every 12 months and dated | CCPA §1798.130(a)(5) | Notice "last updated" date | Page text | Required when CA threshold met; else Recommended | founder | Review and re-date yearly. |
| Employee, contractor and B2B contact data covered (CA only) | CCPA (exemptions expired 1 Jan 2023) | Staff/HR data, CRM | Answer | Required when CA threshold met | founder | Give CA employees/contractors a notice at collection. |
| Opt-out of targeted advertising in-app (mobile) | State laws; Apple ATT (store rule, see app-stores.md) | `track.analytics.*` + ad SDKs in `mobile.*` | SDK init file:line | Required when threshold met | engineer | In-app "Privacy choices" screen that disables ad SDKs. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2020-01-01 | CCPA (CPRA amendments 2023-01-01) | in force |
| 2025-01-01 | CCPA revenue threshold $26,625,000 | in force |
| 2025-04-11 | TCPA revoke-consent-by-any-reasonable-means, 10-business-day honour | in force |
| 2025-10-01 | Montana thresholds lowered to 25,000/15,000 | in force |
| 2026-01-01 | Indiana, Kentucky, Rhode Island laws effective | in force |
| 2026-04-22 | COPPA amended Rule compliance date | in force |
| 2026-07-01 | Connecticut amendments (35,000 threshold, sensitive-data triggers) — confirm via source | in force |
| 2027-01-01 | Next CCPA CPI threshold adjustment (posted by 15 Jan 2027) | future |

## Needs a lawyer
- Whether ad pixels/SDKs constitute "sale" or "sharing" under CCPA and peer state laws for this product.
- Exact applicability where user counts per state are unknown or near 35,000.
- Washington My Health My Data and other consumer-health-data laws if any health-adjacent data is collected.
- TCPA exposure for any marketing SMS or call program (class-action risk).
- State breach-notice obligations after an actual incident (per-state timelines and AG filings).
