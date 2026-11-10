---
description: Send an ntfy push notification at a point the user names (e.g. "/notify-me when you finish the implementation")
argument-hint: <condition, e.g. "when you finish the implementation">
---

Parse "$ARGUMENTS" for:
- a **condition** — when to send the notification (e.g. "when you finish the implementation", "if the tests fail")
- an optional **priority** override — if the user names one (min/low/default/high/urgent, or 1-5), use it; otherwise default to priority **4 (high)**

Continue with the work already in progress / requested in this conversation. Once the condition is met, send a push notification using this plugin's `ntfy-send` script (or the ntfy skill's curl pattern if the script isn't available). The server is the plugin's `server` setting, `${user_config.server}`; if that value still contains the text `user_config`, the setting was never saved, so use `https://ntfy.sh`:

```bash
ntfy-send -s ${user_config.server} "<short message describing what happened>" -t "<short title>" -p 4
```

- Message: one line, states what happened (e.g. "Implementation finished — all tests passing").
- Title: short context label (e.g. the task or repo name).
- Priority: 4 unless the user's condition/args specify otherwise.

Do not fabricate completion — only send the notification once the condition has genuinely been met.
