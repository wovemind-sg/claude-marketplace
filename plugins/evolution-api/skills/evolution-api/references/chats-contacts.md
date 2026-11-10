# Chats, Contacts, Labels, Calls

## Find endpoints (shared query shape)

`POST /chat/findChats/{instanceName}`
`POST /chat/findContacts/{instanceName}`
`POST /chat/findMessages/{instanceName}`

All three take Prisma-style query body — fields optional, empty body `{}` return all paginated:

- `where` (object) — field filters, e.g. `{ "remoteJid": "5511999999999@s.whatsapp.net" }` for messages, `{ "id": "..." }` for contacts
- `take` (integer) — page size
- `skip` (integer) — offset
- `orderBy` (object) — e.g. `{ "messageTimestamp": "desc" }`

Responses:

- **findChats** `200`: array of chat objects
- **findContacts** `200`: array of `{ id, pushName, number, profilePictureUrl }`
- **findMessages** `200`:

```json
{ "messages": { "total": 0, "pages": 0, "currentPage": 1,
    "records": [ { "id", "key", "message", "messageType", "fromMe", "timestamp" } ] } }
```

## Archive Chat

`POST /chat/archiveChat/{instanceName}`

- `number` (required, string)
- `archive` (required, boolean) — `true` archive, `false` unarchive

## Check WhatsApp Numbers

`POST /chat/whatsappNumbers/{instanceName}` — verify numbers exist on WhatsApp **before** send; sending non-existent numbers = spam signal, waste quota.

- `numbers` (required, array of string)

Success `200`: `{ "numbers": [ { "number": "...", "exists": true } ] }`

## Labels

`GET /label/findLabels/{instanceName}` → array of `{ id, name, color }` (empty array if none).

`POST /label/handleLabel/{instanceName}` — attach/detach label:

- `name` (required, string) — label name
- `type` (required, string) — enum: `chat`, `message`
- `id` (required, string) — chat JID or message id to label
- `action` (string) — enum: `add`, `remove`

## Offer Call

`POST /call/offer/{instanceName}` — start call.

- `number` (required, string)
- `offer` (required, object) — call params (e.g. `{ "isVideo": false, "callDuration": 30 }`)

Success `200`: `{ "success": true, "message": "..." }`