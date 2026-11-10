# Privacy — EU GDPR, UK GDPR, ePrivacy and PECR
last-reviewed: 2026-10-13
applies-when: EU/EEA or UK in markets (answer), or EU/UK users reachable (`auth.accounts` + no geo-block); UK rows only when UK in markets
sources:
- https://eur-lex.europa.eu/eli/reg/2016/679/oj
- https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32002L0058
- https://www.legislation.gov.uk/uksi/2003/2426/contents
- https://www.legislation.gov.uk/ukpga/2025/18/contents
- https://ico.org.uk/for-organisations/data-protection-fee/
- https://www.legislation.gov.uk/uksi/2025/63/contents/made
- https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guidance-on-the-use-of-storage-and-access-technologies/
- https://ico.org.uk/for-organisations/how-to-deal-with-data-protection-complaints/
- https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/documentation/
- https://ico.org.uk/for-organisations/report-a-breach/
- https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-012022-data-subject-rights-right-access_en
- https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-92022-personal-data-breach-notification-under_en
- https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-32018-territorial-scope-gdpr-article-3-version_en
- https://www.edpb.europa.eu/our-work-tools/our-documents/recommendations/recommendations-012020-measures-supplement-transfer_en
- https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/standard-contractual-clauses-scc_en
- https://www.dataprivacyframework.gov/
- https://railway.com/legal/dpa
- https://trust.railway.com/item/subprocessors

## Who it applies to and thresholds

