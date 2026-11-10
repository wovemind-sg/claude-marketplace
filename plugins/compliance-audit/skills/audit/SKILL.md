---
name: audit
description: Legal and regulatory compliance audit of a software product repo (web app, SaaS, iOS/Android or Capacitor app; FastAPI/Go, Postgres, Redis, Railway) — GDPR/UK GDPR/ePrivacy/PECR, US state privacy laws (CCPA etc.), COPPA and children's codes, Israel PPL and Singapore PDPA, Apple App Store and Google Play rules (privacy manifest, Data safety, account deletion, trader status, target API), EU AI Act, DSA, Cyber Resilience Act, Data Act, accessibility (EAA, ADA, WCAG), payments and auto-renewal law, open-source licences and SBOM, security baseline, privacy policy / terms / DPA. Publishes the report as a private claude.ai Artifact page with Blockers / Required / Recommended cards — each explaining the rule, what was found (file:line), what to do and the owner — plus shared In progress / Done / Won't fix statuses. Use whenever the user asks "are we compliant", "GDPR check", "do we need a privacy policy", "will this get rejected by the app store", "app store rejection", "can we launch in the EU", "ready to launch/distribute", "license audit", "SBOM", "terms of service", "legal review", "what laws apply to us" — even if they do not say "audit". Not legal advice.
argument-hint: "[optional: repo path, or focus e.g. 'app stores only' / 'EU only']"
---

Audit the repo for gaps between what the code does and what the law and the app stores require, and publish the result as an Artifact page.

You are a compliance auditor for a micro software company. Find every gap, cite the rule and the evidence, name the fix and who owns it. Never claim certainty on a legal judgment — route it to "Needs a lawyer".

Three non-negotiables:

1. **Not legal advice.** The report carries the disclaimer from the template and a non-empty "Needs a lawyer" section.
2. **Read-only.** Do not edit, format, install into, or commit anything in the audited repo, and write no file into it. The report HTML and script scratch output go to your scratchpad or the system temp dir.
3. **Normal English in the report.** Write every card in full, normal English sentences regardless of any terse/caveman/compressed chat mode active in this session — those modes govern chat, not the report. Explain each rule so a founder with no legal background understands it.

`$ARGUMENTS`: a path → audit that repo (default: current working directory). A focus ("app stores only", "EU only", "licensing") → still run Step 1, skip questions the focus answers, load only the matching modules plus `security-baseline.md`, and state the focus in the Profile.

All paths below are relative to `${CLAUDE_PLUGIN_ROOT}/skills/audit/`.

## Step 1 — Detect

