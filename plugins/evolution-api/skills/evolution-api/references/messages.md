# Sending Messages

All endpoints: `POST`, JSON body (except Send Media — multipart), `apikey` header, path param `{instanceName}`.

Every send endpoint return same success shape (`200`, `201` for template):

```json
{ "key": { "remoteJid": "...", "fromMe": true, "id": "..." }, "message": { ... }, "status": "PENDING" }
```

Keep `key` — need later for reactions, quoting, mark-as-read. Errors use standard envelope (see SKILL.md).

`number` always recipient phone w/ country code, no `+` (e.g. `5511999999999`). Groups: use group JID (`...@g.us`) instead.

## Send Text Message

`POST /message/sendText/{instanceName}`

Request body (per 2.3.7 OpenAPI spec):

- `number` (required, string)
- `textMessage` (required, object)
  - `text` (required, string)
- `delay` (integer) — ms Evolution wait before delivering; use for human-like pacing
- `quoted` (object) — message key to reply to
- `linkPreview` (boolean)
- `mentioned` (array of string) — JIDs to @mention

> Version note: many Evolution API v2 deployments accept flat shape `{"number": "...", "text": "...", "delay": 3500}` instead of nested `textMessage.text`. If one shape return 400, try other; confirm against your instance's own `/docs`.

## Send Media Message

`POST /message/sendMedia/{instanceName}` — **multipart/form-data**, not JSON.

Form fields:

- `number` (required, string)
- `mediatype` (required, string) — enum: `image`, `video`, `audio`, `document`
- `media` (required, binary file)
- `caption` (string)
- `fileName` (string) — display name, mainly for documents

```bash
curl -s -X POST "$BASE/message/sendMedia/$INSTANCE" \
  -H "apikey: $APIKEY" \
  -F number=5511999999999 -F mediatype=image \
  -F media=@photo.jpg -F caption="Here you go"
```

## Send Buttons

`POST /message/sendButtons/{instanceName}` — interactive buttons.

- `number` (required, string)
- `text` (required, string) — main message body
- `footerText` (required, string)
- `buttons` (required, array of objects)
  - `buttonId` (string)
  - `buttonText` (object) — `{ "displayText": "..." }`

## Send List

`POST /message/sendList/{instanceName}` — interactive list menu.

- `number` (required, string)
- `title` (required, string)
- `description` (required, string)
- `buttonText` (required, string) — label of button that opens list
- `sections` (required, array of objects) — each `{ "title": "...", "rows": [{ "title", "description", "rowId" }] }`

## Send Template Message

`POST /message/sendTemplate/{instanceName}` — WhatsApp Business (Cloud API) approved templates only. Returns `201`.

- `number` (required, string)
- `textMessage` (required, object) — `{ "text": "..." }`
- `delay` (integer)

## Send Location

`POST /message/sendLocation/{instanceName}`

- `number` (required, string)
- `latitude` (required, number)
- `longitude` (required, number)
- `name` (string)
- `address` (string)

## Send Contact

`POST /message/sendContact/{instanceName}` — contact card(s).

- `number` (required, string)
- `contacts` (required, array of objects)
  - `displayName` (string)
  - `contacts` (array of objects) — phone entries, e.g. `{ "phoneNumber": "5511888888888" }`

## Send Poll

`POST /message/sendPoll/{instanceName}`

- `number` (required, string)
- `name` (required, string) — poll question
- `selectableCount` (required, integer) — how many options voter may pick
- `values` (required, array of string) — poll options

## Send Reaction

`POST /message/sendReaction/{instanceName}` — emoji reaction to existing message.

- `reactionKey` (required, object) — target message's `key` (`{ "remoteJid", "fromMe", "id" }`)
- `reactionMessage` (required, string) — emoji, e.g. `"👍"`; empty string removes reaction

## Mark Message as Read

`POST /chat/markMessageAsRead/{instanceName}`

- `readMessages` (required, array of objects) — message keys to mark read, each `{ "remoteJid", "fromMe", "id" }`

Success: `{ "success": true, "message": "Message marked as read successfully" }`