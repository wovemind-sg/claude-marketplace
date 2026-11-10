# Webhooks & Events

Two delivery channels per instance: HTTP webhook and WebSocket (also RabbitMQ / SQS / NATS / Pusher via env config). Webhook usual choice for bots: Evolution POSTs event JSON to your URL.

## Set Webhook

`POST /webhook/set/{instanceName}`

- `enabled` (boolean) — `false` stops deliveries
- `url` (string) — your HTTPS endpoint
- `events` (array of string) — event names to subscribe (see table); omit unneeded ones
- `headers` (object) — extra headers Evolution sends per delivery (use for own auth, e.g. shared secret)
- `base64` (boolean) — include media as base64 in message events

Success `200`: `{ "success": true, "message": "..." }`

Webhook also settable at instance creation (`webhook` block in `POST /instance/create`) or globally via env (`WEBHOOK_GLOBAL_URL`, `WEBHOOK_GLOBAL_ENABLED`, per-event `WEBHOOK_EVENTS_*` vars).

## Get Webhook

`GET /webhook/find/{instanceName}` → `{ "enabled", "url", "webhookByEvents", "events": [...] }`, or `null` if never configured.

## Set WebSocket

`POST /websocket/set/{instanceName}` — body `{ "enabled": bool, "events": [...] }`. Success `201`, empty body.

## Supported events

| Event | Fires when |
|---|---|
| `APPLICATION_STARTUP` | Evolution app starts |
| `QRCODE_UPDATED` | New QR code generated (payload has base64) — listen during connect flow |
| `CONNECTION_UPDATE` | WhatsApp connection status changes — watch for unexpected `close` |
| `MESSAGES_SET` | Initial full message history load (fires once) |
| `MESSAGES_UPSERT` | **Message received** — main event for bots/auto-reply |
| `MESSAGES_UPDATE` | Message updated (delivered/read acks, edits) |
| `MESSAGES_DELETE` | Message deleted |
| `SEND_MESSAGE` | Message sent from this instance |
| `CONTACTS_SET` | Initial contact load (once) |
| `CONTACTS_UPSERT` | Contact reload w/ extra info (once) |
| `CONTACTS_UPDATE` | Contact updated |
| `PRESENCE_UPDATE` | Contact presence: `unavailable`, `available`, `composing`, `recording`, `paused` |
| `CHATS_SET` | Initial chat list load |
| `CHATS_UPSERT` | New chat info |
| `CHATS_UPDATE` | Chat updated |
| `CHATS_DELETE` | Chat deleted |
| `GROUPS_UPSERT` | Group created |
| `GROUPS_UPDATE` | Group info changed |
| `GROUP_PARTICIPANTS_UPDATE` | Participant add/remove/promote/demote |
| `NEW_TOKEN` | Instance JWT rotated |
| `TYPEBOT_START`, `TYPEBOT_CHANGE_STATUS` | Typebot integration events |
| `ERRORS` | Error events (enable via `WEBHOOK_EVENTS_ERRORS` + `WEBHOOK_EVENTS_ERRORS_WEBHOOK`) |

## webhook_by_events routing

With `webhook_by_events: true` (or `WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=true`), Evolution appends kebab-case event name to your URL per event: `https://host/webhook/` → `https://host/webhook/messages-upsert`, `/connection-update`, `/qrcode-updated`, … (`NEW_TOKEN` → `/new-jwt`). Useful for routing per-event handlers without inspecting payloads.

## Consumer guidance

- Respond `2xx` fast; do real work async. Slow/failing endpoints drop events.
- `MESSAGES_UPSERT` payloads include message `key` — check `key.fromMe` to avoid replying to own messages (echo loops).
- Payload set/upsert events (`*_SET`, `CONTACTS_UPSERT`) fire once at sync, can be huge — only subscribe if needed.
- Validate deliveries using custom `headers` configured; webhook has no built-in signature.