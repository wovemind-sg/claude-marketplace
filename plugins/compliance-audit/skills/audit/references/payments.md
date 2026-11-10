# Payments, subscriptions and consumer-sales rules
last-reviewed: 2026-10-13
applies-when: any `pay.*` signal (`pay.stripe|revenuecat|storekit|playbilling|paddle|lemonsqueezy`) or the user says the product takes payments or sells subscriptions
sources:
- https://www.pcisecuritystandards.org/document_library/
- https://docs.stripe.com/security/guide
- https://developer.apple.com/app-store/review/guidelines/
- https://developer.apple.com/support/storekit-external-entitlement-us/
- https://developer.apple.com/support/dma-and-apps-in-the-eu/
- https://support.google.com/googleplay/android-developer/answer/9858738
- https://support.google.com/googleplay/android-developer/answer/140504
- https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-425
- https://eur-lex.europa.eu/eli/dir/2011/83/oj
- https://eur-lex.europa.eu/eli/dir/2019/2161/oj
- https://eur-lex.europa.eu/eli/dir/2023/2673/oj
- https://vat-one-stop-shop.ec.europa.eu/index_en
- https://www.gov.uk/guidance/the-vat-rules-if-you-supply-digital-services-to-private-consumers
- https://www.iras.gov.sg/taxes/goods-services-tax-(gst)/gst-and-digital-economy
- https://stripe.com/legal/dpa
- https://www.revenuecat.com/dpa/

## Who it applies to and thresholds

