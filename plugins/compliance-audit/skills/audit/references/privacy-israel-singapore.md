# Privacy — Israel (PPL + Amendment 13) and Singapore (PDPA)
last-reviewed: 2026-10-13
applies-when: Israel or Singapore in markets (answer) or company seat/establishment in either; Israel rows only for Israel, Singapore rows only for Singapore
sources:
- https://www.nevo.co.il/law_html/law01/p182_001.htm
- https://iapp.org/news/a/israel-marks-a-new-era-in-privacy-law-amendment-13-ushers-in-sweeping-reform
- https://www.pearlcohen.com/the-knesset-enacts-a-comprehensive-amendment-to-the-privacy-protection-law/
- https://sso.agc.gov.sg/Act/PDPA2012
- https://sso.agc.gov.sg/Act/SCA2007
- https://www.pdpc.gov.sg/
- https://www.pdpc.gov.sg/help-and-resources/2021/01/data-breach-management-guide
- https://www.dnc.gov.sg/

## Who it applies to and thresholds

| Scope point | Rule |
|---|---|
| Israel scope | Protection of Privacy Law 5741-1981 (PPL) applies to any "database" holder/processor processing personal data of people in Israel; the PPA (Privacy Protection Authority, gov.il) enforces. No small-business exemption from the core duties. |
| Israel Amendment 13 | In force 14 Aug 2025. Broadens "personal data" (incl. IP addresses, online identifiers) and "especially sensitive data" (health, biometrics, genetic, location, sexual life, criminal, financial, etc.); cuts database registration to data brokers and public bodies; adds administrative fines and DPO duty. |
| Israel security | Protection of Privacy (Data Security) Regulations 2017 (in force 8 May 2018): every database falls in a level — individual-managed, basic, medium, high — by data sensitivity, number of people and number of authorised users. |
| Israel transfers | Protection of Privacy (Transfer of Data to Databases Abroad) Regulations 2001. Israel holds EU adequacy (reconfirmed Jan 2024), so EU→Israel data flows need no SCCs; Israel→EU/adequate countries is permitted. |
| Singapore scope | PDPA 2012 applies to every private organisation collecting, using or disclosing personal data in Singapore (no size threshold); the Do Not Call (DNC) provisions apply to marketing messages to Singapore numbers wherever the sender is. |
| Singapore penalties | Financial penalty up to 10% of annual Singapore turnover (if turnover > S$10M) or S$1M, whichever is higher (from 1 Oct 2022). |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| IL: Transparency notice at collection (whether provision is legally required or voluntary, purposes, recipients and their purposes, rights of access/correction, consequences of refusal) | PPL s.11 (as amended by Amendment 13) | `legal.privacy_policy_page`; grep for an Israel/Hebrew section or s.11 items; signup form near data fields | Page path + missing items | Required (Blocker if no page and `auth.accounts`) | founder | Add an Israel section listing s.11 items; show it at each collection point (signup, forms). |
| IL: Database definitions document (purposes, data types, transfers, processors, risks, authorised access) | Data Security Regs 2017 reg. 2 | `docs/legal/` or RoPA file | File path or "not found" | Required | founder | Write the definitions document (can extend the GDPR RoPA in privacy-gdpr-uk.md); review yearly or on change. |
| IL: Notify PPA of databases holding especially sensitive data on >100,000 people (identity, address, DPO contact) | PPL as amended by Amendment 13 (timing reported as on reaching the threshold, 30 days — confirm via source) | Answer on user count + `perm.health`/`perm.biometrics`/`perm.location`/`pay.*` | Signals + user-count answer | Required when >100,000; else Note with threshold stated | founder | File the notice with the PPA; record date. |
| IL: Database registration | PPL s.8 as amended | Only data brokers (trade in data, >10,000 people) and public bodies | Business-model answer | Note unless data broker | lawyer | Register if trading data. |
| IL: Privacy Protection Officer (DPO) | PPL s.17B1 (Amendment 13); PPA guidance on DPO | Triggers: public body, data broker, core activity = systematic large-scale monitoring (behavioural analytics/ad targeting), or large-scale especially sensitive data | `track.analytics.*` scale + sensitive signals | Required when a trigger applies; else Recommended | founder | Appoint a qualified DPO (may be external); give independence and board access. |
| IL: Security measures by level (access control, logging, annual review, pen-test/risk survey for high level, encryption in transit for remote access) | Data Security Regs 2017 regs 4–17 | Map to security-baseline.md rows (`security.tls`, `security.encryption`, `log.pii_risk`, access logging) | Per security-baseline.md | Required (see security-baseline.md) | engineer | Classify database level; apply the baseline plus level-specific controls (medium: access logs retained ≥24 months, periodic audits; high: risk survey + pen-test every 18 months). |
| IL: Report severe security incidents to the PPA immediately (medium/high level databases) and notify affected people when the PPA orders | Data Security Regs 2017 reg. 11 | Incident runbook includes PPA step | Runbook path or "not found" | Required for medium/high; Recommended for basic | founder | Add PPA reporting step and template to the breach runbook. |
| IL: Direct marketing — identify as direct mail, offer removal, honour opt-out | PPL s.17F | `comm.email`/`comm.sms` marketing templates | Template file:line | Required | engineer | Add "this is direct marketing" label, sender identity and opt-out; maintain removal list. |
| IL: Advertising messages need prior express consent (email, SMS, fax, auto-dial) and the word "פרסומת" (ad) at the start of the subject | Communications Law s.30A ("Spam Law"; statutory damages up to ₪1,000 per message, no proof of harm) | `comm.email`/`comm.sms` + signup consent checkbox | Form + template file:line | Required (Blocker if marketing sent to Israeli users without opt-in) | engineer | Unticked opt-in at signup; prefix subject with "פרסומת"; one-step unsubscribe. |
| IL: Transfers abroad | Transfer Regulations 2001 reg. 2–3 | `deploy.railway` (US), US AI/analytics vendors | Vendor list | Required | founder | Rely on the reg. 2 grounds (consent, or contractual commitment that recipient protects data and does not re-transfer); keep vendor DPAs. |
| IL: Data subject access and correction | PPL ss.13–14 (respond within 30 days) | `account.export_endpoint`, profile edit | Routes or "not detected" | Required | engineer | Self-serve access/correction or documented 30-day process. |
| SG: Consent, notification of purposes, purpose limitation | PDPA ss.13–20 | `legal.privacy_policy_page` lists purposes; consent at signup | Page + form | Required | founder | Notify purposes before collection; collect only what is reasonable; record consent and deemed consent basis. |
| SG: Designate a DPO and publish business contact | PDPA s.11(3), 11(5) | Notice/contact page names a data-protection contact | Page path or "not found" | Required (every organisation) | founder | Name a DPO (founder is fine) and publish the email in the notice; optionally register on PDPC's BizFile+ DPO list. |
| SG: Data protection policies and complaint process | PDPA s.12 | `docs/` policy; complaint channel in notice | Path or "not found" | Required | founder | Write internal policy + publish complaint process. |
| SG: Access and correction within 30 days | PDPA ss.21–22 | `account.export_endpoint`, profile edit | Routes | Required | engineer | Provide access/correction; respond within 30 days or tell the user when. |
| SG: Protection (reasonable security) | PDPA s.24 | security-baseline.md rows | Per security-baseline.md | Required (see security-baseline.md) | engineer | Apply security-baseline.md fixes. |
| SG: Retention limitation | PDPA s.25 | `retention.job` | Job file:line or "not detected" | Required | engineer | Delete or anonymise once purpose no longer served; add purge job. |
| SG: Transfer limitation (comparable protection abroad) | PDPA s.26; PDP Regs 2021 Part 3 | `deploy.railway` (US), other foreign vendors | Vendor list + DPAs | Required | founder | Use contractual clauses (ASEAN MCCs or vendor DPA) giving comparable protection. |
| SG: Breach — assess within 30 days; notify PDPC no later than 3 calendar days after assessing as notifiable (significant harm or ≥500 individuals); notify affected individuals if significant harm | PDPA ss.26B–26D; PDP (Notification of Data Breaches) Regs 2021 | Incident runbook includes PDPC step and 3-day clock | Runbook path or "not found" | Required | founder | Add PDPC online notification step, 30-day assessment and 3-day notice clocks to the runbook. |
| SG: Data portability | PDPA Part 6B (passed 2020) | — | — | Note: not yet in force as of 2026-10-13 — confirm via source | founder | Track PDPC commencement notice. |
| SG: DNC Registry check before marketing calls/SMS/fax to Singapore numbers (results valid 21 days); sender identification; no dictionary attacks | PDPA Part 9 (ss.43–48) | `comm.sms` + phone-number marketing | Webhook/campaign code | Required when sending marketing to SG numbers; Blocker if campaigns run with no DNC check | engineer | Check numbers via the dnc.gov.sg API within 21 days before sending (validity cut from 30 to 21 days in 2021 — confirm via source), or rely on clear and unambiguous consent in writing. |
| SG: Unsolicited commercial email/SMS — "<ADV>" label, unsubscribe honoured within 10 business days, accurate headers | Spam Control Act 2007 (bulk: >100 similar messages/24 h etc.) | `comm.email` marketing templates | Template file:line | Required when bulk marketing to SG | engineer | Add "<ADV>" subject prefix for unsolicited messages, unsubscribe facility, sender contact. |
| SG: Children | PDPC Advisory Guidelines for Children's Personal Data (2024) | Answer on minors | Per minors.md | Required (see minors.md) | founder | Apply minors.md fixes. |
| IL: Processor (outsourcing) agreements with required terms (purpose, data types, security, return/deletion, reporting) | Data Security Regs 2017 reg. 15 | Vendors from signals (`deploy.railway`, `ai.*`, `pay.*`, `comm.*`) | Vendor list → DPA | Required | founder | Use vendor DPAs covering reg. 15 terms; keep a processor list. |
| IL: Authorised-access list and staff confidentiality | Data Security Regs 2017 regs 8–9 | Admin roles, DB access list | Access config | Required (medium/high); Recommended (basic) | founder | Keep a list of people with DB access; review twice a year. |
| IL: Biometric data and camera use | Amendment 13 (especially sensitive data); PPA guidance on biometrics | `perm.biometrics`, `perm.camera` + face processing | Feature file:line | Required | founder | Necessity assessment, explicit notice, high-level security. |
| IL: Data accuracy and deletion of unnecessary data | PPL s.14 (correction), s.2 / Amendment 13 purpose limitation | `retention.job`, profile edit | Job/route file:line | Required | engineer | Allow correction; delete data no longer needed for the purpose. |
| SG: Accuracy obligation | PDPA s.23 | Profile edit + data used for decisions | Route file:line | Required | engineer | Reasonable effort to keep data accurate where used for decisions or disclosed. |
| SG: Legitimate-interests / business-improvement exceptions need documented assessment | PDPA First/Second Schedule (2021 amendments) | `docs/` assessment when relying on these bases | Path or "not found" | Recommended | founder | Write a short legitimate-interests assessment; disclose reliance. |
| SG: Do not collect NRIC numbers unless required by law | PDPC Advisory Guidelines on NRIC | Grep models/forms for `nric`, `fin` | file:line | Required if found | engineer | Remove NRIC fields; use other identifiers. |
| SG: Data intermediaries (processors) bound by protection, retention and breach-notify-to-controller duties | PDPA s.4(2), 26E | Vendor contracts | DPA list | Required | founder | DPAs require vendors to notify you without undue delay. |
| SG: Accountability — data protection management programme | PDPA ss.11–12; PDPC DPMP guide | `docs/` | Path or "not found" | Recommended | founder | Keep a lightweight DPMP (policies, training, breach plan). |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2018-05-08 | Israel Data Security Regulations 2017 | in force |
| 2021-02-01 | Singapore PDPA amendments: mandatory breach notification, deemed consent by notification | in force |
| 2022-10-01 | Singapore higher financial penalty cap (10% turnover) | in force |
| 2024-01-15 | EU reconfirms Israel adequacy | in force |
| 2025-08-14 | Israel Amendment 13 (fines, DPO, s.11 notice, sensitive-database notice) | in force |
| — | Singapore data portability (Part 6B) | not yet in force — confirm via source |

## Needs a lawyer
- Whether a non-Israeli company must appoint an Israeli DPO or file the >100,000 sensitive-database notice; PPA position on extraterritorial reach.
- Israeli database security level classification when sensitive data or many authorised users are involved.
- Israel Spam Law (s.30A) exposure for any past marketing sends without opt-in.
- Whether a Singapore local representative or DPO located in Singapore is expected for a foreign company (PDPC guidance prefers a reachable contact, not residency).
- Singapore DNC compliance for any campaign using purchased or old phone lists.
- Israel transfer-abroad regulations: whether reg. 2 grounds cover US cloud and AI vendors without explicit consent.
- Singapore Spam Control Act applicability to B2B marketing email and to messages sent via third-party platforms.
