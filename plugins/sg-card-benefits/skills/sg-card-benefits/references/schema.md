# Normalized Card JSON Schema

One JSON file per card at `cards/<issuer>/<card-slug>.json`. The schema is designed to be **diffable**: stable keys, canonical enums, numbers not prose. If two extractions of semantically identical terms produce different bytes, that's a bug in the extraction, not a card change.

## Determinism rules (non-negotiable)

- All object keys sorted alphabetically when serializing (`json.dumps(..., sort_keys=True, indent=2)` or `jq -S`).
- Arrays sorted by a stable key: `earn_rates` by `category`, `channel`, `tier`; `caps` by `applies_to`, `period`, `unit`, `scope`; `minimum_spend` by `period`, `amount`; `promotions` by `ends`, `name`; `other_benefits` by `name`; `exclusions.mcc` numerically; `scheduled_changes` by `effective_date`; `sources` by `id` (ids are unique per card).
- Dates: ISO `YYYY-MM-DD`. Money: plain numbers in SGD (no "S$", no commas). Percentages as numbers (`1.5` = 1.5%). Rates as numbers (`4` = 4 mpd).
- Absent ≠ null: omit fields you found no evidence for; use `null` only for "explicitly stated as none" (e.g. `"annual_fee": 0` fee-free forever vs omitted = unknown).
- No free-text values except `source_quote`, `notes`, and `name` fields. Everything else: enums and numbers from `normalization.md`.
- Any object carrying a `source_quote` also carries `source_id` — the `sources[].id` the evidence came from. Field-level provenance drives the extractor-drift guard and conflict resolution in `change-detection.md`.

## Top-level structure

```json
{
  "schema_version": 1,
  "issuer": "dbs",
  "card_slug": "womans-world-card",
  "card_name": "DBS Woman's World Card",
  "card_kind": "credit",
  "network": "mastercard",
  "reward_currency": "dbs_points",
  "reward_currency_to_miles": 2.0,
  "as_of": "2026-08-07",
  "earn_rates": [],
  "caps": [],
  "minimum_spend": [],
  "exclusions": {},
  "eligibility": {},
  "fees": {},
  "travel_benefits": {},
  "other_benefits": [],
  "promotions": [],
  "scheduled_changes": [],
  "sources": [],
  "extraction_flags": []
}
```

- `card_kind`: `credit` | `debit` | `charge` | `prepaid`
- `network`: `visa` | `mastercard` | `amex` | `unionpay` | `jcb`
- `reward_currency`: issuer points currency slug (see normalization.md) | `cashback` | `miles_direct`
- `reward_currency_to_miles`: miles per point unit, if convertible (omit for pure cashback)
- `as_of`: date this state was extracted
- `extraction_flags`: array of `{"field": "...", "flag": "ambiguous|conflict|stale_source|assumed", "detail": "...", "source_quote": "..."}` — the honesty channel; anything you weren't sure about goes here

## earn_rates

One entry per (category, channel) combination that earns differently from base. Always include the base rate as `category: "all"`.

```json
{
  "category": "online",
  "channel": "any",
  "rate": 4.0,
  "rate_unit": "mpd",
  "conditions": ["mobile_wallet_required"],
  "source_id": "tnc-pdf-card",
  "source_quote": "10X DBS Points on online purchases"
}
```

- `category`: canonical enum from normalization.md (`all`, `online`, `dining`, `groceries`, `transport`, `petrol`, `travel`, `overseas`, `entertainment`, `streaming`, `utilities`, `insurance`, `education`, `government`, `healthcare`, `shopping`, `airlines`, `hotels`, …)
- `channel`: `any` | `online` | `in_store` | `contactless` | `mobile_wallet`. Geography is never a channel — overseas/FCY spend is the `overseas` *category*. Use channel `online` only to restrict a category bonus (e.g. online grocery → category `groceries`, channel `online`); a plain online-spend bonus is category `online`, channel `any`.
- `tier`: only when multiple entries legitimately share category+channel (tiered programmes like UOB One): integer `1..n` by ascending qualification threshold. Diff identity for `earn_rates` = category+channel+tier.
- `rate_unit`: `mpd` (miles per dollar) | `cashback_pct` | `points_per_dollar`
- **Always express miles cards in `mpd`** after applying the points→miles conversion — that's the comparable unit. Record the raw points mechanics in `source_quote`.
- `conditions`: canonical condition slugs (`min_spend_required`, `mobile_wallet_required`, `contactless_only`, `salary_credit_required`, `selected_categories_only`, …)