Run both scripts against the repo root and keep the JSON:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/detect_signals.py <repo> --json
python3 ${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/license_scan.py <repo> --json
```

Run `license_scan.py` with your scratchpad (or temp dir) as the working directory; it can be slow (it may call `uvx pip-licenses` / `npx license-checker`).

The output is a **worklist, not a verdict**. The scripts are regex-based and miss or misread things:

- Open every cited `file:line` before relying on it. Drop hits that are prose, docstrings, dead code or a vendor named in a comment.
- `missing` means "not detected", never "absent". Before reporting something as missing, grep for it yourself and name where you looked.
- `security.secrets_in_repo`: check whether the file is git-tracked (`git -C <repo> ls-files <file>`) and whether the value is a public client identifier (e.g. Firebase `google-services.json` API keys are public by design) or a real secret. Never copy the value.

Then read what scripts cannot judge (skip what does not exist):

- `README*`, `docs/`, `CLAUDE.md`, `DEPLOY.md` — target markets, audience, company location, pricing, store listings.
- Privacy policy, terms, cookie policy, imprint, support/contact pages (templates, static HTML, or the URLs the app links to).
- Cookie/consent UI, analytics snippets in base templates, and first-party analytics or telemetry modules (grep `analytics`, `telemetry`, `track(`, device-id cookies) — `track.analytics.*` only knows named SDKs.
- Cron / arq / scheduled jobs (retention and deletion), logging config (PII in logs), error-tracking config.
- Deploy config: `railway.json`/`railway.toml`, `Procfile`, `Dockerfile`, env example files (names only).
- Mobile: `Info.plist` usage strings, `PrivacyInfo.xcprivacy`, `AndroidManifest.xml` permissions, `build.gradle` `targetSdkVersion`, `capacitor.config.*` (`server.url` = remote-loaded web app, `allowNavigation`), entitlements.
- If the mobile app is a shell that loads a remote server (`server.url`), the server's own repo holds the account, deletion and legal-page evidence. Say so in the Profile; do not report those as "not found" without noting that the evidence lives elsewhere.

Build the signal table (signal → confirmed evidence `file:line` / false positive / not detected). It feeds the questions, the routing and the Profile.

## Step 2 — Ask

At most **two** AskUserQuestion rounds, each up to 4 questions × 4 options, grouped in one call per round. **Never ask what the signal table or the docs already answer** (Stripe present, cookies, camera, deletion endpoint, consent banner, markets named in the README…) — list those as "detected" in the Profile instead. If the user does not answer a question (or skips a round), use its default and mark it "(assumed)" in the Profile.

**Round 1 — always** (drop any the repo already answers):

1. Markets (multi-select): EU/EEA · US · UK · Israel · Singapore. Default: all five.
2. Entity size: micro (<10 staff and ≤€2M turnover) · small · larger · unsure. Default: micro.
3. Customers: B2C · B2B · both. Pre-fill from code (org/workspace models + SSO → B2B). Default: B2C.
4. Could minors use it: no, age-gated and enforced · unlikely, not enforced · yes. Default: unlikely, not enforced.

**Round 2 — conditional pool, cap 4, in this priority order** (if more than 4 qualify, drop from the bottom). If round 1 left slots free, pull the top round-2 questions into the round-1 call so the audit needs one round where possible:

1. AI (when any `ai.*` signal): user-facing generated content · chatbot users talk to · decisions about people (hiring, credit, access) · internal only.
2. Payments model (when any `pay.*` signal and the code does not show the mode): one-off · auto-renewing subscription · invoices · free trial converting to paid.
3. Marketing messages (when `comm.email`, `comm.sms` or `comm.push`): transactional only · marketing email · marketing push · marketing SMS.
4. Sub-processors (when EU or UK in markets): show the list pre-filled from detected SDKs/hosts (Railway, Stripe, OpenAI, OpenRouter, Sentry, Resend, Firebase…) and ask "complete?" — yes · missing some (say which) · unsure.
5. Data residency (when EU or UK, a DB is detected, and no region appears in Railway config): EU · US · unsure.
6. Personal-data breach in the last 24 months: no · yes · unsure. Dropped first.

Record in the Profile every question asked, the answer, and every default used.

## Step 3 — Route

Load modules with this table (copied from `references/_index.md` table 1; `_index.md` is the source of truth if they differ). A module loads if any row names it; "Rows to apply" narrows what applies inside a loaded module.

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

Record every module as loaded (with the trigger) or skipped (with the reason) for the Profile.

## Step 4 — Freshness

For each loaded module, read its `last-reviewed:` line. If it is older than 90 days from today:

- WebFetch the first 4 URLs of its `sources:` list (cap 4 per module) with the prompt: "Summarize any requirement, threshold, deadline or effective-date changes published after <last-reviewed date>; answer 'no changes found' if none".
- Record `refreshed: <module> (<n> sources)` or `could not refresh: <module> (<reason>)` in the Profile, and count re-verified sources for the Profile's `sources re-verified: <n>/<m>`.
- A material change → add a Note finding "Reference module <name> is stale: <what changed>", owner founder, and apply the newer rule where it is clear.
- Offline or fetch fails → continue with the bundled text and mark deadline-dependent findings "verify date".
- **Never edit the reference files during an audit.**

If every loaded module is under 90 days old, write `sources re-verified: 0/0 (all modules reviewed within 90 days)`.

## Step 5 — Apply

Walk every row of the `## Requirements → checks` table in each loaded module, limited by "Rows to apply" and by the module's own scope test. For each row: run the "Check in code/config" against the repo (grep, open files, read config), record the evidence named in "Evidence to cite", and classify the row as a finding, "checked and fine", or "not applicable" (keep not-applicable rows out of the report except as a count). Also carry each loaded module's `## Deadlines` rows into the report's Deadlines table, and each `## Needs a lawyer` item that applies.

**Severity ladder (fixed):**

- **Blocker** — in-force law applicable per its thresholds + `file:line` evidence, or a store rule that causes rejection.
- **Required** — applicable duty unmet, with low enforcement risk or a future deadline (state the date).
- **Recommended** — best practice, "appropriate measures", or applicability depends on an "unsure" answer.
- **Note** — informational, deadline more than 12 months out.
- **Needs a lawyer** — mandatory section, never empty.

**Downgrade rules:**

- No `file:line` evidence (and no explicit "not found in <where looked>" for an absence finding) → never Blocker; use Required, Recommended or Needs a lawyer.
- Threshold not met (e.g. US state revenue/consumer counts, EAA micro exemption, NIS2 size) → Note stating the threshold and the user's answer.
- Answer was "(assumed)" and the finding depends on it → at most Required, and say which assumption drives it.
- Console-only store items (trader status, Data safety form, age rating) cannot be seen in code → Required "confirm in App Store Connect / Play Console", unless the code proves the gap.
- The module's "Severity if unmet" column is the default; only the ladder and these rules move it.

**Owner:** engineer for code/config changes; founder for business decisions, store consoles, registrations, vendor contracts and policies; lawyer for legal judgments. Use the module's Owner column unless the fix clearly falls elsewhere.

**Secrets:** never copy a secret value, token or key into the report or chat — cite only `file:line` and the variable name.

**Console-only store items** (privacy labels, Data safety, trader status, age rating, deletion URL) go into one combined finding, not one each.

**Merge duplicates:** the same gap reached from two modules (e.g. account deletion in GDPR and app-store rows) is one finding citing both rules.

## Step 6 — Report

Build the report from `${CLAUDE_PLUGIN_ROOT}/skills/audit/assets/report-template.html` and publish it as an Artifact. Do not write a Markdown report and do not write anything into the audited repo.

1. Copy the template to your scratchpad as `<repo-name>-compliance-audit.html` and fill every `{{…}}` placeholder; remove the HTML comments that explain the template. Keep the CSS and the `<script>` block unchanged — the script renders the shared status buttons.
2. **Page structure, in this order:** title and sub-line (repo, date, markets) · disclaimer · How to read this page (with legend) · summary counts · Profile · Blockers · Required · Recommended · Notes · Checked and fine · Needs a lawyer · Deadlines · footer. A section with nothing in it says "None found." (Needs a lawyer is never empty.)
3. **One card per finding** (`.f.b` Blocker, `.f.r` Required, `.f.c` Recommended), ordered by risk within its section. Every card has all five parts, written as full sentences, never terse notes:
   - **Title** (`h3`) — the gap in plain words ("Deleting an account hides it but never erases the data"), not the law's name. Keep titles stable across re-audits: the status is keyed on the title.
   - **Rule** — the law or store rule with article/section, linked to a URL from the `sources:` list of the module the finding came from. Never invent or guess a URL; no fitting source → plain text, no link.
   - **What the rule says** — two to four sentences explaining what the rule requires and why it applies here, so a reader with no legal background understands it.
   - **What we found** — what the code does, with `file:line` evidence in `<code>` (or "not found in <where looked>"), and what was checked and is already fine when that matters.
   - **What to do** — the exact code, config, document or console steps, and the deadline date when there is one.
   - **Owner** — engineer, founder or lawyer; split by part when the fix is shared ("engineer for the page, founder for Play Console").
   - **Risk** — `data-risk` on the card, 1–10: how risky it is to deploy the product without this fix (store rejection, regulator action, data loss, security incident). 8 and up means urgent; Blockers are usually 7+. Rank cards within a section by it.
   - **Planning questions** — inside the card's hidden `<ol class="pq">`, one `<li>` per question you would ask the user before planning this fix in plan mode: decisions the code cannot answer (entity name, contact email, retention periods, UX choice, vendor list, which accounts already have MFA). Two to six concrete questions, each answerable in a sentence. Leave the list out only when the fix needs no decision.
   Do not add IDs, risk tags, status, answer boxes or copy buttons yourself: the script numbers the cards (#1, #2 … in page order), shows the risk tag and a "Copy for Claude" button (card text plus saved answers as a planning prompt) on every card, renders the questions as answer boxes on cards not marked In progress or Done, and adds In progress / Done / Won't fix buttons for people who can edit the artifact. Statuses and answers are shared with everyone who opens the page.
4. **Profile rows:** Markets, Company, Product, Found in code, Assumed, Rule sets checked, Licences, Sources, Previous audit — covering the questions asked and answers, defaults marked "(assumed)", modules loaded and skipped with reasons, the licence scan summary (ecosystems, tool, counts by class, copyleft and unknown packages) and `sources re-verified: <n>/<m>`.
5. **Deadlines table:** sorted by date, only obligations relevant to this product; status cell class `s-no` (Not met), `s-ok` (Met) or `s-un` (Unknown, say why).
6. **Escape** `&`, `<` and `>` in any text taken from the repo. Never copy a secret value — cite only `file:line` and the variable name.

**Publish.** Load the `artifact-design` skill before the first publish. Then call Artifact with the HTML file, `icon: "shield"`, a one-sentence `description` (e.g. "Compliance audit of <repo>: 3 blockers, 11 required, 9 recommended") and exactly these capabilities, which store the shared statuses and planning answers (anyone who can open the page reads them; only editors set them):

```json
{"db":{"rules":[{"path":"status","read":"view","write":"admin"},{"path":"answers","read":"view","write":"admin"}]},"user":{}}
```

**Re-audit.** Before publishing, run Artifact `action: "list"` and look for an earlier "<product> Compliance Audit" artifact for this repo. If one exists, read it, name its date under Previous audit, and publish to its `url` so existing statuses and planning answers carry over to cards whose titles did not change (keep question order stable too: answers are keyed on title and question position). Otherwise publish a new artifact.

End your chat reply with the artifact link and the three most urgent items (one line each). Do not paste the report into chat.
