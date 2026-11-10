# compliance-audit

Audits a product repo for legal and regulatory compliance gaps and publishes the report as a private claude.ai Artifact page: findings ranked by legal risk, each card explaining the law or store rule in plain words, what was found (`file:line` evidence), the exact fix and an owner (engineer / founder / lawyer). Each card has a running ID, a 1–10 risk score for deploying without the fix, the planning questions Claude would ask before fixing it (answer boxes, saved and shared), and a "Copy for Claude" button that copies the card plus your answers as a plan-mode prompt. Editors mark each card In progress, Done or Won't fix; status and answers are shared with everyone who opens the page.

Built for micro software companies shipping native apps (iOS/Android, incl. Capacitor), web apps and SaaS on FastAPI or Go backends with Postgres, Redis and Railway. Default jurisdictions: EU/EEA, US, UK, Israel, Singapore (confirmed per run).

**Not legal advice.** The report is a generated audit. Items under "Needs a lawyer" require counsel.

## Install

```
/plugin marketplace add wovemind-sg/claude-marketplace
/plugin install compliance-audit@wovemind
```

## Usage

```
/compliance-audit:audit [focus] [--markets EU,US,UK,Israel,Singapore] [--size micro|small|larger]   # defaults: all five markets, micro
```

`focus` is optional, e.g. `EU only`, `app store only`, `licensing`. Run it from the root of the repo you want audited.

After answering the planning questions on the report page:

```
/compliance-audit:apply [artifact url] [--planner opus] [--implementer sonnet] [--base <branch>] [--branch-prefix <prefix>]   # default prefix compliance/
```

Implements every card not marked Done or Won't fix, one PR per card. It orders cards by dependency (legal documents last), then per card: an Opus subagent plans from the card and your saved answers and asks you anything they do not settle; `/plan-tools:split-plan` splits the plan if needed; Sonnet subagents implement it (`/plan-tools:plan-split-implment` when split); anything they surface is fixed on the same branch, never opened as a follow-up issue; `/plan-tools:finalize-pr` reviews, runs the test plan once and raises the PR against `--base` (default: the plugin setting `default_base_branch`, set with `/plugin configure compliance-audit@wovemind`; when empty, the repository's default branch) with the results in the body; the PR is set to squash auto-merge and the skill waits for the merge, merging the base branch back in whenever it moves. The card is then marked Done and the next card starts. Cards whose fix lies outside the repo (store consoles, registrations, lawyer review) are listed at the end, not implemented.

It runs unattended apart from planning questions. When stuck (auto-merge disabled, a check failing three times, a review needed for hours), it sends an ntfy push at priority 4 and waits.

Requires the `plan-tools` and `ntfy` plugins from this marketplace, `gh` authenticated with push access, and auto-merge enabled on the repo. The artifact URL defaults to the newest compliance audit for the current repo. Re-running resumes: Done cards are skipped and open card PRs are picked up where they were.

## What a run does

1. **Detect** — runs `detect_signals.py` and `license_scan.py`, then reads what scripts cannot judge (legal pages, consent UI, retention jobs, logging, store manifests).
2. **Ask** — at most two grouped question rounds (markets, entity size, B2C/B2B, minors; then AI, payments, marketing comms, sub-processors as relevant), merged into one when the code already answers most of round 1. Anything the code already answers is not asked; unanswered questions get a default marked "(assumed)".
3. **Route** — loads only the reference modules that apply (privacy per jurisdiction, app stores, EU digital acts, AI, payments, minors, accessibility, licensing, security, contracts).
4. **Audit** — checks each requirement against the code and config, assigns a severity, picks an owner.
5. **Report** — fills `skills/audit/assets/report-template.html` and publishes it as an Artifact. Re-running the audit republishes to the same artifact, so statuses and answers carry over. Nothing in the audited repo is written or modified.

## What gets written

A private claude.ai Artifact page (requires Claude Code with Artifacts enabled), with these sections:

