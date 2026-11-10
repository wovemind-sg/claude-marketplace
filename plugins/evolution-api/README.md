# evolution-api

Skill teach Claude full [Evolution API](https://docs.evolutionfoundation.com.br/en/evolution-api) surface (spec v2.3.7) — write correct WhatsApp client code: endpoint paths, request/response schemas, auth, webhook events, error flows.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install evolution-api@wovemind
```

## Requirements

- An Evolution API server (version 2) that you run yourself, reachable from wherever your client code runs.
- An API key for that server: the global key to create instances, or an instance key to use one connected number.
- A WhatsApp number connected to an instance on that server before any message can be sent.

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

The plugin itself reads no environment variables. These are the names the generated code uses, so set them wherever that code runs.

## Example

Ask Claude:

> "Send 'Your order has shipped' to +65 9123 4567 from my instance `shop-bot`."

Claude first checks that the instance is connected, then sends the text with a short delay, using the base URL and key from your environment:

```bash
curl -s "$EVOLUTION_BASE_URL/instance/connectionState/shop-bot" -H "apikey: $EVOLUTION_API_KEY"
# {"instance":{"state":"open"}}

curl -s -X POST "$EVOLUTION_BASE_URL/message/sendText/shop-bot" \
  -H "apikey: $EVOLUTION_API_KEY" -H "Content-Type: application/json" \
  -d '{"number":"6591234567","textMessage":{"text":"Your order has shipped"},"delay":3000}'
```

The response contains a message `key`. Claude keeps it so the same message can later be quoted, reacted to or marked as read.

## Pairs with

`whatsapp-safety` (same marketplace) — anti-ban guide skill defer to for pacing, warm-up, broadcast rules.