| Scope point | Rule |
|---|---|
| Territorial | GDPR Art. 3(2): non-EU company is in scope when it offers goods/services to people in the EU or monitors their behaviour (analytics, tracking). Same test for UK GDPR and UK users. |
| Size | No small-business exemption from GDPR/UK GDPR. Only the Art. 30 records duty has a <250-employee carve-out (Art. 30(5)), and it is lost when processing is not occasional — any SaaS/app processing user accounts is not occasional. |
| Cookies/trackers | ePrivacy Art. 5(3) / PECR reg. 6 apply to any storage or access on the user's device (cookies, localStorage, SDK identifiers), personal data or not. |
| UK reform | Data (Use and Access) Act 2025 (DUAA): main UK GDPR/PECR amendments in force 5 Feb 2026; complaints-handling duty from 19 Jun 2026. PECR fines raised to £17.5M or 4% of global turnover. |
| UK fee | Every UK controller pays the ICO data protection fee unless exempt. Tier 1 (micro: ≤10 staff or ≤£632k turnover) £52, tier 2 £78, tier 3 £3,763 (SI 2025/63, from 17 Feb 2025). |
| EU pending | "Digital Omnibus" GDPR/ePrivacy amendments are still in trilogue (Oct 2026) — not law; do not rely on them. |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| Privacy notice given at collection (identity, purposes, lawful basis, recipients, transfers, retention, rights, complaint right) | GDPR Art. 12–14; UK GDPR same | `legal.privacy_policy_page` present; open it and grep for `retention`, `lawful basis`/`legitimate interest`, `transfer`, processor names | Page path + missing headings | Blocker if no page and `auth.accounts` present; Required if page lacks Art. 13 items | founder | Publish a notice covering every Art. 13 item; link from signup, app settings and store listing (see contracts-docs.md). |
| Lawful basis documented per purpose | GDPR Art. 6 | Notice text + any `docs/legal/` record | Purposes listed without basis | Required | founder | Map each purpose to a basis (contract, legitimate interest, consent, legal obligation). |
| Consent before non-essential cookies/SDKs | ePrivacy Art. 5(3); PECR reg. 6 | `web.cookies`, `track.analytics.*` present AND `consent.banner` missing; grep analytics init for a consent guard | file:line of tracker init loaded before consent | Blocker (EU) when trackers fire pre-consent; UK: Recommended if analytics fits the DUAA statistical exemption below, else Blocker | engineer | Gate SDK init on stored consent; reject as easy as accept; record consent with timestamp. |
| UK analytics exemption conditions | PECR reg. 6 as amended by DUAA 2025 | First-party, aggregate-only analytics (e.g. `track.analytics.plausible`); no ad/profiling use; notice explains purpose; free opt-out link | Analytics config + notice text | Required if relying on exemption without opt-out | engineer | Add opt-out toggle and notice text, or treat as consent-based. Third-party analytics with own-purpose use (e.g. Google) likely does not qualify — Needs a lawyer. |
| Right of access + portability (machine-readable export) | GDPR Art. 15, 20; Art. 12(3) one month (+2 for complex) | `account.export_endpoint`; else grep routers for `export`, `download my data` | Route file:line or "not detected" | Required | engineer | Add authenticated JSON/CSV export of all user data, or a documented manual DSAR process with a 1-month SLA. |
| Right to erasure | GDPR Art. 17 | `account.delete_endpoint`; check cascades/anonymisation in models and backups policy; `retention.job` | Route + ORM `ondelete`/delete logic | Required (Blocker for app stores — see app-stores.md) | engineer | Delete or anonymise all user rows, files and processor copies; document backup expiry window. |
| Storage limitation / retention schedule | GDPR Art. 5(1)(e) | `retention.job` (cron/arq job purging old data); retention periods stated in notice | Job file:line or "not detected" | Required | engineer | Define per-category retention; add scheduled purge job; state periods in notice. |
| Records of processing (RoPA) | GDPR Art. 30; Art. 30(5) | `docs/legal/` or `docs/*ropa*`; any doc listing purposes/categories/recipients | File path or "not found" | Required (exemption almost never applies to an app processing accounts continuously) | founder | Keep a RoPA spreadsheet (ICO template) and review yearly. |
| Processor contracts (DPA) with every vendor | GDPR Art. 28(3) | Vendors from signals: `deploy.railway`, `pay.*`, `ai.*`, `track.analytics.*`, `comm.*` | Signal list → vendor → DPA signed? | Required | founder | Sign each vendor's DPA. Railway's DPA is not automatic: it binds only once executed via the DocuSign link in its §14. |
| Sub-processor list published | GDPR Art. 28(2), 28(4); Art. 13(1)(e) recipients | Notice or `/subprocessors` page lists vendors from signals | Missing vendors | Required | founder | Publish a sub-processor page; include Railway (and its own list at trust.railway.com). |
| International transfers safeguarded | GDPR Art. 44–46; UK GDPR same + UK Addendum | `deploy.railway` (primary processing in US, on GCP per Railway DPA §9.1/Exh. C); US AI/analytics vendors | Vendor list + DPA transfer clause | Required | founder | Rely on EU-US DPF if vendor is certified, else SCCs (Railway DPA §9.2 EU SCCs, §9.4 UK Addendum); keep a transfer impact assessment. Note US CLOUD Act exposure regardless of region. |
| Security of processing | GDPR Art. 32 | Rows in security-baseline.md (`security.tls`, `security.encryption`, `security.secrets_in_repo`, `log.pii_risk`) | Per security-baseline.md | Required (see security-baseline.md) | engineer | Apply security-baseline.md fixes. |
| Breach notification to regulator within 72 h | GDPR Art. 33; UK GDPR Art. 33 | `docs/` incident runbook naming authority + 72 h clock | Runbook path or "not found" | Required | founder | Write runbook: detect → assess risk → notify lead authority/ICO ≤72 h → log every breach (Art. 33(5)). |
| Notify affected users when high risk | GDPR Art. 34 | Runbook includes user-notification template; `comm.email` available | Runbook section | Required | founder | Add user-notification template and decision criteria. |
| DPIA for high-risk processing | GDPR Art. 35 | Triggers: `perm.health`, `perm.biometrics`, `perm.location` tracking, large-scale profiling, `ai.*` decisions about users | Signal hits | Recommended; Required when Art. 35(3) criteria met | founder | Run a DPIA before launch of the risky feature. |
| Special category data | GDPR Art. 9 | `perm.health`, `perm.biometrics` (on-device Face ID unlock that never leaves device is not processing by you) | Permission declarations + where data is stored | Required (explicit consent or other Art. 9(2) ground) | founder | Collect explicit consent, minimise, encrypt at field level, DPIA. |
| DPO appointment | GDPR Art. 37 | Answers + `perm.health`/`perm.biometrics`/`track.analytics.*` scale; only if core activity is large-scale monitoring or large-scale special-category processing | Answers + `perm.health`/`perm.biometrics` | Note unless Art. 37 criteria met, then Required | founder | Appoint DPO (can be external) and publish contact. |
| EU representative (no EU establishment) | GDPR Art. 27 | Answer: entity location outside EU + EU in markets | Company location answer | Required (exemption only for occasional, low-risk processing) | lawyer | Appoint an EU representative; name it in the notice. |
| UK representative (no UK establishment) | UK GDPR Art. 27 | Answer: entity outside UK + UK in markets | Company location answer | Required | lawyer | Appoint a UK representative; name it in the notice. |
| ICO fee paid | DP (Charges and Information) Regs 2018, SI 2025/63 | Answer: UK establishment | Fee register entry | Required | founder | Pay tier fee yearly on ico.org.uk; record registration number in notice. |
| UK complaints handling | DPA 2018 s.164A (inserted by DUAA s.103) | Notice/contact page has a data-protection complaint channel; grep templates for `complain` | Page path or "not found" | Required | founder | Provide complaint channel, acknowledge within 30 days, respond without undue delay, keep records. |
| Marketing email/SMS/push consent | PECR reg. 22; ePrivacy Art. 13 | `comm.email`, `comm.sms`, `comm.push` + signup form opt-in checkbox not pre-ticked; unsubscribe link in templates | Signup template + mail template file:line | Required | engineer | Opt-in (or soft opt-in for existing customers' similar products with opt-out at collection and in every message); one-click unsubscribe. |
| Consent as easy to withdraw as to give | GDPR Art. 7(3); PECR reg. 6 | `consent.banner` offers a persistent "cookie settings"/withdraw link; account settings toggle for marketing | Template file:line | Required | engineer | Add a footer/settings link that reopens consent choices and updates SDK state. |
| Automated decisions with legal/similar effect | GDPR Art. 22; UK GDPR Art. 22A–22D (DUAA, relaxed safeguards regime) | `ai.*` used to accept/reject, price or rank users (grep model output feeding `approve`, `ban`, `score`) | Decision code file:line | Required when solely automated and significant; else Note | founder | Offer human review, explanation and contest route; disclose in notice. |
| Joint controllership with ad/analytics vendors | GDPR Art. 26 | Meta Pixel (grep `fbq(`, `connect.facebook.net`), `track.analytics.google` with ads features | SDK init file:line | Recommended | founder | Accept vendor's joint-controller terms; disclose in notice. |
| DSAR identity check and search scope | GDPR Art. 12(6); UK DPA 2018 s.45 + DUAA "reasonable and proportionate search" | DSAR process doc in `docs/` | Path or "not found" | Recommended | founder | Verify identity proportionately; search DB, logs, backups, vendors; reply within one month. |
| Children's data | GDPR Art. 8 (age 13–16 by state); UK Age Appropriate Design Code | Answer (under-16 users possible) → minors.md checks | Per minors.md | Required (see minors.md) | founder | Apply minors.md fixes (age gate, parental consent). |
| Data protection by design and default | GDPR Art. 25 | Default settings minimise sharing; `log.pii_risk` | Settings defaults, log lines | Recommended | engineer | Default to private; drop unneeded fields. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2018-05-25 | GDPR applies | in force |
| 2021-01-01 | UK GDPR (post-Brexit copy) + UK Art. 27 representative | in force |
| 2023-07-10 | EU-US Data Privacy Framework adequacy decision | in force |
| 2025-02-17 | ICO fee tiers £52 / £78 / £3,763 | in force |
| 2026-02-05 | DUAA main changes: PECR fines to £17.5M/4%, cookie exemptions incl. statistical analytics | in force |
| 2026-06-19 | UK controller complaints-handling duty (DPA 2018 s.164A) | in force |

## Needs a lawyer
- Whether an EU and/or UK Art. 27 representative is required, and who to appoint.
- Legitimate-interest balancing test for analytics, fraud, product emails.
- Transfer impact assessment for US vendors (Railway, AI APIs), CLOUD Act exposure.
- Whether third-party analytics qualify for the UK DUAA statistical-purpose cookie exemption.
- Lead supervisory authority when the company has no EU establishment (one-stop-shop unavailable).