| Scope point | Rule |
|---|---|
| Who is merchant of record (MoR) | App Store / Play purchases (`pay.storekit`, `pay.playbilling`, `pay.revenuecat` on top of them): Apple/Google are the seller to the consumer, collect and remit VAT/GST, and handle refunds; you still own disclosure, restore and cancellation UX. Paddle / Lemon Squeezy (`pay.paddle`, `pay.lemonsqueezy`): MoR, they handle tax. Stripe direct (`pay.stripe`): **you** are the seller — all tax, consumer-law and refund duties are yours (Stripe Tax computes but you register and file). |
| PCI DSS | Applies to anyone accepting cards. v4.0.1 is current; all "future-dated" requirements mandatory since 31 Mar 2025. Fully hosted Stripe Checkout / Payment Element (iframe) → SAQ A (smallest scope). Any card field your own code renders or posts → SAQ A-EP or D. |
| Consumer subscriptions | US state auto-renewal laws (CA Bus. & Prof. Code §17600 ff., amended AB 2863 from 1 Jul 2025; NY GBL §527-a; ~half of states have one) apply when selling to consumers in that state, no size threshold. EU/UK consumer law applies to B2C sales to EU/UK consumers. |
| B2B only | Most consumer rules (withdrawal, ARL) do not apply to pure B2B; PCI DSS and tax still do. |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| Never touch raw card numbers (PAN) | PCI DSS v4.0.1 (SAQ A eligibility) | `pay.stripe`: grep templates/forms for `card_number`, `cardNumber`, `cvc`, `name="card`; ensure Stripe.js loads from `js.stripe.com` and card UI is Elements/Checkout | file:line of any own card field | Blocker if own code receives PAN; else Checked and fine | engineer | Use Stripe Checkout or Payment Element only; never log or post card data to your backend. |
| Payment page script integrity (SAQ A: scripts on the page embedding the iframe protected from tampering) | PCI DSS v4.0.1 req. 6.4.3, 11.6.1 (or SAQ A eligibility confirmation) | CSP header, SRI on third-party scripts on checkout page | Middleware/template file:line | Recommended | engineer | Add CSP and keep third-party scripts off checkout pages; complete SAQ A yearly. |
| Annual PCI self-assessment | PCI DSS; Stripe services agreement | Founder answer | — | Recommended | founder | Complete SAQ A in Stripe Dashboard (Settings → Compliance) each year. |
| Digital goods/features in iOS apps sold via In-App Purchase | Apple App Review 3.1.1 | `mobile.ios` + `pay.stripe`/web checkout links inside the app for digital content without `pay.storekit` | Purchase button file:line | Blocker (store rejection) unless an exception applies: US storefront external purchase links (court-ordered since 30 Apr 2025; Apple commission on linked purchases under remand as of Oct 2026 — confirm via source); EU DMA alternative terms; reader apps 3.1.3(a); physical goods/services 3.1.3(e) | engineer | Route digital purchases through StoreKit (or RevenueCat); use external links only under the documented entitlement/storefront rules. |
| Digital goods in Android apps via Google Play Billing | Google Play Payments policy | `mobile.android` + digital purchase without `pay.playbilling` | Purchase file:line | Blocker unless an alternative-billing / external-offers programme applies (US/EEA/other — confirm via source) | engineer | Use Play Billing (or RevenueCat) for digital goods. |
| Restore purchases | Apple 3.1.1 (restorable IAP must offer a restore mechanism) | `pay.storekit`/`pay.revenuecat`: grep `restorePurchases`, `restoreCompletedTransactions`, "Restore" button | file:line or "not found" | Blocker (store rejection) | engineer | Add a visible "Restore purchases" button calling `Purchases.restorePurchases()` / `AppStore.sync()`. |
| Subscription disclosure before purchase (title, length, price per period, what is included, auto-renews, how to cancel; links to Terms and Privacy) | Apple 3.1.2; Play Subscriptions policy | Paywall screen (RevenueCat paywall or own): grep price strings, `auto-renew`, terms/privacy links | Paywall file:line | Blocker (store rejection) if missing | engineer | Show all items on the paywall; free-trial screens state the post-trial price and date. |
| In-app cancellation path | Play Subscriptions policy ("easy-to-use, online method to cancel"); Apple 3.1.2 | Settings link to `https://apps.apple.com/account/subscriptions` / Play subscriptions deep link, or RevenueCat Customer Center | file:line | Required | engineer | Add "Manage subscription" link in settings. |
| Auto-renewal disclosure "clear and conspicuous", in visual proximity to the request for consent | CA BPC §17602(a)(1); NY GBL §527-a; ROSCA 15 U.S.C. 8403 | `pay.stripe` web checkout with `mode: 'subscription'` or recurring `price` | Checkout template + session create file:line | Required (Blocker if consumer subscriptions sold with no renewal terms shown) | engineer | Show price, period, renewal and cancel terms next to the subscribe button. |
| Express affirmative consent to the renewal terms | CA BPC §17602(a)(2) (as amended from 1 Jul 2025); ROSCA | Separate unticked checkbox or explicit button text | Template file:line | Required | engineer | Capture consent; store timestamp and the terms shown. |
| Acknowledgement email with terms + cancellation method | CA BPC §17602(a)(3) | `comm.email` + Stripe webhook `checkout.session.completed`/`customer.subscription.created` handler sends receipt | Handler file:line | Required | engineer | Send confirmation with terms and cancel link (Stripe receipts alone may not include cancel instructions). |
| Online cancellation in the same medium, no obstruction ("click to cancel"); limits on save offers | CA BPC §17602(c)–(d) (AB 2863); NY GBL §527-a; other states. FTC federal click-to-cancel rule vacated by 8th Cir. 8 Jul 2025; FTC ANPRM restarting negative-option rulemaking 11 Mar 2026 — confirm via source. ROSCA still enforced. | Account settings → cancel; Stripe Billing Customer Portal enabled | Route file:line or "not found" | Required | engineer | Enable Stripe Customer Portal cancellation or an in-app cancel button; at most one save offer before confirming. |
| Annual reminder and advance notice of price change / trial end | CA BPC §17602(b) (7–30 days before price change; annual reminder for annual plans), other states | Scheduled email job around renewals | Job file:line or "not detected" | Required (CA consumers) | engineer | Send renewal / trial-end / price-change emails via Stripe Billing settings or own job. |
| EU/UK 14-day right of withdrawal; information before contract | CRD 2011/83/EU Art. 6, 9; UK CCR 2013 regs 13, 29 | Checkout/ToS text mentions withdrawal; B2C answer | ToS + checkout file:line | Required (EU/UK B2C) | founder | State the 14-day right, model withdrawal form, and exceptions in ToS and checkout. |
| Digital-content/service waiver wording | CRD Art. 16(m) and Art. 14(3); UK CCR reg. 37 | Checkbox text like "I request immediate access and acknowledge I lose my right of withdrawal" before purchase; confirmation email repeats it | Checkout file:line | Required (else consumer can withdraw and get full refund after use) | engineer | Add the express-consent + acknowledgement checkbox; confirm on a durable medium (email). |
| Withdrawal function ("withdraw from contract here" button) for online contracts | CRD Art. 11a inserted by Directive 2023/2673; applies from 19 Jun 2026 | Account/settings page offers a withdrawal action during the withdrawal period | Route file:line or "not found" | Required (EU B2C via own web checkout; store purchases handled by the store) | engineer | Add a clearly labelled withdrawal function with confirmation receipt. |
| Price display incl. VAT and all mandatory charges; prior-lowest-price for discounts | Price Indication Dir. 98/6/EC Art. 6a (Omnibus 2019/2161, 30-day prior price); UK DMCCA 2024 drip-pricing rules | Pricing page templates: grep `excl. VAT`, strike-through prices | Template file:line | Required (B2C) | engineer | Show VAT-inclusive prices to consumers; when showing a reduction, show the lowest price in the prior 30 days. |
| EU VAT on B2C digital services | VAT Dir. Art. 58; non-Union OSS (no threshold for non-EU sellers) | `pay.stripe` direct sales to EU consumers; Stripe Tax config (`automatic_tax`) | Checkout code | Required (Stripe direct); Note when MoR (stores, Paddle, Lemon Squeezy) | founder | Register for non-Union/Union OSS, charge customer-country VAT, file quarterly. |
| UK VAT on B2C digital services | VATA 1994; no threshold for non-UK-established sellers | Same as above for UK customers | Checkout code | Required (Stripe direct, non-UK seller) | founder | Register with HMRC from first UK B2C sale; charge 20%. |
| Singapore GST on overseas digital services (OVR) | GST Act; register if global turnover > S$1M and B2C digital supplies to SG > S$100k | SG customers + `pay.stripe` | Answer + checkout | Required above threshold; else Note with threshold stated | founder | Register under OVR, charge 9% GST. |
| Israel VAT | VAT Law 5736-1975 (18% from 1 Jan 2025) | Israeli entity or Israeli customers | Answer | Required for Israeli entities; foreign sellers → Needs a lawyer | founder | Israeli entity: issue tax invoices/receipts per ITA rules (allocation numbers for large B2B invoices). |
| Invoices/receipts with legally required fields | EU VAT Dir. Art. 226; UK VAT regs; local rules | Stripe invoice settings (tax ID, address) | Config | Recommended | founder | Enable Stripe invoices with seller tax IDs and address. |
| Refund policy in ToS consistent with store and law | Contracts; CRD; Apple/Google refund handled by stores | `legal.terms_page` grep `refund` | ToS text | Required (see contracts-docs.md) | founder | State refund terms; do not promise refunds you cannot issue for store purchases. |
| Payment providers listed as processors / independent controllers | GDPR Art. 13, 28; CCPA | Notice names Stripe/RevenueCat/Paddle; DPA accepted (Stripe DPA incorporated in Stripe Services Agreement; RevenueCat DPA online) | Notice text | Required | founder | List payment vendors in the sub-processor page (see privacy-gdpr-uk.md). |
| Chargeback/dispute handling and evidence | Card-network rules; Stripe dispute flow | Webhook handles `charge.dispute.created`; logs proof of consent/usage | Handler file:line | Recommended | engineer | Handle disputes, keep consent and usage evidence. |
| Webhook authenticity | Stripe docs (signature verification); security | `stripe.Webhook.construct_event` / `webhook.ConstructEvent` with signing secret | Handler file:line | Required (see security-baseline.md) | engineer | Verify signatures; reject unsigned events; idempotency keys. |
| Children purchasing | Apple/Google Ask to Buy; COPPA | Answer on minors | Per minors.md | Required (see minors.md) | founder | Apply minors.md fixes. |
| Strong Customer Authentication (3-D Secure) for EEA/UK card payments | PSD2 RTS on SCA (Reg. (EU) 2018/389); UK FCA SCA-RTS | Stripe Payment Intents/Checkout (handles SCA) vs legacy Charges API (`stripe.Charge.create`) | API call file:line | Required (EEA/UK cards) | engineer | Use Payment Intents / Checkout; handle `requires_action`. |
| Free trial terms: length, post-trial price, renewal date, how to cancel before charge | Apple 3.1.2; Play Subscriptions policy; CA BPC §17602(a)(1) | Trial paywall copy | Paywall file:line | Required | engineer | State trial end date and price; send trial-ending reminder. |
| Store refund requests routed to Apple/Google | Apple/Google terms (store is seller) | Support page tells store users to request refunds from the store | Page text | Recommended | founder | Link to reportaproblem.apple.com / Play refund help. |
| Subscription value: ongoing value, no taking away paid features | Apple 3.1.2(a) | Paywall + feature gates | Gate file:line | Required (store review) | founder | Make subscriptions deliver ongoing value; do not paywall previously-free core features abruptly. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2022-05-28 | EU Omnibus price-reduction (30-day prior price) rules | in force |
| 2025-03-31 | PCI DSS v4.0.x future-dated requirements mandatory | in force |
| 2025-04-30 | US storefront: external purchase links permitted (Epic v. Apple injunction; commission rate on remand) — confirm via source | in force |
| 2025-07-01 | California ARL amendments (AB 2863) | in force |
| 2025-07-08 | FTC Negative Option ("click to cancel") Rule vacated by 8th Circuit | vacated; ANPRM 2026-03-11 |
| 2026-06-19 | EU withdrawal function (CRD Art. 11a) | in force |

## Needs a lawyer
- Whether external purchase links or alternative billing can be used in each storefront and what commission currently applies.
- Tax registration for a foreign seller with Israeli B2C customers, and any US state sales tax nexus for digital subscriptions.
- Consumer subscription terms (auto-renewal, trials, cancellation) against each target US state's ARL.
- Refund and withdrawal exceptions for mixed digital content + service products.
