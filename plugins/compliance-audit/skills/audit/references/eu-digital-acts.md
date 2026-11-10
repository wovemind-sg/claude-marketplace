# EU digital acts — DSA, AI Act, CRA, Data Act, EAA, NIS2, e-commerce, geo-blocking, P2B
last-reviewed: 2026-10-13
applies-when: EU/EEA in markets (answer); every act starts with its scope test and states the default outcome for a micro entity (<10 staff and ≤€2M turnover)
sources:
- https://eur-lex.europa.eu/eli/reg/2022/2065/oj
- https://digital-strategy.ec.europa.eu/en/policies/digital-services-act
- https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- https://eur-lex.europa.eu/eli/reg/2024/2847/oj
- https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act
- https://eur-lex.europa.eu/eli/reg/2023/2854/oj
- https://digital-strategy.ec.europa.eu/en/policies/data-act
- https://eur-lex.europa.eu/eli/dir/2019/882/oj
- https://commission.europa.eu/strategy-and-policy/policies/justice-and-fundamental-rights/disability/union-equality-strategy-rights-persons-disabilities-2021-2030/european-accessibility-act_en
- https://eur-lex.europa.eu/eli/dir/2022/2555/oj
- https://eur-lex.europa.eu/eli/dir/2000/31/oj
- https://eur-lex.europa.eu/eli/reg/2018/302/oj
- https://eur-lex.europa.eu/eli/reg/2019/1150/oj

## Who it applies to and thresholds

Micro entity = fewer than 10 staff and annual turnover or balance sheet ≤ €2M (Commission Rec. 2003/361). "Default micro outcome" = the result when the size answer is micro and no other trigger applies.

