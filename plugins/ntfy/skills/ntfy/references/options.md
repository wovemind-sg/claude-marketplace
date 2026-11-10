# ntfy publish options — full reference

All of these work as `-H "Header: value"` on the base `curl -H "Authorization:
Bearer $(cat ~/.ntfy)" ... <server>/<topic>` call
from SKILL.md, where `<server>` is the server URL SKILL.md resolved and the
`Authorization` header is sent only when `~/.ntfy` exists. Header name and its short alias are both valid; use whichever
reads clearer.

| Feature | Header | Alias | Example |
|---|---|---|---|
| Title | `X-Title` | `Title`, `t` | `Title: My Alert` |
| Priority | `X-Priority` | `Priority`, `p` | `1`-`5` or `min`/`low`/`default`/`high`/`urgent` |
| Tags | `X-Tags` | `Tags`, `ta` | `Tags: warning,skull` |
| Click action | `X-Click` | `Click` | `Click: https://example.com` |
| Icon | `X-Icon` | `Icon` | `Icon: https://example.com/icon.png` |
| Attach (external URL) | `X-Attach` | `Attach`, `a` | `Attach: https://example.com/file.apk` |
| Filename | `X-Filename` | `Filename`, `f` | `Filename: document.pdf` |
| Delay | `X-Delay` | `Delay`, `At`, `In` | `In: 30m` or `At: tomorrow, 10am` |
| Email forward | `Email` | — | `Email: user@example.com` |
| Markdown | `X-Markdown` | `Markdown`, `md` | `Markdown: yes` |
| Cache | `X-Cache` | `Cache` | `Cache: no` — don't store/replay on resubscribe |
| Message ID (for update/delete) | `X-Message-ID` | — | any unique string you choose |

## Action buttons

Up to 3 per notification, via `X-Actions` (or `Actions`), semicolon-separated:

```
<action>, <label>, <url>[, param=value...]
```

**View** (opens a URL when tapped):
```bash
curl -H "Authorization: Bearer $(cat ~/.ntfy)" \
     -H "Actions: view, Open dashboard, https://example.com" \
     -d "Deploy complete" <server>/<topic>
```

**HTTP** (fires a request when tapped — e.g. an approve/rollback button):
```
http, Rollback, https://api.example.com/rollback, method=POST, headers.Authorization=Bearer xyz, body={"env":"prod"}
```

**Copy to clipboard**: `copy, Copy code, 123456`

Append `clear=true` to any action to dismiss the notification once tapped.

## Attachments

**External URL** (no upload, just a link ntfy fetches):
```bash
curl -d "" -H "Attach: https://example.com/report.pdf" <server>/<topic>
```

**Local file upload** (PUT, not POST) — server stores it, capped at 15 MB,
expires in 3 hours on ntfy.sh (self-hosted limits may differ):
```bash
curl -T report.pdf -H "Authorization: Bearer $(cat ~/.ntfy)" \
     -H "Filename: report.pdf" <server>/<topic>
```

## Scheduled / delayed delivery

`X-Delay` (alias `At`/`In`) accepts durations or natural language, 10s to 3
days out:

```bash
curl -H "Authorization: Bearer $(cat ~/.ntfy)" -H "In: 30m" \
     -d "Reminder: stand-up" <server>/<topic>
```

## JSON publishing

Useful when setting many fields at once, or building the payload
programmatically instead of stacking headers:

```bash
curl -X POST <server> \
     -H "Authorization: Bearer $(cat ~/.ntfy)" \
     -H "Content-Type: application/json" \
     -d '{
       "topic": "<topic>",
       "title": "Alert",
       "message": "Something happened",
       "priority": 5,
       "tags": ["warning"],
       "actions": [{"action":"view","label":"Open","url":"https://example.com"}]
     }'
```

Note the topic moves *into* the JSON body here — the URL is just the bare
server root, not `/<topic>`.

## Updating / deleting a published message

Publish again with the same `X-Message-ID` to replace it. Delete with:

```bash
curl -X DELETE <server>/<topic>/<message-id>
```

Clear every message on a topic: `curl -X DELETE <server>/<topic>`

## Limits worth knowing before something silently fails

- Message body: 4,096 bytes max (non-UTF-8 content gets treated as an
  attachment instead of failing outright)
- Attachments: 15 MB per file (ntfy.sh default; self-hosted may be configured
  differently)
- Delay range: 10 seconds to 3 days
- Actions: max 3 per notification
- Topic names: letters, numbers, underscores, dashes; 64 chars max
