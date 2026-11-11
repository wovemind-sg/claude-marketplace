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
  `user_config` or is empty, the setting was never saved. Then check
  `[ -f ~/.ntfy ] && echo yes` (test only — never print the file):
  - `~/.ntfy` exists: do not send anything, since its token may belong to
    another server. Tell the user to run `/plugin configure ntfy@wovemind`
    and set `server` (to their own server, or to `https://ntfy.sh` if that is
    where their token belongs), then stop. When running unattended (called
    from another skill such as plan-tools `drain-issues` or compliance-audit
    `apply`), skip the notification and say so in the report instead of
    stopping the caller.
  - no `~/.ntfy`: use `https://ntfy.sh`.

  Wherever this file or `references/options.md` shows `<server>`, use the
  server chosen here.
- **Auth token** (optional): if `~/.ntfy` exists, it holds one line, a
  `tk_...` access token for a server that requires auth. Public ntfy.sh needs
  none.
- **Topic**: `${user_config.topic}` — the plugin's `topic` setting. If that
  value still contains the text `user_config` or is empty, the setting was
  never saved: use `claude`. A topic is the channel name notifications
  go to (anyone subscribed to that topic on this server gets the message —
  treat it like a password). Use this default topic unless the user names a
  different topic for a specific purpose (e.g. `ci-alerts`). Wherever this
  file or `references/options.md` shows `<topic>`, use
  the topic chosen here.

The simplest way to send is the `ntfy-send` script this plugin puts on the
`PATH` (it adds the token header itself when `~/.ntfy` exists):

```bash
ntfy-send -s <server> -o <topic> [-t title] [-p priority] [-T tags] -- "message"
```

`--` lets a message start with `-`. Single-quote any value with `$`, backticks or
`'` in it, since double quotes would run them as shell.

Use raw `curl` only for headers `ntfy-send` has no flag for (Markdown, Click,
and the options in `references/options.md`). Send the token the way
`ntfy-send` does: only when `~/.ntfy` exists, and through stdin, so it never
shows up in the process list or the output:

```bash
{ [ -f ~/.ntfy ] && printf 'Authorization: Bearer %s\n' "$(cat ~/.ntfy)"; } |
  curl -H @- -H "Markdown: yes" --data-raw "**message**" <server>/<topic>
```

`--data-raw` is the message body (unlike `-d`, it never reads a file when the
message starts with `@`).

## Sending a basic notification

```bash
ntfy-send -s <server> -o <topic> -- "Backup finished successfully"
```

That alone is enough for a working notification — everything below is
optional embellishment.

## Adding title, priority, tags

`ntfy-send` takes title (`-t`), priority (`-p`) and tags (`-T`); the rest
are headers on the raw `curl` call above. Common ones:

| Field | Header | Values |
|---|---|---|
| Title | `-H "Title: ..."` | any string |
| Priority | `-H "Priority: ..."` | `1`/`min`, `2`/`low`, `3`/`default`, `4`/`high`, `5`/`urgent` |
| Tags (emoji/labels) | `-H "Tags: ..."` | comma-separated, e.g. `warning,skull` |
| Markdown | `-H "Markdown: yes"` | enables bold/italic/links/code in the message |
| Click action | `-H "Click: <url>"` | URL opened when notification is tapped |

Example — a failure alert:

```bash
ntfy-send -s <server> -o <topic> -t "Build failed" -p high -T warning,rotating_light \
  -- "CI pipeline failed on main branch"
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

`ntfy-send` and `curl` print a JSON response line on success (it contains an
`"id"` field) — check it rather than assuming the notification landed.
`ntfy-send` exits non-zero on an HTTP error (bad or expired token,
unauthorized topic). Raw `curl` without `-f` exits 0 on those errors and
prints an error body instead (look for `"code"` and `"error"`), so a zero
exit code from curl does *not* mean the notification succeeded.
