# Normalization: Vocabulary, Conversions, MCC Knowledge, SG Gotchas

The point of normalization: two runs over reworded-but-identical terms must produce identical JSON, and genuinely different terms must produce different JSON. Map issuer language onto the canonical vocabulary below; never let marketing phrasing leak into values.

## Canonical spend categories

| Enum | Issuer phrasings to map here |
|------|------------------------------|
| `all` | base rate, "all spend", "all eligible transactions", "local retail" + "overseas retail" combined base |
| `online` | "Eligible Online Transactions", "Online Retail Transactions", "online purchases", "e-commerce", "card-not-present" |
| `contactless` (channel) | "Paywave", "PayPass", "tap", "contactless transactions" |
| `mobile_wallet` (channel) | "Apple Pay/Google Pay/Samsung Pay", "mobile contactless" — NOTE: some issuers distinguish mobile wallet from physical-card contactless; if T&C does, keep them separate via `channel` |
| `dining` | "food & beverages", "restaurants", "F&B", "dining & food delivery" (if delivery included — check!) |
| `groceries` | "supermarkets", "grocery stores", "online grocery" |
| `transport` | "land transport", "ride-hailing", "Grab/Gojek/TADA", "SimplyGo", "taxis", "bus & MRT" |
| `petrol` | "fuel", "petrol service stations" |
| `travel` | "air tickets, hotels, travel agencies" as a bundle — if issuer splits airlines/hotels, use `airlines` / `hotels` |
| `overseas` | "foreign currency spend", "overseas transactions" — always a *category*, never a `channel`; clarify FCY-based vs geography-based in `source_quote` |
| `entertainment` | "movies", "cinemas", "attractions", "leisure" |
| `streaming` | "digital subscriptions", "streaming services" |
| `utilities` | "recurring bills", "telco", "electricity" |
| `insurance`, `education`, `government`, `healthcare` | usually exclusions, occasionally earn categories |
| `shopping` | "retail", "department stores", "fashion" |

If an issuer defines a category by an explicit merchant or MCC list that doesn't match any enum well, pick the closest enum and put the definition in `source_quote` — the diff still works because the enum + quote are both compared.

## Points → miles conversions (`reward_currency_to_miles`)

Verify on first use per issuer — conversion ratios and transfer partners change. Historical stable values:

| Currency slug | Issuer | Miles per unit | Earn basis gotcha |
|---|---|---|---|
| `dbs_points` | DBS/POSB | 2.0 | earned per S$5 block |
| `uni_dollars` | UOB | 2.0 | earned per S$5 block |
| `ocbc_rewards` (OCBC$) | OCBC | 0.4 | per S$1 |
| `citi_points` (ThankYou) | Citi | 0.4 | per S$1 |
| `sc_points` (360° Rewards) | SC | ~0.4 | check current programme |
| `hsbc_points` | HSBC | 0.4 | per S$1 |
| `treats_points` | Maybank | 0.4 | per S$1 |
| `mr_points` | Amex | varies by card (KrisFlyer cards earn miles direct) | — |

**mpd math**: "10X points" ≠ 10 mpd. Compute: points-per-dollar × miles-per-point. DBS 10X = 10 points/S$5 blocks ≈ 4 mpd. UOB "10X UNI$" = UNI$10 per S$5 = 4 mpd. Always publish `rate` in mpd, keep the raw mechanic in `source_quote`.

**Block rounding**: per-S$5-block earners (DBS, UOB) forfeit remainders — a S$4.99 transaction can earn 0 bonus. Record `"conditions": ["per_5sgd_block"]` when the T&C states block-based earning; a switch between per-S$1 and per-S$5 earning is a **breaking/beneficial change** worth reporting even if headline mpd is unchanged.

## Common MCC exclusion knowledge

Standard SG exclusion lists cluster around these. Use to map MCC lists → `categories` rollup (never the reverse — don't invent MCCs from category names):

| Category | Typical MCCs |
|---|---|
| `government` | 9211, 9222, 9223, 9311, 9399, 9402 |
| `education` | 8211, 8220, 8241, 8244, 8249, 8299 |
| `insurance` | 5960, 6300, 6381 |
| `financial` | 6010, 6011, 6012, 6051, 6211, 6540 (incl. quasi-cash, crypto) |
| `utilities` | 4900 |
| `healthcare_public` | 8062 (hospitals), 8011, 8021, 8099 — some issuers exclude only public hospitals by merchant |
| `charity` | 8398 |
| `prepaid_topup` | 6540 + named merchants: AXS, SAM, EZ-Link, GrabPay top-up, YouTrip/Revolut/Wise top-up |
| `real_estate/rent` | 6513 + rent platforms (CardUp, ipaymy, RentHero) |

Wallet top-up exclusions are the most volatile — GrabPay/ShopeePay/prepaid-wallet top-ups get added to exclusion lists frequently. Diff `merchants` and `payment_types` carefully.

## Parsing SG issuer language — gotchas

- **"S$" amounts**: strip `S$`, commas. "S$3,000" → `3000`.
- **"first S$X of spend"** → cap: `{"amount": X, "unit": "spend_sgd", "scope": "bonus_only"}` (base usually still earns beyond; if T&C says nothing earns beyond, `scope: total`).
- **"capped at X points/miles/cashback"** → cap in that unit; optionally derive spend-equivalent in `notes`.
- **"per calendar month" vs "per statement cycle"**: NOT the same — statement cycles vary per customer. Map to `monthly` vs `statement_cycle` faithfully. A silent switch between them is a real (usually breaking) change.
- **"eligible transactions"**: always defined somewhere in the T&C — find the definition clause; it's where exclusions hide.
- **"with effect from [date]"** / "w.e.f." → `scheduled_changes.effective_date` if future, else already-effective.
- **"up to X mpd"**: marketing for a tiered/conditional rate. Extract the tiers as separate `earn_rates` entries with conditions; never store "up to" as the rate.
- **Contactless vs mobile-wallet drift**: issuers have narrowed "contactless" to "mobile contactless (excluding physical card taps)" — a channel narrowing is a breaking change; compare `channel` precisely.
- **Debit cards**: same schema; watch salary-credit/balance conditions (`requirements`) — GXS/Trust/MariBank/Chocolate tie rates to deposits.
- **Fee amounts include GST** (9% from 2024): issuers quote fees GST-inclusive; store as printed. A fee change that's purely a GST-rate change is `neutral` — note it.
- **Miles cards with direct-earn** (Amex KrisFlyer, KrisFlyer UOB): `reward_currency: miles_direct`, rate already in mpd.
- **Multi-condition bonuses** (UOB One-style: spend + N transactions + salary credit): model as `earn_rates` with `conditions` + `minimum_spend` entries; the rebate tiers become multiple entries carrying `tier: 1..n` (ascending threshold) so each stays uniquely diffable. Ugly but diffable — the alternative (prose) is undiffable.
