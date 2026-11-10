# Groups

Group identifier = **group JID** — looks like `120363012345678901@g.us`. Get from Create Group's response or webhook events (`GROUPS_UPSERT`). Participant identifiers = phone numbers / user JIDs.

> Adding people who didn't ask = top ban trigger. If whatsapp-safety skill installed, apply before writing group-add code.

## Create Group

`POST /group/create/{instanceName}`

- `subject` (required, string) — group name
- `participants` (required, array of string) — phone numbers with country code
- `description` (string)

Success `200`: `{ "success": true, "group": { ...includes the group JID... } }`

## Get Group Info

`GET /group/findGroupInfos/{instanceName}?groupJid=<jid>`

- `groupJid` (required, query) — WhatsApp group JID

Success `200`: `{ "success": true, "group": { ... } }`

## Get Participants

`GET /group/participants/{instanceName}?groupJid=<jid>`

- `groupJid` (required, query)

Success `200`: `{ "success": true, "participants": [ ... ] }`

## Update Participant

`POST /group/updateParticipant/{instanceName}` — add, remove, promote (to admin), demote.

- `groupJid` (required, string)
- `action` (required, string) — enum: `add`, `remove`, `promote`, `demote`
- `participants` (required, array of string)

Success `200`: `{ "success": true, "message": "..." }`

Adding can partially fail per participant (privacy settings block add); inspect response, don't assume all joined.
