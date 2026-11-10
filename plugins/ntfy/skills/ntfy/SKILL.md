---
name: ntfy
description: >
  Send push notifications to the user's phone/desktop via ntfy (https://ntfy.sh
  or the server set in the plugin's settings). Use this whenever the user asks to be
  notified, pinged, alerted, or sent a push notification about something —
  e.g. "let me know when this finishes", "ping me if it fails", "notify me",
  "send me a push notification", "text me when done" — even if they don't say
  "ntfy" explicitly. Covers publishing messages with titles/priority/tags,
  action buttons, attachments, scheduled/delayed delivery, and markdown
  formatting over ntfy's HTTP API.
---

# ntfy push notifications

ntfy is an HTTP pub-sub notification service: POST/PUT a message to
`<server>/<topic>` and every subscriber to that topic (phone app, desktop,
browser) gets a push notification. No accounts, no SDKs — plain HTTP.

## Setup

- **Server**: `${user_config.server}` — the plugin's `server` setting
  (`/plugin configure ntfy@wovemind`). If that value still contains the text
  `user_config`, the setting was never saved: use `https://ntfy.sh`.
  Wherever this file or `references/options.md` shows the server URL or
  `<server>`, use that value.
- **Auth token** (optional): if `~/.ntfy` exists, it holds one line, a
  `tk_...` access token for a server that requires auth. Public ntfy.sh needs
  none.
- **Topic**: `${user_config.topic}` — the plugin's `topic` setting. If that
  value still contains the text `user_config`, the setting was never saved:
  use `claude`. A topic is the channel name notifications
  go to (anyone subscribed to that topic on this server gets the message —
  treat it like a password). Use this default topic unless the user names a
  different topic for a specific purpose (e.g. `ci-alerts`). Wherever this
  file or `references/options.md` shows `<topic>`, use
  the topic chosen here.

The simplest way to send is the `ntfy-send` script this plugin puts on the
`PATH` (it adds the token header itself when `~/.ntfy` exists):

```bash
ntfy-send -s ${user_config.server} -o <topic> "message" [-t title] [-p priority] [-T tags]
```

For raw `curl` (needed for the options below), add the auth header only when
`~/.ntfy` exists, and drop it from the examples otherwise. Read the token at
call time — never print it, log it, or paste it into a file/command where
it'd be echoed back to the user:

```bash
curl -H "Authorization: Bearer $(cat ~/.ntfy)" -d "message" ${user_config.server}/<topic>
```

## Sending a basic notification

```bash
curl -H "Authorization: Bearer $(cat ~/.ntfy)" \
     -d "Backup finished successfully" \
     ${user_config.server}/<topic>
```

`-d` is the message body. That alone is enough for a working notification —
everything below is optional embellishment.

## Adding title, priority, tags

Pass extra fields as headers. Common ones:

| Field | Header | Values |
|---|---|---|
| Title | `-H "Title: ..."` | any string |
| Priority | `-H "Priority: ..."` | `1`/`min`, `2`/`low`, `3`/`default`, `4`/`high`, `5`/`urgent` |
| Tags (emoji/labels) | `-H "Tags: ..."` | comma-separated, e.g. `warning,skull` |
| Markdown | `-H "Markdown: yes"` | enables bold/italic/links/code in the message |
| Click action | `-H "Click: <url>"` | URL opened when notification is tapped |

Example — a failure alert:

```bash
curl -H "Authorization: Bearer $(cat ~/.ntfy)" \
     -H "Title: Build failed" \
     -H "Priority: high" \
     -H "Tags: warning,rotating_light" \
     -d "CI pipeline failed on main branch" \
     ${user_config.server}/<topic>
```

Reach for **high/urgent priority + a tag** when the message is actionable or
time-sensitive (failures, approvals needed); leave priority at default for
routine "job finished" pings — it's the difference between a notification
that interrupts and one that just logs.

For the full header reference (action buttons, attachments, scheduled
delivery, JSON publishing, updating/deleting messages, message size limits),
read `references/options.md` before reaching for anything beyond
title/priority/tags/markdown/click.

## Verifying delivery

`curl` prints a JSON response line on success (contains an `"id"` field) —
check it rather than assuming the notification landed, since a bad topic
name or expired token still returns an HTTP response, just not a pushed
notification. If the response is an error body instead (look for `"code"`
and `"error"`), read it: expired/missing token and unauthorized-topic errors
both come back as normal HTTP responses, not curl failures, so a non-error
exit code from curl does *not* mean the notification succeeded.
