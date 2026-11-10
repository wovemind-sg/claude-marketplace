# Profile, Templates, Business Catalog

## Profile (own account)

`POST /chat/updateProfileName/{instanceName}` — body `{ "name": "..." }` (required)

`POST /chat/updateProfilePicture/{instanceName}` — picture upload (image in body; spec docs no JSON schema — send image, verify shape vs instance's `/docs`)

`POST /chat/updateProfileStatus/{instanceName}` — body `{ "status": "..." }` (required) — "About" text

All return `{ "success": true, "message": "..." }`.

## Templates (WhatsApp Business / Cloud API instances only)

Templates apply only `WHATSAPP-BUSINESS` (Meta Cloud API) instances; Baileys skip. Need Meta approval before send.

### Create Template

`POST /template/create/{instanceName}`

- `name` (required, string)
- `category` (required, string) — enum: `MARKETING`, `UTILITY`, `AUTHENTICATION`
- `language` (required, string) — e.g. `en_US`, `pt_BR`
- `components` (required, array of objects) — Meta template components (HEADER/BODY/FOOTER/BUTTONS)

Success `200`: `{ "success": true, "template": { ... } }`

### Find Templates

`GET /template/find/{instanceName}` — all templates for instance; empty body if none.

### Edit Template

`POST /template/edit/{instanceName}`

- `name` (required, string)
- `components` (array of objects)

### Delete Template

`DELETE /template/delete/{instanceName}` — body `{ "name": "..." }` (required; note: DELETE with JSON body)

## Business Catalog

`POST /business/getCatalog/{instanceName}` — body `{ "number": "..." }` (required) → `{ "success": true, "catalog": { ... } }`

`POST /business/getCollections/{instanceName}` — body `{ "number": "..." }` (required) → `{ "success": true, "collections": [ ... ] }`

`number` = business account whose catalog fetched.