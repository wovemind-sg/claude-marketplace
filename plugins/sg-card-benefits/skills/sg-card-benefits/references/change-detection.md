# Change Detection, Validation, Conflicts, Recovery

## Diff strategy

Diff **normalized JSON vs normalized JSON** — never page text vs page text. Because both sides obey the determinism rules in `schema.md`, the diff is a straightforward structural comparison:

1. Load the current `cards/<issuer>/<card-slug>.json` and the staged `.new.json` from Phase 3. The Phase 4 date pass (scheduled changes maturing, promotions expiring) produces diff entries even when no source changed.
2. Compare field-by-field. For arrays, match entries by their identity keys (`earn_rates`: category+channel+tier; `caps`: applies_to+period+unit+scope; `exclusions.mcc`: set diff; `promotions`: `name`, falling back to (`benefit.type`, `ends`) when only the title changed).
3. Ignore in the diff: `as_of`, `sources[].fetched_at`, `sources[].content_hash`, `source_quote` changes where the parent value is unchanged (rewording), `extraction_flags`.
4. Every surviving difference is a candidate change. Classify it (below), then decide report/suppress.

### Classification

| Class | Meaning | Examples |
|---|---|---|
| `breaking` | worse for cardholder | rate ↓, cap introduced/↓, MCC/merchant added to exclusions, min spend ↑, lounge visits ↓, fee ↑, channel narrowed (contactless → mobile-wallet-only), period monthly → statement_cycle when it reduces value |
| `beneficial` | better | rate ↑, cap ↑/removed, exclusion removed, min spend ↓, fee ↓/waiver added, new category added |
| `neutral` | no cardholder impact | rewording (quote changed, value same), document URL moved, GST-driven fee restatement, promotion expired on its stated end date, category re-bucketing with same effective rate |

Report breaking + beneficial always; neutral only as a one-line footnote (or suppress rewording entirely).

### False-positive suppression

- Source hash unchanged → no extraction → no diff. First line of defense.
- Value unchanged + quote changed → rewording, suppress.
- Your own normalization improvement (you mapped a category differently than last run with no underlying text change): this is *extractor drift*, the worst false positive. Guard: every value carries `source_id`; if the hash of that source is unchanged but your normalized value differs from the stored one, trust the stored one and flag `extraction_flags: assumed` — **unless** a newer explicitly dated source (e.g. an announcement) changed and the precedence rules below award it the field; then the change is real.
- A change appearing simultaneously across many cards of one issuer (e.g. every card's fee +S$3): verify once against the announcement page — likely one real programme-level change; report it grouped, not as N independent surprises.

## Validation rules — run before promoting a new snapshot

Reject (flag for human review, discard the staged `.new.json`, keep the current snapshot, leave `last_hash` un-advanced so next run refetches and retries) if any of:

- `rate` outside sane bounds: mpd > 10 or < 0; cashback_pct > 15 (non-promo) or < 0.
- Cap amount ≤ 0, or monthly spend cap > 100000.
- `effective_date` in `scheduled_changes` earlier than `announced_date`.
- Any date parsed outside 2000–2100 (parser probably ate a phone number).
- Earn rates array empty for a card that previously had rates (extraction likely failed silently).
- New state loses > 50% of previously populated fields while source hashes changed only for one minor source — likely partial page load, refetch.
- `reward_currency_to_miles` differs from the known table without a supporting `source_quote` — conversion changes are rare and big news; demand evidence.

A validation failure is not silent: record it in `extraction_flags` and mention it in the run report ("DBS Altitude: extraction failed validation, kept previous state").

## Ambiguous language

When the T&C genuinely underdetermines the value:

1. Extract the most conservative (cardholder-pessimistic) reading as the value.
2. Add `extraction_flags` entry: `{"flag": "ambiguous", "field": ..., "detail": "could mean X or Y", "source_quote": "…"}`.
3. Check the official FAQ (source type `faq`) — it often resolves definitions ("do hotel bookings on airline sites count as airline spend?").
4. Do NOT resolve ambiguity from blogs. A blog interpretation may be reported in `notes` as `"community reading: …"` at most.
5. If a previously-ambiguous field's wording didn't change, keep the previous resolution — don't flip-flop between readings run to run.

## Conflicting sources

Precedence when two official sources disagree: **T&C PDF > reward guide > card page > announcement > FAQ** — *except* when the lower-precedence source is **newer and explicitly dated** (an announcement dated after the T&C's `document_date` describing a change "with effect from…"). Then:

- Future effective date → record under `scheduled_changes`; T&C value stays current.
- Past effective date but T&C not yet updated → the announcement wins for current state; flag `conflict` so next run re-checks whether the T&C caught up.
- Marketing page shows better rate than T&C supports → hunt for newer T&C (discovery process); if none, T&C wins, flag `conflict` with both quotes.

## Error recovery

| Failure | Action |
|---|---|
| Fetch 404 / redirect-to-homepage | Run discovery (issuers.md). Found → update registry, continue. Not found after discovery → mark source `stale`, keep old data, report "unverifiable since <date>". |
| Bot-blocked / CAPTCHA / JS-only page | Try the PDF sources instead (rarely blocked). Note in report; consider the announcements page via search cache. Never guess content. |
| PDF unparseable | Save raw anyway, flag `stale`, retry next run. |
| Extraction fails validation | Keep current snapshot, discard staging, don't advance `last_hash` (auto-retry next run). Escalate in report after 3 consecutive failures. |
| Source stale > 30 days | Escalate in report: "cannot verify <card> against official source for 30+ days — data may be outdated". |
| Card discontinued (page removed, "no longer available") | Don't delete the card file. Set `extraction_flags: [{"flag": "assumed", "detail": "card appears discontinued <date>"}]`, report it, stop fetching after user confirms removal from registry. |
| Whole-issuer site redesign (many 404s at once) | Stop per-card discovery spam; re-discover the cards hub once, rebuild that issuer's registry URLs from it. |

## Run report shape (`changes/<date>.md`)

```markdown
# SG Card Changes — 2026-08-07

## ⚠️ Upcoming (act before these dates)
- **UOB Lady's Card** — monthly bonus cap S$2,000 → S$1,500, effective **2026-09-01** (announced 2026-07-15). [source]

## Now in effect since last run
- **Citi Rewards** — mobile wallet transactions excluded from 10X, effective 2026-08-01 (previously announced). [source]

## Beneficial
- …

## Promotions
- expiring ≤ 30 days: …

## Housekeeping
- OCBC 365: T&C PDF unverifiable since 2026-07-20 (404, discovery failed) — data stale.
- Neutral/reworded: 3 suppressed.
```

Machine copy `changes/<date>.json`: array of the classified diff entries (schema.md `scheduled_changes` shape plus `card_slug`, `status: upcoming|effective|expired`).

## Maintenance recommendations

- Run daily (cheap: the curl-hash check means unchanged sources are never read into context). Weekly minimum — SG issuers commonly give ~30 days notice; weekly still catches announcements pre-effective-date.
- Monthly: sweep announcements pages of ALL issuers in registry even for untracked cards — catches new-card launches and programme-wide changes.
- Quarterly: re-verify the points→miles conversion table and lounge programme entitlements; spot-check 2–3 registry URLs per issuer for silent moves.
- When adding extraction improvements, re-run against stored `raw/` documents (not live fetches) and confirm no diffs appear for unchanged sources before trusting the next live run — protects against extractor drift.
- Keep `raw/` capped: latest + previous per source is enough; history lives in normalized `history/`.