## caps

```json
{
  "applies_to": "online",
  "amount": 1500,
  "unit": "spend_sgd",
  "period": "monthly",
  "scope": "bonus_only",
  "source_quote": "first S$1,500 of eligible spend per calendar month"
}
```

- `unit`: `spend_sgd` (cap on spend earning bonus) | `reward_sgd` (cashback dollar cap) | `points` | `miles`
- `period`: `monthly` | `quarterly` | `annual` | `statement_cycle` | `promo_period`
- `scope`: `bonus_only` (base still earns past cap) | `total`
- Normalize to the spend-basis when the wording allows ("capped at S$120 cashback at 8%" on a category → also derivable as S$1,500 spend; store what the issuer states, put the derivation in `notes` if helpful).

## minimum_spend

```json
{
  "amount": 800,
  "period": "monthly",
  "unlocks": ["dining", "groceries"],
  "counts_excluded_spend": false,
  "source_quote": "min. spend S$800 per month"
}
```

## exclusions

```json
{
  "mcc": [6300, 8211, 8220, 9211, 9222, 9311, 9399],
  "categories": ["insurance", "education", "government"],
  "merchants": ["AXS", "SAM"],
  "payment_types": ["prepaid_topup", "installment_plans", "bill_payment_via_bank"],
  "wallets_excluded": [],
  "notes": ""
}
```

MCC list is the ground truth when the T&C provides one; `categories` is the normalized rollup (see MCC table in normalization.md). If the T&C names categories without MCCs, fill `categories` only — do not invent MCC numbers.

## eligibility / fees

```json
"eligibility": {
  "min_income_sgd": 30000,
  "min_income_foreigner_sgd": 45000,
  "min_age": 21,
  "new_customer_only": false,
  "requirements": ["salary_credit_required"]
},
"fees": {
  "annual_fee_sgd": 196.20,
  "fee_waiver": {"type": "conditional", "condition_spend_sgd": 25000, "years_free": 1},
  "supplementary_fee_sgd": 98.10,
  "foreign_transaction_pct": 3.25
}
```

`fee_waiver.type`: `none` | `first_year` | `conditional` | `perpetual`.

## travel_benefits

```json
{
  "lounge_visits_per_year": 2,
  "lounge_program": "priority_pass",
  "travel_insurance_coverage_sgd": 1000000,
  "travel_insurance_condition": "fare_charged_to_card",
  "limo_rides_per_quarter": 0,
  "airport_transfer_condition": null
}
```

## promotions (time-boxed offers, kept separate from permanent terms)

```json
{
  "name": "krisflyer-welcome-bonus-2026-09-30",
  "description_quote": "…",
  "benefit": {"type": "bonus_miles", "amount": 30000},
  "requires": {"spend_sgd": 3000, "within_days": 60, "new_customer_only": true},
  "starts": "2026-07-01",
  "ends": "2026-09-30"
}
```

`name` is deterministic: slugified official promo title + end date. Never coin a freeform name — it's the diff identity key; if the issuer retitles the promo, diff matching falls back to (`benefit.type`, `ends`).

Promotions expiring is a *neutral-expected* change (report as "promotion expired", not "benefit removed").

## scheduled_changes — the early-warning payload

Announced changes not yet effective. **Extract these aggressively**; they're the reason this tracker exists.

```json
{
  "announced_date": "2026-07-15",
  "effective_date": "2026-09-01",
  "field_path": "caps[applies_to=online].amount",
  "old_value": 2000,
  "new_value": 1500,
  "classification": "breaking",
  "source_quote": "With effect from 1 September 2026, ...",
  "source_url": "https://..."
}
```

Maturation happens in Phase 4's date pass on **every** run — it must never depend on a source changing: when `effective_date` ≤ today, apply the change to the main body, remove it from `scheduled_changes`, and report it as "previously announced change now in effect".

## sources

```json
{
  "id": "tnc-pdf-card",
  "type": "tnc-pdf",
  "url": "https://...",
  "fetched_at": "2026-08-07",
  "content_hash": "sha256:…",
  "document_date": "2026-06-01"
}
```

`id` must be unique within the card — issuers often publish both a card T&C and a rewards-programme T&C; suffix them (`tnc-pdf-card`, `tnc-pdf-rewards`). The id names the raw file (`raw/<issuer>/<card-slug>/<id>.<ext>`) and is the target of every `source_id` reference.

`document_date`: the version/effective date printed in the document itself, when present — key input for conflict resolution.
