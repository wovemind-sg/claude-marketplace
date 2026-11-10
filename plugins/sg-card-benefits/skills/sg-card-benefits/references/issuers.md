# Issuer Source Registry & Discovery

Where each Singapore issuer publishes card benefit information, how they publish changes, and how to (re)discover documents when URLs move. URLs below are entry points known to be stable patterns — **verify each on first use** and persist the verified/resolved URL into `registry.json`. Bank sites redesign; the discovery process at the bottom is the durable part.

## Source types (reliability order)

1. **tnc-pdf** — Official Terms & Conditions PDF for the card/rewards programme. Legally binding, most precise, slowest to update visually but authoritative.
2. **reward-guide** — Official rewards programme guide/brochure (often PDF). Rates, caps, tables.
3. **card-page** — Marketing page for the card. First place headline rates change; imprecise on conditions.
4. **announcements** — "Important notices" / "Updates to terms" pages. Where **future** changes appear first, often 30–60 days before effective date. Fetch every run. Every issuer has one even where the profiles below don't list a URL — locate it during seeding via discovery; a missing `announcements_url` is a registry gap to fill, never a reason to skip the early-warning fetch.
5. **faq** — Official FAQ. Useful for interpretation disputes (e.g. what counts as "online").

## Issuer profiles

### DBS / POSB (same platform, dbs.com.sg)
- Cards hub: `https://www.dbs.com.sg/personal/cards/credit-cards/default.page`
- T&C hub: `https://www.dbs.com.sg/personal/support/card-terms-conditions.html` — PDFs live under `dbs.com.sg/iwov-resources/...`
- Rewards T&C: search site for "DBS Rewards Programme Terms" PDF
- Announcements: `https://www.dbs.com.sg/personal/support/` + card-specific "important information" blocks on each card page
- Publishing pattern: changes announced as dated inserts on the card page and revised T&C PDFs; PDF filenames often carry dates — filename change is itself a change signal.
- Key cards: Woman's World Card, Woman's Card, Altitude (Visa/Amex), Vantage, yuu Card, Live Fresh, Takashimaya, SAFRA, POSB Everyday Card.

### UOB (uob.com.sg)
- Cards hub: `https://www.uob.com.sg/personal/cards/`
- T&C: each card page links PDFs under `uob.com.sg/web-resources/...`; rewards governed by "UOB Rewards Programme" + card-specific T&Cs
- Announcements: `https://www.uob.com.sg/personal/cards/card-updates.page` (card updates/notices page — verify path)
- Publishing pattern: UOB is the most active changer of bonus mechanics (per-S$5 UNI$ blocks, contactless definitions). Announces via dated notices with explicit effective dates.
- Key cards: Lady's Card / Lady's Solitaire, Preferred Platinum Visa, Visa Signature, PRVI Miles, One Card, EVOL, Absolute Cashback, KrisFlyer UOB.

### OCBC (ocbc.com)
- Cards hub: `https://www.ocbc.com/personal-banking/cards`
- T&C: `https://www.ocbc.com/personal-banking/help-and-support/terms-and-conditions` — card + rewards programme PDFs
- Announcements: notices section on card pages; OCBC also mails/publishes "changes to terms" PDFs
- Key cards: 365, Rewards (Titanium), 90°N (Visa/Mastercard), INFINITY Cashback, FRANK, Great Eastern.

### Citibank Singapore (citibank.com.sg)
- Cards hub: `https://www.citibank.com.sg/credit-cards/`
- T&C: each card has "Terms and Conditions" PDF links; rewards under "Citi ThankYou Rewards" / card-specific programme T&Cs
- Announcements: `https://www.citibank.com.sg/` important information / updates section
- Publishing pattern: Citi changes points-per-dollar and exclusion lists via revised programme T&Cs; watch the "Citi Rewards Card" bonus exclusion list closely (travel, mobile wallet nuances).
- Key cards: Rewards, PremierMiles, Cash Back, Cash Back+, Prestige, Ultima.

### HSBC Singapore (hsbc.com.sg)
- Cards hub: `https://www.hsbc.com.sg/credit-cards/`
- T&C: card pages link PDFs; rewards programme T&C separate
- Key cards: Revolution, Live+, TravelOne, Visa Infinite, Premier Mastercard.
- Watch: Revolution's bonus categories and cap have changed repeatedly.

