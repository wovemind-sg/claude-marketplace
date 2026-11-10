---
name: sg-card-benefits
description: Monitor Singapore credit and debit card benefits and terms & conditions for changes. Use whenever the user wants to track, check, compare, or get alerted about SG card rewards — miles per dollar rates, cashback, caps, MCC exclusions, minimum spend, lounge access, annual fees, or promotions — from any Singapore issuer (DBS, POSB, UOB, OCBC, Citibank, HSBC, Standard Chartered, Maybank, CIMB, Amex, Trust, GXS, MariBank, Chocolate Finance). Also use when the user asks "did anything change on my card", "run the card tracker", "check card T&Cs", or wants to add a new card or issuer to monitoring, even if they don't name this skill.
argument-hint: "[issuer or card names to check, or 'all'] [--data-dir path]"
---

# Singapore Card Benefits Tracker

Detect changes to Singapore credit/debit card benefits **before** cardholders are hurt by them. Issuers routinely add caps, exclude MCCs, raise minimum spends, and cut lounge visits — usually announced in a PDF few people read, weeks before the effective date. Your job each run: fetch official sources, extract structured card terms, normalize them into a stable JSON schema, diff against the previous snapshot, and report every material change with its effective date.

You are the interpreter, not a scraper. Issuer language is deliberately vague and inconsistent; the value of this skill is turning "bonus is awarded on the first S$3,000 of Eligible Online Transactions per calendar month" into `{"cap": {"amount": 3000, "period": "monthly", "basis": "spend"}}` — the same JSON every run, regardless of how the wording shifts.

## Reference files — read before the relevant phase

| File | When to read |
|------|--------------|
| `references/issuers.md` | Phase 2 (fetch): per-issuer source registry, publishing patterns, discovery process for new issuers/cards |
| `references/schema.md` | Phase 3 (extract): the normalized JSON schema and determinism rules |
| `references/normalization.md` | Phase 3 (extract): canonical vocabulary, points→miles conversions, MCC knowledge, SG-specific extraction gotchas |
| `references/change-detection.md` | Phases 4–5 (diff/report): diff strategy, materiality classification, validation rules, ambiguity/conflict/error handling |

## Data directory

All state lives in one directory (default `./card-data/`, override with `--data-dir`). Create on first run:

```
card-data/
├── registry.json                     # issuer → card → source URLs (seeded from references/issuers.md, grows as you discover)
├── raw/<issuer>/<card-slug>/         # latest + previous raw fetch per source, named <source-id>.<ext> and <source-id>.prev.<ext>
├── cards/<issuer>/<card-slug>.json   # current normalized state (the thing that gets diffed)
├── history/<issuer>/<card-slug>/     # dated snapshots: <YYYY-MM-DD>.json (written only when content changed)
└── changes/<YYYY-MM-DD>.md           # human report per run that found changes (+ .json machine copy)
```

`registry.json` is the durable memory of *where* to look. `references/issuers.md` seeds it; verified URLs, discovered PDFs, new cards, and per-source `last_hash`/`last_fetched` state get written back to `registry.json` — never edit the reference file at runtime.

## Workflow

### Phase 1 — Scope

Parse `$ARGUMENTS`: specific issuers/cards, or `all` (default: everything in `registry.json`). First run with no registry: seed `registry.json` from `references/issuers.md`, then confirm scope with the user if they asked for "all" — a full sweep of every SG issuer is dozens of fetches; offer to start with the issuers they actually hold cards from.

### Phase 2 — Fetch

Read `references/issuers.md`. For each card, fetch its sources in reliability order (T&C PDF → reward guide → card page → announcements → FAQ). For each source:

1. Fetch cheaply with curl to a temp file (PDFs and most pages; fall back to WebFetch only if curl is blocked or the page is JS-only).
2. Compute a content hash: PDFs — hash the file bytes; HTML — strip tags and boilerplate to text first (nav, footers, cookie banners change daily and are not signal), hash the text.
3. Compare against the source's `last_hash` in `registry.json`. **Match → update `last_fetched`, skip this source without reading it into context.** This is the main efficiency lever for daily runs — most days nothing changed. Mismatch → rename the current raw file to `<source-id>.prev.<ext>`, save the new fetch to `raw/`, and mark the card for extraction. Do NOT advance `last_hash` here — it advances only in Phase 4 once the new snapshot survives validation, so a failed extraction is retried next run.
4. On fetch failure (404, redirect to homepage, bot-block): do NOT treat as "benefits removed". Follow the error-recovery rules in `references/change-detection.md`, try the discovery process in `references/issuers.md` to relocate the document, and update `registry.json` with the new URL if found.

