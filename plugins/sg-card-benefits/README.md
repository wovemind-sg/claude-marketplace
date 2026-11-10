# sg-card-benefits

**This plugin is specific to Singapore.** It knows Singapore card issuers, their documents and Singapore-dollar terms, and is of little use for cards issued elsewhere.

Claude Code skill that monitors Singapore credit/debit card benefits and T&Cs for changes — before caps, exclusions, and nerfs hit your rewards.

## What it does

- Fetches official issuer sources (T&C PDFs, reward guides, card pages, announcements, FAQs) for every major SG issuer: DBS/POSB, UOB, OCBC, Citi, HSBC, SC, Maybank, CIMB, Amex, Trust, GXS, MariBank, Chocolate Finance.
- Extracts structured terms: earn rates (normalized to mpd / cashback %), caps, minimum spend, MCC/merchant exclusions, eligibility, fees, lounge/travel benefits, promotions.
- Extracts **scheduled future changes** ("with effect from 1 Sep…") — the early warning that matters.
- Normalizes into deterministic JSON (stable keys, canonical vocabulary) so runs are byte-comparable.
- Diffs against the previous snapshot, classifies each change (breaking / beneficial / neutral), and writes a dated change report. Wording-only changes are suppressed.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install sg-card-benefits@wovemind
```

## Usage

```
/sg-card-benefits:sg-card-benefits uob citibank
/sg-card-benefits:sg-card-benefits all --data-dir ~/card-data
```

First run seeds a source registry and establishes baselines (no diff report). Subsequent runs (daily recommended) hash-skip unchanged sources, extract only what changed, and report diffs. State lives entirely in the data directory — safe to commit to a private repo for history.

## Example change report

Say you ran `/sg-card-benefits:sg-card-benefits uob` last week, and UOB has since published a notice that lowers a bonus cap from September. The next run fetches the notice, sees that the extracted cap differs from the stored snapshot, classifies the change as breaking because it reduces your rewards, and lists it under "Upcoming" in the dated report it writes to the data directory:

```markdown
## ⚠️ Upcoming
- UOB Lady's Card — monthly bonus cap S$2,000 → S$1,500, effective 2026-09-01 (announced 2026-07-15)
```

## Requirements

- Claude Code with WebFetch/WebSearch enabled. No API keys, no scraper dependencies — the skill is expert knowledge; Claude does the fetching and interpretation.

## Environment variables

None.

## Notes

- Official issuer sources only for facts; blogs (MileLion etc.) used only to locate documents.
- Adding an issuer/card: see the checklist in `skills/sg-card-benefits/references/issuers.md`.