### Standard Chartered Singapore (sc.com/sg)
- Cards hub: `https://www.sc.com/sg/credit-cards/`
- T&C: `https://www.sc.com/sg/terms-and-conditions/` + per-card PDFs
- Key cards: Simply Cash, Smart, Journey, X Card (if extant), Priority/Visa Infinite.

### Maybank Singapore (maybank2u.com.sg)
- Cards hub: `https://www.maybank2u.com.sg/en/personal/cards/`
- Key cards: Family & Friends, Horizon Visa Signature, World Mastercard, Platinum Visa.
- Watch: Family & Friends category list and 8% tiers change often.

### CIMB Singapore (cimb.com.sg)
- Cards hub: `https://www.cimb.com.sg/en/personal/products/cards.html`
- Key cards: Visa Signature, World Mastercard, AWSM, Visa Infinite.

### American Express Singapore (americanexpress.com/sg)
- Cards hub: `https://www.americanexpress.com/sg/credit-cards/`
- T&C: per-card T&C pages + Membership Rewards T&C
- Key cards: KrisFlyer Credit Card, KrisFlyer Ascend, Platinum Charge, Platinum Credit, True Cashback.

### Trust Bank (trustbank.sg)
- Card page: `https://trustbank.sg/credit-card/` (+ link rewards T&C PDF)
- Digital bank — changes land quickly and quietly on the app/site; check monthly promos page too.

### Digital banks / fintech (verify current card offerings before tracking)
- **GXS** (gxs.com.sg) — GXS FlexiCard / debit card, if current.
- **MariBank** (maribank.sg) — Mari Credit Card, if current.
- **Chocolate Finance** (chocolatefinance.com) — Chocolate Visa debit card; miles programme T&Cs on site.
- These issuers may launch/kill products fast; on each run confirm the product still exists before diffing.

## registry.json shape

```json
{
  "dbs": {
    "issuer_name": "DBS Bank",
    "announcements_url": "https://...",
    "cards": {
      "womans-world-card": {
        "card_name": "DBS Woman's World Card",
        "sources": [
          {"id": "tnc-pdf-card", "type": "tnc-pdf", "url": "https://...", "last_hash": "…", "last_fetched": "2026-08-07", "status": "ok"},
          {"id": "tnc-pdf-rewards", "type": "tnc-pdf", "url": "https://...", "last_hash": "…", "last_fetched": "2026-08-07", "status": "ok"},
          {"id": "card-page", "type": "card-page", "url": "https://...", "last_hash": "…", "last_fetched": "2026-08-07", "status": "ok"}
        ]
      }
    }
  }
}
```

`status`: `ok` | `stale` (fetch failing, keep old data) | `moved` (relocated — old URL kept in `previous_urls`).

`id` must be unique per card — it names the raw file and is referenced by `source_id` in the card JSON. Multiple documents of one type get suffixes (`tnc-pdf-card`, `tnc-pdf-rewards`). `last_hash` advances only after Phase 4 promotes a validated snapshot, never at fetch time.

## Discovery process

Use when a URL 404s, redirects to a homepage, a registry entry is missing a URL the workflow needs (e.g. no `announcements_url`), or you're adding a new card/issuer:

1. **Site search first**: WebSearch `site:<issuer-domain> "<card name>" terms and conditions` and `site:<issuer-domain> "<card name>" filetype:pdf`.
2. **Walk from the cards hub**: fetch the issuer cards hub, find the card's page, harvest every T&C/PDF link on it.
3. **Blog tripwire** (locate only, never extract values): search MileLion / SingSaver / Seedly for the card — their articles link official PDFs and flag recent changes worth verifying.
4. **PDF vs page mismatch**: if the card page shows a rate the T&C PDF doesn't support, hunt for a *newer* T&C PDF before concluding conflict — marketing usually updates first.
5. Persist every resolved URL to `registry.json` with `status: ok`; move the dead one to `previous_urls`.

## Adding a new issuer — checklist

1. Identify official domain(s). Beware lookalike/affiliate domains — official only.
2. Locate: cards hub, T&C hub/pattern, announcements page, FAQ.
3. For each card to track: locate T&C PDF + reward guide + card page. Minimum viable = card page + one official T&C document.
4. Note the issuer's publishing pattern (dated notices? silent PDF swaps? app-only announcements?) — record as `notes` in the registry entry.
5. First run = baseline only, no change report.
