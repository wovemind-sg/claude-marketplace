# Instances, Settings, Presence, Proxy

*Instance* = one connected WhatsApp number. Everything else scoped to instance via `{instanceName}` path param. Lifecycle: create → connect (scan QR / pairing code) → state `open` → use → logout/delete.

## Create Instance

`POST /instance/create` — only endpoint *not* scoped to instance. Needs **global** API key.

Request body:

- `instanceName` (required, string)
- `qrcode` (boolean) — return QR code immediately in response
- `integration` (string) — provider: `WHATSAPP-BAILEYS` (default, WhatsApp Web session), `WHATSAPP-BUSINESS` (Meta Cloud API), or Evolution provider
- `token` (string) — set specific instance API key; omitted → generated (returned as `hash`)
- `number` (string) — phone number for pairing-code connect
- `webhook` (object) — configure webhook at creation: `{ "enabled", "url", "events": [...] }`

Success `201`:

- `instance` — `{ instanceName, instanceId, integration, status: "connecting", webhookWaBusiness, accessTokenWaBusiness }`
- `hash` (string) — **instance API key; store it**
- `settings` — `{ rejectCall, msgCall, groupsIgnore, alwaysOnline, readMessages, readStatus, syncFullHistory, wavoipToken }`
- `qrcode` — `{ pairingCode, code, base64, count }` (`base64` = data-URI PNG, render/scan)
- plus event-channel blocks: `webhook`, `websocket`, `rabbitmq`, `nats`, `sqs`

## Fetch All Instances

`GET /instance/fetchInstances` — global key. Returns array of `{ instance: { instanceName, status, qrcode, connectionStatus } }`.

## Connect Instance

`GET /instance/connect/{instanceName}` — start WhatsApp connection.

Success `200`: `{ "pairingCode": "...", "code": "2@...", "base64": "data:image/png;base64,...", "count": 1 }`

Render `base64` as QR to scan, or show `pairingCode` for phone-number pairing. QR expires + rotates — poll connection state after.

## Get Connection State

`GET /instance/connectionState/{instanceName}`

Success `200`: `{ "instance": { "instanceName": "...", "state": "open" | "close" | "connecting" } }`

**Check `state == "open"` before sending anything** — sends against closed instance fail.

## Restart Instance

`POST /instance/restart/{instanceName}` — success `200` returns `{ "error": bool, "message": "..." }` (diff shape, note).

## Logout Instance

`DELETE /instance/logout/{instanceName}` — disconnect WhatsApp session, keep instance. `{ "success": true, "message": "..." }`

## Delete Instance

`DELETE /instance/delete/{instanceName}` — remove instance entirely. Logout first if connected. `{ "success": true, "message": "..." }`

## Settings

`GET /settings/find/{instanceName}` / `POST /settings/set/{instanceName}` (set returns `201`)

All fields optional booleans/strings:

- `rejectCall` (boolean) + `msgCall` (string) — auto-reject calls, optional text auto-reply to caller
- `groupsIgnore` (boolean) — ignore all group messages/events
- `alwaysOnline` (boolean) — keep presence "online"
- `readMessages` (boolean) — auto-mark incoming messages read (blue ticks)
- `readStatus` (boolean) — auto-view contacts' status updates
- `syncFullHistory` (boolean) — sync full chat history on connect
- `wavoipToken` (string) — WAVoip integration token

## Set Presence

`POST /instance/setPresence/{instanceName}`

- `presence` (required, string) — enum: `available`, `unavailable`, `composing`, `recording`

Use `composing` briefly before send, mimics typing. `{ "success": true, ... }`

## Proxy

`POST /proxy/set/{instanceName}` / `GET /proxy/find/{instanceName}` (find returns `null` when unset)

- `enabled` (boolean)
- `proxyHost`, `proxyPort` (strings)
- `proxyProtocol` (string) — enum: `http`, `https`, `socks4`, `socks5`
- `proxyUsername`, `proxyPassword` (strings)