---
name: evolution-api
description: Complete endpoint reference for Evolution API (v2.3.7) — the self-hosted WhatsApp integration REST API. Use this whenever writing client code that talks to an Evolution API server; sending WhatsApp text, media, buttons, lists, polls, locations, contacts, or reactions; creating or connecting WhatsApp instances (QR code / pairing); configuring webhooks or reacting to webhook events; managing groups, chats, contacts, labels, profiles, or Business templates. Trigger even when the user just says "send a WhatsApp message", "build a WhatsApp bot", or "hook up WhatsApp notifications" without naming Evolution API, if their stack uses an Evolution server.
---
# Evolution API Client Reference

Evolution API: self-hosted REST API, sits front WhatsApp. One server, many *instances*, each instance = one connected WhatsApp number. Providers: `WHATSAPP-BAILEYS` (unofficial WhatsApp Web session — common case) and `WHATSAPP-BUSINESS` (official Meta Cloud API). Docs: https://docs.evolutionfoundation.com.br/en/evolution-api (spec v2.3.7).

## Basics every call shares

- **Base URL**: user's server (e.g. `https://your-instance.com`; local default `http://localhost:8080`). Keep in env var, never hardcode.
- **Auth**: header `apikey: <key>` every request. Two key scopes: **global** key (server env `AUTHENTICATION_API_KEY`) works everywhere, required for `/instance/create` and `/instance/fetchInstances`; **instance** key (`hash` from create-instance, or `token` you set) works only that instance's endpoints. 401 = missing/bad key.
- **Instance scoping**: every endpoint except create/fetchInstances takes `{instanceName}` final path segment.
- **Numbers**: country code + number, digits only (`5511999999999`). Groups: JIDs end `@g.us`; individual: JIDs end `@s.whatsapp.net`.
- `Content-Type: application/json` everywhere except Send Media (multipart/form-data).

## Error handling

All errors, one envelope:

```json
{ "success": false,
  "error": { "code": "NOT_FOUND", "message": "Instance not found" },
  "meta": { "timestamp": "...", "path": "/message/sendText/{instanceName}", "method": "POST" } }
```

| HTTP | code | Meaning / client action |
|---|---|---|
| 400 | `BAD_REQUEST` | Invalid body — check required fields/shapes, don't retry unchanged |
| 401 | `UNAUTHORIZED` | Bad/missing `apikey` — check key scope (global vs instance) |
| 403 | `FORBIDDEN` | Key valid, not allowed this action |
| 404 | `NOT_FOUND` | Usually instance name wrong or instance deleted |
| 500 | `INTERNAL_SERVER_ERROR` | Server-side, safe retry w/ backoff |

Beyond HTTP errors, common runtime failure: **instance not connected**. Check `GET /instance/connectionState/{instanceName}` returns `state: "open"` before sending, subscribe `CONNECTION_UPDATE` webhook events for drops.

## Quick start: send a text

```bash
# 1. verify connection
curl -s "$BASE/instance/connectionState/$INSTANCE" -H "apikey: $APIKEY"
# → {"instance":{"state":"open"}}

# 2. send
curl -s -X POST "$BASE/message/sendText/$INSTANCE" \
  -H "apikey: $APIKEY" -H "Content-Type: application/json" \
  -d '{"number":"5511999999999","textMessage":{"text":"Hello"},"delay":3000}'
# → {"key":{...},"message":{...},"status":"PENDING"}
```

Save returned `key` — identifies message for reactions, quoting, mark-as-read. (Some v2 builds use flat `"text"` instead `textMessage.text` — see references/messages.md.)

## Where to look next

Read only reference file matching task:

| Task | File |
|---|---|
| Send anything (text, media, buttons, list, template, location, contact, poll, reaction), mark read | `references/messages.md` |
| Create/connect/QR/delete instances, settings (auto-read, reject calls…), presence, proxy | `references/instances.md` |
| Webhook setup, full event list, `webhook_by_events` URL routing, consumer patterns | `references/webhooks-events.md` |
| Groups: create, info, participants, add/remove/promote | `references/groups.md` |
| Search chats/contacts/messages, archive, verify numbers on WhatsApp, labels, calls | `references/chats-contacts.md` |
| Own profile, Business templates (Cloud API), catalog | `references/profile-business.md` |

## Gotchas

- **Ban risk real.** Baileys instances unofficial sessions; bulk/spammy sends get numbers permanently banned. If `whatsapp-safety` skill installed, apply before writing any send/group/broadcast code. Min hygiene regardless: use `delay`, pace between recipients, verify recipients `POST /chat/whatsappNumbers/{instanceName}` first, only message people who expect it.
- Success shapes inconsistent across endpoint families: sends return `{key,message,status}`, most management endpoints `{success,message}`, restart returns `{error,message}`. Don't assume one shape.
- QR code from create/connect rotates (`count` increments); re-fetch on `QRCODE_UPDATED` events, don't cache.
- `DELETE /template/delete` takes JSON body — some HTTP clients need explicit support DELETE-with-body.
- Find endpoints (`findChats`/`findContacts`/`findMessages`) POST w/ Prisma-style `where/take/skip/orderBy` — not GET w/ query params.
- Spec examples on doc pages embed full OpenAPI YAML; site's `openapi.json` is placeholder ("Plant Store") — don't fetch expecting real spec. Own server serves true spec at `/docs`.