Also fetch the issuer's announcements/notice page even when card sources are unchanged — that's where *future* changes appear first. A registry entry with no `announcements_url` is a gap, not nothing-to-fetch: run discovery (every issuer has a notices/important-information page) and record the URL.

### Phase 3 — Extract & normalize

Only for cards where at least one source changed (or no snapshot exists yet) — date-driven updates (scheduled changes maturing, promotions expiring) need no extraction and happen in Phase 4 for every in-scope card. Read `references/schema.md` and `references/normalization.md`, then:

1. Extract every fact the schema covers: earn rates, caps, minimum spend, exclusions, eligibility, fees, travel benefits, other perks — and **all dates** (effective, announced, expiry, scheduled future changes).
2. Normalize per the vocabulary and conversion tables. Never store raw marketing phrasing as a value; map to canonical enums and numbers. Keep the exact source quote in `source_quote` fields for anything non-obvious — that's your audit trail.
3. When sources conflict or language is ambiguous, apply the precedence and ambiguity rules in `references/change-detection.md`.
4. Write the result to a staging file `cards/<issuer>/<card-slug>.new.json` following the determinism rules (sorted keys, sorted arrays, ISO dates) — a semantically identical extraction must be byte-identical. Never overwrite the current snapshot; Phase 4 diffs against it.

### Phase 4 — Validate & diff

Read `references/change-detection.md`.

1. **Date pass — every in-scope card, even with no source change:** in the stored snapshot, mature `scheduled_changes` whose `effective_date` ≤ today into the main body (report as "previously announced change now in effect") and expire promotions past their `ends` date. These produce report entries despite no fetch diff.
2. Run the validation rules on the staged JSON (rate bounds, cap sanity, date sanity). Validation failure → flag for human review, delete the staging file, keep the current snapshot, leave `last_hash` un-advanced so next run retries.
3. Diff staged JSON against the current `cards/<issuer>/<card-slug>.json` — a semantic diff over normalized fields, never a text diff of pages.
4. Classify each change: **breaking** (worse for cardholder), **beneficial**, **neutral** (reworded, restructured, no semantic change → suppress from report).
5. Real change → archive current snapshot to `history/`, promote staging over `cards/`, advance `last_hash` in `registry.json`. No semantic change → discard staging and still advance `last_hash` (wording changed, terms didn't — don't re-extract it forever).

### Phase 5 — Report

If changes found, write `changes/<date>.md` and `.json` using the report template in `references/change-detection.md` — upcoming changes lead the report; they're the whole point of daily monitoring. Every change entry states: card, field, old → new value, classification, **effective date**, announcement date, and source URL.

If no changes: say so in one line, note any sources that were unreachable or stale. Do not write a changes file for a no-change run.

## Adding an issuer or card

New card from an existing issuer: add it under the issuer in `registry.json`, run discovery (in `references/issuers.md`) to locate its T&C PDF and reward page, then run Phases 2–5 for it — first run establishes the baseline, no diff report.

New issuer: follow the "Adding a new issuer" checklist in `references/issuers.md`, then propose the entry as an addition to both `registry.json` and (for permanence) `references/issuers.md`.

## Hard rules

- Official issuer sources only for extracted facts. Blogs (MileLion, Seedly, SingSaver) may be used to *locate* official documents or as a tripwire ("blog says cap changed — go verify against the T&C"), never as the value source.
- Never report a change whose only evidence is a formatting/wording difference — normalize first, diff normalized values only.
- Every extracted number with a date attached: prefer the *effective* date over the *published* date. A T&C published today may govern terms effective next month; both dates go in the JSON.
- A missing source ≠ a removed benefit. Distinguish "couldn't verify" (mark stale, keep old data) from "verified removed" (source explicitly changed).