- Header, disclaimer, how-to-read legend and summary counts
- **Profile** — markets, company, product, detected signals, assumptions, rule sets checked, licence scan, sources re-verified
- **Blockers** — store rejection or unlawful to distribute today, with `file:line` evidence
- **Required** — legal duty unmet, lower enforcement risk or a future deadline (date stated)
- **Recommended** — best practice, "appropriate measures", or depends on an unsure answer
- **Notes** — informational, more than 12 months out, or below a threshold
- **Checked and fine**
- **Needs a lawyer** — always present and non-empty
- **Deadlines** — date | obligation | status

Secret values are never copied into the report, only their `file:line`.

## Modules

Reference modules in `skills/audit/references/`, loaded only when they apply:

| Module | Scope |
|---|---|
| `privacy-gdpr-uk.md` | EU GDPR, UK GDPR, ePrivacy/PECR, DUAA 2025: notices, cookies, data-subject rights, retention, DPAs, transfers, breach, representatives, ICO fee. |
| `security-baseline.md` | "Appropriate technical measures" mapped to FastAPI/Go, Postgres, Redis, Railway and mobile: TLS, hashing, secrets, backups, logs, auth hardening, disclosure. |
| `contracts-docs.md` | Privacy policy, terms/EULA, DPA and sub-processors, cookie and refund policies, liability, governing law, imprint, trademarks, notices. |
| `licensing-sbom.md` | OSS licence compatibility (SaaS vs distributed app), attribution, SBOM, AI model/API terms, fonts and assets. |
| `privacy-us.md` | US state comprehensive laws and thresholds, GPC, CCPA links, FTC Act §5, CAN-SPAM, TCPA, Health Breach Notification Rule, state breach laws. |
| `privacy-israel-singapore.md` | Israel PPL + Amendment 13, Data Security Regulations, Spam Law; Singapore PDPA, DPO, breach notification, DNC Registry, Spam Control Act. |
| `payments.md` | PCI DSS scope, Apple IAP / Play Billing, restore and subscription disclosures, US auto-renewal laws, EU withdrawal and price rules, VAT/GST, disputes. |
| `ai-features.md` | EU AI Act Art. 50 transparency and risk screening, GDPR for LLM vendors, US state AI laws, store AI-content policies, prompt-injection cross-ref. |
| `minors.md` | COPPA amended Rule, Apple Kids / Play Families, GDPR Art. 8, UK Children's Code and Online Safety Act, US state kids and app-store age laws. |
| `app-stores.md` | Apple and Google Play rules: privacy manifest and labels, Data safety, account deletion, Sign in with Apple, ATT, permission strings, target API, developer verification, DSA trader status, Capacitor specifics. |
| `eu-digital-acts.md` | DSA, AI Act literacy, Cyber Resilience Act, Data Act switching, EAA, NIS2, e-commerce information duties, geo-blocking, P2B — each with a scope test and micro-entity default. |
| `accessibility.md` | WCAG 2.1 AA / EN 301 549 checks mapped to code, native screen-reader and text-size checks, EAA, ADA Titles II/III, UK Equality Act, accessibility statement, store labels. |

`_index.md` holds the routing table (signal/answer → modules) that SKILL.md embeds, plus each module's `applies-when` and `last-reviewed` lines.

## Scripts

All Python 3 stdlib, in `skills/audit/scripts/`. Each detector has a `--selftest` that exits 1 on failure.

| Script | Usage | Output |
|---|---|---|
| `detect_signals.py` | `detect_signals.py <repo> [--json]` / `--selftest` | `{"stack", "signals": {id: [{file, line, match}]}, "missing"}`; up to 5 hits per signal. `missing` means "not detected", never "absent". |
| `license_scan.py` | `license_scan.py <repo> [--json]` / `--selftest` | `{"ecosystems", "packages": [{name, version, license, class, via}], "flags", "tool_used", "notes"}`; classes `strong_copyleft`, `weak_copyleft`, `permissive`, `unknown`. Uses `pip-licenses` / `go-licenses` / `license-checker` when available, else reads `.venv` metadata, `node_modules`, or manifest names. Never installs into the audited repo. |
| `check_sources.py` | `check_sources.py [references_dir]` | Maintainer tool: `status  last-modified  url` for every source; exits 1 on any 4xx. |

