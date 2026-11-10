# Outreach, Consent & Broadcast

Highest-risk area. Cold outreach + broadcast to non-opt-in people = fastest route to permanent ban. Evolution API give no protection. Read before execute anything that message numbers proactive at scale.

## Consent rule

Only message people who **expect** hear from you. One of:

- They message you first (best — replies low risk).
- Explicit opt-in (signed up, gave number this purpose, ticked box).
- Genuine prior relationship + reason they'd welcome message.

Rest = cold outreach. WhatsApp not email — unsolicited messages get blocked/reported fast. Handful reports on young number = ban.

## Why block/report rate dominates

WhatsApp's most reliable ban signal: recipients **block or report** you. Pace perfect, spin content perfect — message unwanted, people block, number dies. Consent not compliance checkbox — primary technical defense. Lower block rate *is* safety strategy.

## Broadcasts — avoid trap

- **No one message body to big list.** Exact pattern detectors hunt.
- WhatsApp's own "Broadcast Lists" deliver only to people who saved *your* number — respect that spirit even automating.
- Reach many opted-in people → treat as **many individual, spun, paced 1:1 messages** (see `references/message-content.md` and `references/rate-limiting.md`), not broadcast. Segment list, spread over days.
- Prefer **groups or Channels** for genuine broadcast-style updates to people who chose join, over identical DMs.

## Validate numbers first

Before message list, check each number exist on WhatsApp (`/chat/whatsappNumbers`, see `references/evolution-api.md`). Send to dead/invalid numbers itself spam signal, wastes daily budget. Drop invalid ones.

## Safer alternatives to cold DM outreach

User want reach non-opt-in people → steer here instead of executing blast:

- **Official WhatsApp Business API** (Meta/Cloud API) w/ approved message templates — only sanctioned way message users proactive at scale. Unofficial automation (Evolution API) no such allowance.
- **Get opt-in first** via other channel (website, ad, existing contact), then message.
- **Inbound funnels** — "click to WhatsApp" link/QR so people initiate, flip every conversation into low-risk reply traffic.

## User insist cold outreach anyway

Be honest: likely get number banned, maybe fast. Proceed despite warning → minimize damage — tiny volumes, heavy spinning, real personalization, dead-slow pacing, opt-out every message, throwaway number they afford lose (not main one). Lead with recommendation not to, though.