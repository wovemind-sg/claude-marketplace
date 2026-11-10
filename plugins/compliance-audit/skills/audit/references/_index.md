# Routing index — signal/answer → modules
last-reviewed: 2026-10-13

SKILL.md embeds table 1. Tables 2 and 3 mirror each module's header and must be updated whenever a module's `applies-when:` or `last-reviewed:` line changes (pipes inside cells are escaped as `\|`). Consistency check: `grep -h '^applies-when:' references/*.md` must equal table 2 with the escapes removed.

## 1. Route — which modules to load

Signals come from `detect_signals.py`; answers from the question rounds. A module loads if any row names it. Within a loaded module, the "Rows to apply" column names the rows the trigger activates.

| Trigger (signal or answer) | Load modules | Rows to apply |
|---|---|---|
| always (every audit) | `privacy-gdpr-uk.md`, `security-baseline.md`, `contracts-docs.md`, `licensing-sbom.md` | privacy-gdpr-uk rows only when EU/EEA or UK in markets, or EU/UK users reachable (`auth.accounts` + no geo-block); otherwise record "not in scope" |
| `mobile.ios`, `mobile.android`, `mobile.capacitor`, `mobile.react_native`, or answer "ships an iOS/Android app" | `app-stores.md` | Apple rows for iOS, Google rows for Android, both for Capacitor/RN; licensing-sbom mobile attribution rows; security-baseline mobile rows |
| EU/EEA in markets | `eu-digital-acts.md` | DSA hosting rows only if UGC; CRA rows if `mobile.*` or distributed software; Data Act rows if SaaS |
| US in markets, or US users reachable (`auth.accounts` + no geo-block) | `privacy-us.md` | state-law rows only when a threshold is met or the size answer is "unsure" |
| Israel or Singapore in markets, or company seat there | `privacy-israel-singapore.md` | Israel rows for IL, Singapore rows for SG |
| any `ai.*` signal, or answer "has AI features" | `ai-features.md` | plus eu-digital-acts AI Act rows when EU |
| any `pay.*` signal, or answer "takes payments / subscriptions" | `payments.md` | plus app-stores IAP/Play Billing rows when `mobile.*` |
| B2C and minors answer "yes" or "unlikely, not enforced"; or Kids/Families store category | `minors.md` | plus app-stores Families/Kids rows when `mobile.*` |
| EU/EEA in markets and size answer not micro (or user opts in); or US in markets with public-facing B2C | `accessibility.md` | UK rows when UK in markets; EAA rows Recommended when micro |
| `web.cookies` or any `track.analytics.*` | (no new module) | privacy-gdpr-uk ePrivacy/PECR consent rows; privacy-us opt-out of sale/sharing + GPC rows; app-stores ATT / Advertising ID rows when `mobile.*` |
| any `perm.*` (esp. `perm.health`, `perm.biometrics`, `perm.location`) | (no new module) | privacy-gdpr-uk Art. 9 special-category + DPIA rows; privacy-us sensitive-data rows; app-stores permission-string / declaration rows |
| `comm.email` | (no new module) | privacy-gdpr-uk PECR reg. 22 marketing consent; privacy-us CAN-SPAM; privacy-israel-singapore Spam Law / Spam Control Act |
| `comm.sms` | (no new module) | privacy-us TCPA; privacy-gdpr-uk PECR; privacy-israel-singapore Spam Law and Singapore DNC Registry |
| `comm.push` | (no new module) | privacy-gdpr-uk PECR marketing consent when push is promotional |
| `account.delete_endpoint` / `account.export_endpoint` missing | (no new module) | privacy-gdpr-uk erasure/access rows; app-stores account-deletion rows; eu-digital-acts Data Act export rows |
| `security.secrets_in_repo`, `log.pii_risk`, `security.tls` missing | (no new module) | security-baseline rows (always loaded) |
| `sbom.present` missing + `mobile.*` | (no new module) | licensing-sbom SBOM row; eu-digital-acts CRA SBOM row (Note until 2027-12-11) |

## 2. Module → applies-when (verbatim from each file)

| Module | applies-when |
|---|---|
| `accessibility.md` | EU/EEA in markets and (size answer is not micro or the user opts in), or US in markets with a public-facing B2C product; UK rows only when UK in markets |
| `ai-features.md` | any `ai.*` signal (`ai.anthropic\|openai\|openrouter\|google\|litellm\|langchain\|ollama`) or the user says the product has AI features |
| `app-stores.md` | any `mobile.*` signal (`mobile.ios`, `mobile.android`, `mobile.capacitor`, `mobile.react_native`) or the user says the product ships an iOS/Android app; Apple rows only for iOS, Google rows only for Android |
| `contracts-docs.md` | always (every audit); B2B rows when answer = B2B/both; consumer rows when answer = B2C/both |
| `eu-digital-acts.md` | EU/EEA in markets (answer); every act starts with its scope test and states the default outcome for a micro entity (<10 staff and ≤€2M turnover) |
| `licensing-sbom.md` | always (every audit); input = license_scan.py JSON + sbom.present + ai.* + mobile.* signals |
| `minors.md` | B2C product and the minors answer is "yes" or "unlikely, not enforced" (no age gate); also when the app is in a Kids/Families store category |
| `payments.md` | any `pay.*` signal (`pay.stripe\|revenuecat\|storekit\|playbilling\|paddle\|lemonsqueezy`) or the user says the product takes payments or sells subscriptions |
| `privacy-gdpr-uk.md` | EU/EEA or UK in markets (answer), or EU/UK users reachable (`auth.accounts` + no geo-block); UK rows only when UK in markets |
| `privacy-israel-singapore.md` | Israel or Singapore in markets (answer) or company seat/establishment in either; Israel rows only for Israel, Singapore rows only for Singapore |
| `privacy-us.md` | US in markets (answer), or US users reachable (`auth.accounts` + no geo-block); state-law rows only when a threshold below is met or the size answer is "unsure" |
| `security-baseline.md` | always (every audit); rows keyed to stack signals backend.fastapi, backend.go, db.postgres, cache.redis, deploy.railway, mobile.* |

## 3. Module → last-reviewed

Modules older than 90 days get their first sources re-fetched during an audit (README "Maintainers").

| Module | last-reviewed |
|---|---|
| `accessibility.md` | 2026-10-13 |
| `ai-features.md` | 2026-10-13 |
| `app-stores.md` | 2026-10-13 |
| `contracts-docs.md` | 2026-10-13 |
| `eu-digital-acts.md` | 2026-10-13 |
| `licensing-sbom.md` | 2026-10-13 |
| `minors.md` | 2026-10-13 |
| `payments.md` | 2026-10-13 |
| `privacy-gdpr-uk.md` | 2026-10-13 |
| `privacy-israel-singapore.md` | 2026-10-13 |
| `privacy-us.md` | 2026-10-13 |
| `security-baseline.md` | 2026-10-13 |
