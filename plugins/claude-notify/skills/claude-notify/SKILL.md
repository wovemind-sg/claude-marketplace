---
name: claude-notify
description: >
  Send a desktop notification via the claude-notifier CLI. By default, notify
  when Claude finishes the given task or gets blocked and needs the user's
  attention — e.g. "let me know when done", "notify me if you get stuck",
  "ping me". Use whenever the user asks to be notified, pinged, or alerted,
  even if they don't say "claude-notifier" explicitly.
---

# claude-notify

Sends a native desktop notification via the `claude-notifier` CLI (already
installed at `/opt/homebrew/bin/claude-notifier`).

## Default triggers

Unless the user specifies otherwise, send a notification:
- when the requested task finishes
- when Claude is blocked and needs the user's input (a decision, missing
  info, a permission prompt with no response)

## Usage

```bash
claude-notifier -m "<message>" [options]
```

| Flag | Meaning |
|---|---|
| `-m, --message "text"` | Notification body (required) |
| `-t, --title "text"` | Title (default: "Claude") |
| `-s, --subtitle "text"` | Subtitle |
| `-i, --session-id "id"` | Session ID for focus-on-click |
| `-T, --terminal "type"` | iterm2, terminal, vscode, vscodium, cursor, windsurf, zed, ghostty, warp, webstorm, intellij |
| `-S, --sound "sound"` | "default", "none", or a named sound (Glass, Basso, Blow, Ping, Pop, Funk, Submarine) |
| `-c, --claude-session-id "id"` | Claude session ID, for resolving session context |

Set `-t` to reflect the outcome ("Task done" / "Claude needs input") and
`-m` to a one-line summary of what happened or what's needed. Use
`-S urgent`-style attention (e.g. `Basso` or `Ping`) when blocked, default
sound when just done.

Example — task finished:

```bash
claude-notifier -t "Task done" -m "Build finished, all tests pass" -S default
```

Example — blocked on user:

```bash
claude-notifier -t "Claude needs input" -m "Which auth provider should I use?" -S Ping
```

If `claude-notifier` errors, run `claude-notifier doctor` to diagnose
installation/permission issues.
