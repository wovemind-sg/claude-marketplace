# evolution-api

Skill teach Claude full [Evolution API](https://docs.evolutionfoundation.com.br/en/evolution-api) surface (spec v2.3.7) — write correct WhatsApp client code: endpoint paths, request/response schemas, auth, webhook events, error flows.

## What's inside

- `skills/evolution-api/SKILL.md` — auth model (global vs instance `apikey`), standard error envelope, quick-start, gotchas, decision table point to right reference.
- `references/messages.md` — all send endpoints (text, media, buttons, list, template, location, contact, poll, reaction) + mark-as-read.
- `references/instances.md` — instance lifecycle (create → connect/QR → open → logout/delete), settings, presence, proxy.
- `references/webhooks-events.md` — webhook/WebSocket config, full event table, `webhook_by_events` routing, consumer patterns.
- `references/groups.md` — create groups, info, participants, add/remove/promote/demote.
- `references/chats-contacts.md` — find chats/contacts/messages, archive, number verification, labels, calls.
- `references/profile-business.md` — profile updates, Business templates, catalog.

## Usage

Install, ask for Evolution API work — skill trigger auto:

> "Send a WhatsApp message to +55 11 99999-9999 via my Evolution server"
> "Build a webhook receiver that auto-replies to incoming WhatsApp messages"
> "Create a new WhatsApp instance and show me the QR code"

## Required environment

Client code skill produce expect:

| Variable | Meaning |
|---|---|
| `EVOLUTION_BASE_URL` | Your Evolution API server URL |
| `EVOLUTION_API_KEY` | Global or instance `apikey` |

## Pairs with

`whatsapp-safety` (same marketplace) — anti-ban guide skill defer to for pacing, warm-up, broadcast rules.