`skills/apply/scripts/` (used by `apply`):

| Script | Usage | Output |
|---|---|---|
| `parse_cards.py` | `parse_cards.py <report.html>` / `--selftest` | JSON list of cards: `id`, `sid` (title slug, the db key for status and answers), `severity`, `risk`, `title`, `sections`, `questions`. |
| `wait_pr.sh` | `wait_pr.sh <pr> [interval=60] [max-hours=6]` | Polls a PR; exit 0 merged, 10 behind/conflicting, 20 closed, 30 check failed, 40 timed out. |

`detect_signals.py` skips tests, comment lines, Markdown prose, lockfiles, virtualenvs, `node_modules`, build output and `.claude/` worktrees, so evidence points at shipped code.

## Maintainers

Every module in `skills/audit/references/` starts with a `last-reviewed: YYYY-MM-DD` line and a `sources:` bullet list.

- **90-day freshness rule:** during an audit, a module whose `last-reviewed` is older than 90 days has its first sources re-fetched and the report records what was re-verified. The audit never edits references.
- **Adding a module:** copy the header format of an existing module exactly (`# Title`, `last-reviewed:`, `applies-when:`, `sources:` list, then `## Who it applies to and thresholds`, `## Requirements → checks` with the 7-column table, `## Deadlines`, `## Needs a lawyer`); use only signal IDs that `detect_signals.py` emits; keep it 80–200 lines. Then add a routing row to table 1 of `_index.md`, copy its `applies-when:` line verbatim into table 2 and its date into table 3, list it in the Modules table above, run `check_sources.py`, and bump `version` in `.claude-plugin/plugin.json`.
- **Refreshing a module:** run `python3 skills/audit/scripts/check_sources.py`, fix any 4xx or moved URLs, re-read the sources for changed thresholds, deadlines or effective dates, update the tables, then bump `last-reviewed:` to today and bump `version` in `.claude-plugin/plugin.json`.

## Example report excerpt

From a real run on a FastAPI + Capacitor family app (names and paths anonymised):

```
## Profile
- Markets: EU/EEA, US, UK, Israel, Singapore (detected: the privacy policy says the app is available globally).
- Entity size: micro (answer) · Customers: B2C (detected) · Minors: yes, inside a parent-managed account (detected).
- Questions asked: one round: entity size → micro; AI use → generated labels, no chatbot; marketing messages → transactional only;
  sub-processor list complete? → unsure. Defaults used: data residency "unsure" (assumed); breach in last 24 months "no" (assumed).
- Modules loaded: privacy-gdpr-uk, security-baseline, contracts-docs, licensing-sbom, app-stores, eu-digital-acts, privacy-us,
  privacy-israel-singapore, ai-features, minors, accessibility. Skipped: payments (no payment SDK; terms say the app is free).

## Blockers
1. **Analytics device cookie is set before any consent** — ePrivacy Directive Art. 5(3); UK PECR reg. 6 — `app/main.py:63`
   Gap: Every visitor receives a persistent analytics identifier and events are sent to the analytics provider before any choice is offered.
   Fix: Do not mint the cookie or send events until the parent opts in; make "decline" as easy as "accept"; keep the settings toggle for withdrawal.
   Owner: engineer · Source: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32002L0058
```

A Capacitor shell that loads a remote server (`server.url`) gets a scoped report: server-side items (accounts, deletion, legal pages) are marked "verify in the server repo" and never become Blockers from the shell alone. Audit the server repo too.

## Disclaimer

This plugin produces an automated compliance audit to help prioritise work. It is not legal advice, does not create a lawyer-client relationship, and may be incomplete or out of date. Confirm anything marked "Needs a lawyer", and any decision with legal consequences, with qualified counsel in the relevant jurisdiction.