| Act | In scope | Out of scope / carve-outs | Default micro outcome |
|---|---|---|---|
| DSA (Reg. 2022/2065) | Intermediary services offered to EU users: mere conduit, caching, hosting. Hosting = storing user-provided content (UGC, profiles, uploads, comments, shared lists). Online platform = hosting that disseminates to the public. | Apps without UGC are not intermediaries. Micro/small enterprises are exempt from online-platform duties (Art. 19, 29) and transparency reports (Art. 15(2)); not from Art. 11–14, 16–18. | No UGC: Note (trader info is a store rule, app-stores.md). UGC: hosting rows Required. |
| AI Act (Reg. 2024/1689) | Providers and deployers of AI systems used in the EU. | No size exemption for Art. 4 or Art. 50. | Art. 4 literacy Required for any `ai.*`; rest in ai-features.md. |
| CRA (Reg. 2024/2847) | Products with digital elements made available on the EU market: downloadable native apps, desktop software, firmware, libraries sold/monetised; remote data processing that the product needs to function. | Pure SaaS not tied to a product is out (covered by NIS2 if anything). Non-monetised open source out; open-source stewards light regime (Art. 24). Micro/small: no fines for missing the 24 h early warning (Art. 64(10)(a)). | `mobile.*` → in (Required, dates below). Web-only SaaS → Note. |
| Data Act (Reg. 2023/2854) | Ch. VI switching: every provider of a data processing service (IaaS/PaaS/SaaS) to EU customers, consumer or business. Ch. II: connected products and related services. | Art. 31: services mostly custom-built for one customer, and non-production test versions, get lighter duties. Ch. II data-sharing duties exempt micro/small (Art. 7). No SME exemption from Ch. VI. | SaaS → Required. Native app with no cloud service → Note. |
| EAA (Dir. 2019/882) | Listed consumer services incl. e-commerce services (distance sales via website/app), e-books, consumer banking, e-communications, transport ticketing. | Microenterprises providing services are exempt (Art. 4(5)). B2B-only services out. | Micro → Recommended (accessibility.md). Non-micro B2C e-commerce → Required. |
| NIS2 (Dir. 2022/2555) | Medium and large entities in Annex I/II sectors (incl. cloud, data centres, managed services, online marketplaces, search, social networks). | Micro/small out unless a size-independent category (DNS, TLD, trust services, public e-comms, sole provider). | Note. |
| E-commerce Dir. (2000/31) | Any information society service established in the EU; non-EU providers still meet the same duties via consumer law (CRD Art. 6). | — | Required. |
| Geo-blocking Reg. (2018/302) | Traders selling to customers in the EU. | Non-audiovisual copyrighted content (e-books, music, games, software) is out of the access-to-goods/services rule (Art. 4(1)(b)); access and payment-means rules still apply. | Recommended. |
| P2B Reg. (2019/1150) | Online intermediation services or search engines that serve business users who sell to EU consumers. | Not applicable if you are not a platform for businesses. Micro platforms exempt from internal complaint system (Art. 11(5)). | Note unless marketplace. |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| Trader information on app stores | DSA Art. 30–31 (store duty passed to developers) | `mobile.*` + EU in markets | Answer | Blocker / Required (see app-stores.md) | founder | Declare trader status in App Store Connect and Play Console. |
| Single point of contact for authorities and users | DSA Art. 11–12 (all intermediaries, no size exemption) | UGC present (grep models/routes for `comment`, `post`, `upload`, `message`, `review`); contact page lists electronic contact and languages | Contact page path | Required if UGC | founder | Publish a DSA contact point (email/form) and languages. |
| EU legal representative for non-EU intermediaries | DSA Art. 13 | UGC + company outside EU (answer) | Company location answer | Required if UGC and no EU establishment | lawyer | Appoint and publish a DSA legal representative (often bundled with GDPR Art. 27 representative, privacy-gdpr-uk.md). |
| Terms state content moderation rules | DSA Art. 14 | `legal.terms_page` contains moderation policy, tools, complaint route | Terms path + missing section | Required if UGC | lawyer | Add content rules, moderation tools (incl. automated), and complaint handling to terms. |
| Notice-and-action mechanism | DSA Art. 16 | Report/flag endpoint or UI for illegal content (grep `report`, `flag`, `abuse`) | Route/UI file:line or "not detected" | Required if UGC | engineer | Add an electronic report form (reason, URL, reporter contact, good-faith statement) and acknowledge receipt. |
| Statement of reasons on removal/restriction | DSA Art. 17 | Moderation code sends the affected user a reason | Moderation code file:line | Required if UGC | engineer | Notify users of the decision, facts, legal or terms ground, and redress. |
| Report suspected serious crimes | DSA Art. 18 | Moderation runbook in `docs/` | Doc path | Recommended | founder | Document escalation to national authorities for threats to life or safety. |
| AI literacy of staff | AI Act Art. 4 (from 2 Feb 2025; no size exemption) | `ai.*` signal | Signal hits | Required (see ai-features.md) | founder | Record short AI-literacy training for staff using or building the AI feature. |
| AI transparency and risk class | AI Act Art. 50, Annex III | `ai.*` | Per ai-features.md | Required (see ai-features.md) | engineer | Apply ai-features.md. |
| CRA 24 h early warning / 72 h notification / 14-day final report for actively exploited vulnerabilities and severe incidents | CRA Art. 14 (from 11 Sep 2026; applies to products already on the market) | `mobile.*` or distributed software; `security.txt`; incident runbook naming ENISA single reporting platform | Runbook path or "not detected" | Required (micro/small: no fines for the 24 h deadline, but the duty applies) | founder | Write a runbook: detect → 24 h early warning → 72 h notification → final report via the ENISA platform; also inform users. |
| Coordinated vulnerability disclosure policy | CRA Annex I Part II(5) (from 11 Dec 2027) | `security.txt` + `SECURITY.md` | File path or "not detected" | Note now; Required from 11 Dec 2027 | engineer | Publish `/.well-known/security.txt` and a disclosure policy (see security-baseline.md). |
| SBOM for the product | CRA Annex I Part II(1) (from 11 Dec 2027) | `sbom.present` | SBOM file path | Note now; Required from 11 Dec 2027 | engineer | Generate CycloneDX/SPDX SBOM per release (see licensing-sbom.md). |
| Secure by default, security updates for the support period | CRA Annex I Part I, Art. 13(8) (from 11 Dec 2027) | Default config, update mechanism, declared support period (≥5 years unless shorter expected use) | Config + docs | Note now; Required from 11 Dec 2027 | founder | Define support period, ship separate security updates, default-secure settings. |
| Technical documentation, EU declaration of conformity, CE marking | CRA Art. 28, 30–31, Annex V–VII (from 11 Dec 2027) | Default-category app: self-assessment (module A); "important" classes need more | Docs path | Note now; Required from 11 Dec 2027 | lawyer | Classify the product; prepare docs and DoC; CE mark (shown in store listing / about screen). |
| Contract terms enabling switching and export | Data Act Art. 23, 25 (from 12 Sep 2025) | `legal.terms_page` contains: termination on ≤2 months' notice, 30-day transition, exportable data list, ≥30-day retrieval period, deletion after | Terms path + missing clause | Required for SaaS | lawyer | Add a switching clause to terms covering every Art. 25 item. |
| Data export in structured, commonly used, machine-readable format | Data Act Art. 25–26, 30 | `account.export_endpoint` (also GDPR Art. 20) covers all exportable data incl. metadata | Route file:line | Required for SaaS | engineer | Export all customer-generated data and metadata as JSON/CSV with schema docs. |
| Switching charges | Data Act Art. 29 | Pricing/terms mention export or exit fees | Terms text | Required (reduced to direct cost until 12 Jan 2027, then zero) | founder | Remove exit/egress fees by 12 Jan 2027; until then charge only direct costs and disclose them. |
| Connected-product data access by design | Data Act Art. 3 (products placed on market after 12 Sep 2026) | IoT/BLE device code (grep `bluetooth`, `ble`, `mqtt`) | File:line | Note unless a connected product is sold | founder | Make product data accessible to the user by default. |
| Accessible e-commerce / consumer services | EAA Art. 4, Annex I (from 28 Jun 2025); EN 301 549 / WCAG 2.1 AA | B2C + `pay.*` or checkout in web/app | Per accessibility.md | Recommended for micro; Required for non-micro (see accessibility.md) | engineer | Apply accessibility.md; publish service accessibility information (Annex V). |
| NIS2 registration and measures | NIS2 Art. 3, 21, 23 | Size answer + sector | Answer | Note (out for micro/small) | founder | Re-check when headcount ≥50 or turnover >€10M in a listed sector. |
| Service provider identity information | E-commerce Dir. Art. 5; CRD Art. 6 | Imprint/contact page: legal name, geographic address, email, register number, VAT number, supervisory authority if licensed | Page path + missing item | Required (see contracts-docs.md) | founder | Publish an imprint page linked from footer and app settings. |
| Commercial communications identified | E-commerce Dir. Art. 6 | `comm.email` marketing templates show sender and promo conditions | Template file:line | Recommended | founder | Identify sender and offer conditions in marketing messages. |
| ePrivacy cookie/terminal-access consent | ePrivacy Dir. Art. 5(3) | `web.cookies`, `track.analytics.*`, `consent.banner` | Per privacy-gdpr-uk.md | Required (see privacy-gdpr-uk.md) | engineer | Apply privacy-gdpr-uk.md consent rows. |
| No unjustified geo-blocking or redirection | Geo-blocking Reg. Art. 3–5 | Country-based redirects, storefront locks, card-country rejection in checkout (grep `country`, `geoip`, `cf-ipcountry`) | File:line | Recommended | engineer | Same access and accepted payment means for all EU customers; disclose any lawful restriction. |
| P2B terms, ranking transparency, complaints | P2B Reg. Art. 3, 5, 11 | Marketplace serving business sellers (answer) | Answer | Note unless marketplace; then Required | lawyer | Publish P2B-compliant terms with 15-day change notice and ranking parameters. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2018-12-03 | Geo-blocking Regulation | in force |
| 2020-07-12 | P2B Regulation | in force |
| 2024-02-17 | DSA applies to all intermediary services | in force |
| 2024-10-18 | NIS2 national measures apply | in force |
| 2025-02-02 | AI Act Art. 4 AI literacy and prohibited practices | in force |
| 2025-06-28 | EAA applies to products and services | in force |
| 2025-09-12 | Data Act applies (switching, export, contract terms) | in force |
| 2026-08-02 | AI Act general application incl. Art. 50 (grace per ai-features.md) | in force |
| 2026-09-11 | CRA reporting of actively exploited vulnerabilities and severe incidents | in force |
| 2026-09-12 | Data Act Art. 3 design duty for newly placed connected products | in force |
| 2027-01-12 | Data Act: switching charges abolished | upcoming |
| 2027-12-11 | CRA full obligations (essential requirements, SBOM, CVD, docs, CE marking) | upcoming |

## Needs a lawyer
- Whether the product is a "hosting service" or "online platform" under the DSA, and whether micro/small exemptions apply after group aggregation.
- CRA classification (default vs important/critical), whether a SaaS backend counts as "remote data processing" of the app, and whether the company is a manufacturer, importer or steward.
- Whether the B2C offering is an "e-commerce service" under the EAA and whether the microenterprise exemption applies.
- Data Act Art. 31 custom-service carve-out, and permissible early-termination fees.
- Choice of DSA legal representative and its liability exposure.
