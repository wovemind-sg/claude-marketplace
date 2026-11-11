---
description: Send an ntfy push notification at a point the user names (e.g. "/notify-me when you finish the implementation")
argument-hint: <condition, e.g. "when you finish the implementation">
---

Parse "$ARGUMENTS" for:
- a **condition** — when to send the notification (e.g. "when you finish the implementation", "if the tests fail")
- an optional **priority** override — if the user names one (min/low/default/high/urgent, or 1-5), use it; otherwise default to priority **4 (high)**

Continue with the work already in progress / requested in this conversation. Once the condition is met, send a push notification using this plugin's `ntfy-send` script (or the ntfy skill's curl pattern if the script isn't available). The server is the plugin's `server` setting, `${user_config.server}`; if that value still contains the text `user_config` or is empty, the setting was never saved: if `~/.ntfy` exists (`[ -f ~/.ntfy ] && echo yes` — test only, never print the file), do not send anything, since its token may belong to another server; tell the user to run `/plugin configure ntfy@wovemind` and set `server` (to their own server, or to `https://ntfy.sh` if that is where their token belongs), then stop. When running unattended (called from another skill such as plan-tools `drain-issues` or compliance-audit `apply`), skip the notification and say so in the report instead of stopping the caller. With no `~/.ntfy`, use `https://ntfy.sh`. The topic is the plugin's `topic` setting, `${user_config.topic}`; if that value still contains the text `user_config` or is empty, use `claude`. A topic the user names in "$ARGUMENTS" wins:

```bash
ntfy-send -s <server> -o <topic> -t "<short title>" -p 4 -- "<short message describing what happened>"
```

Single-quote any value with `$`, backticks or `'` in it (`'\''` for a literal `'`).

- Message: one line, states what happened (e.g. "Implementation finished — all tests passing").
- Title: short context label (e.g. the task or repo name).
- Priority: 4 unless the user's condition/args specify otherwise.

Do not fabricate completion — only send the notification once the condition has genuinely been met.
