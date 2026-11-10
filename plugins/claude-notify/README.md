# claude-notify

Send desktop notifications via the `claude-notifier` CLI.

## What it does

Teaches Claude to call `claude-notifier` when a task finishes or Claude is
blocked and needs the user's attention, using its title/subtitle/sound/
terminal/session-id flags.

## Usage

Ask Claude to notify you, e.g.:

> "Let me know when this finishes"
> "Ping me if you get stuck"

By default, Claude notifies on task completion and when blocked — no extra
setup needed beyond `claude-notifier` being installed.

## Required environment

- `claude-notifier` CLI installed and on `PATH` (Homebrew:
  `/opt/homebrew/bin/claude-notifier`)

## Example

```bash
claude-notifier -t "Task done" -m "Build finished, all tests pass" -S default
```

See `skills/claude-notify/SKILL.md` for the full flag reference.
