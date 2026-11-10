---
name: whatsapp-safety
description: Guides safe interaction with WhatsApp through the Evolution API so the connected number does not get flagged, banned, restricted, or shadow-limited. Use this whenever you are about to send WhatsApp messages, create or manage groups, add participants, broadcast, run outreach to new numbers, react to webhook events, or configure an Evolution API instance for messaging — even if the user only says "send a WhatsApp message", "message this contact", "add these people to a group", or "notify customers on WhatsApp" without mentioning bans or safety. Apply it before writing any code that calls Evolution API send/group/broadcast endpoints.
---
# WhatsApp Safety via Evolution API

WhatsApp hunt down automation look non-human. Evolution API run **unofficial** WhatsApp Web session — no official protection, connected number carry all risk. Ban usually **permanent for that number**, can happen minutes after first bad batch. Job: make automated behavior look like careful human, fail safe when signals say stop.

Skill big guide. Not need every section every task — read **Decision guide** below, load only reference files match what user doing.

## First: assess risk tier

Before write send code, classify task. Risk rise sharp moving down:

| Tier | Activity | Ban risk |
|------|----------|----------|
| **Low** | Reply to people who message first (webhook-driven), send to own number, notify handful saved contacts opted in | Low |
| **Medium** | Proactive messages to existing opted-in contacts, small managed groups, transactional/customer messages within 24h reply window | Moderate |
| **High** | First-contact messages to numbers never messaged you, add strangers to groups, any broadcast, identical message to many recipients | High — this get numbers banned |

If task High tier, say plain, steer toward safest form still meet goal (see `references/outreach-and-broadcast.md`). Don't silently run risky cold outreach.

## Non-negotiable foundations

Apply to **every** WhatsApp task regardless tier. Explain *why* to user when relevant — help them judge own use case.

1. **Warm up new numbers.** Fresh number blast messages immediate = #1 ban trigger. New numbers need days gentle, low-volume, human-paced use before automation volume. See `references/account-warmup.md`.
2. **Never send identical text at volume.** Duplicate message bodies across recipients = bulk-spam fingerprint. Spin every message (see `references/message-content.md`).
3. **Pace like human.** No burst loops. Randomized delays, typing presence, working hours only. See `references/rate-limiting.md`.
4. **Respect consent and blocks.** Only message people expect hear from you. High block/report rate = strongest ban signal WhatsApp got. See `references/outreach-and-broadcast.md`.
5. **Watch connection health.** Frequent disconnects, re-pairing, multi-device conflicts look suspicious, precede bans. See `references/evolution-api.md`.

## Decision guide — what to read next

- **Setting up new instance / number, or number < 2 weeks old** → `references/account-warmup.md`
- **Sending any proactive message** → `references/rate-limiting.md` + `references/message-content.md`
- **Cold outreach or broadcasting** → `references/outreach-and-broadcast.md` (and reconsider approach)
- **Creating groups or adding participants** → `references/groups.md`
- **Wiring up Evolution API calls, webhooks, presence, or checking numbers exist** → `references/evolution-api.md`
- **Ban/flag already happened or warning signs seen** → `references/incident-response.md`

## Core operating loop for any send task

When write code sending WhatsApp messages via Evolution API, structure this way — encode safety rules mechanically so not skipped:

1. **Validate target exists on WhatsApp** before send (`/chat/whatsappNumbers`). Sending to numbers not on WhatsApp = spam signal.
2. **Check within working hours** (recipient's local time, roughly 08:00–21:00). Queue for later otherwise.
3. **Set typing presence**, wait delay proportional to message length, then send. Instant sends robotic.
4. **Randomize inter-message delay** — never fixed sleep. See `references/rate-limiting.md` for concrete ranges.
5. **Vary message body** per recipient (`references/message-content.md`).
6. **Honor daily/hourly caps**, stop early if hit errors, blocks, delivery failures.
7. **Log every send** so volume and failure rate auditable.

`references/evolution-api.md` got copy-ready endpoint patterns for each step.

## Hard stops — when to refuse or halt

Stop, warn user (don't just power through) when:

- Task require cold-messaging list of numbers never opted in — this spam, likely get number banned. Offer compliant alternatives.
- Would send same message to large list, no personalization.
- Delivery failures, blocks, or Evolution API errors climbing during run — halt immediate, investigate (`references/incident-response.md`).
- Number brand new, user want immediate high volume — insist warm-up first.

Being honest about ban risk protects user's number, whole point of this skill.