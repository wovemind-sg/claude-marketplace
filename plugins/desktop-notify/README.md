# desktop-notify

Send desktop notifications via the `claude-notifier` CLI. macOS only.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install desktop-notify@wovemind
```

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

## Requirements

- macOS (the plugin is macOS-only)
- `claude-notifier` CLI installed and on `PATH`. The plugin does not install
  it. Claude checks with `command -v claude-notifier`; if it is missing,
  Claude says it is not installed and stops. If it is installed but
  notifications do not appear, `claude-notifier doctor` diagnoses
  installation and permission problems.

## Environment variables and settings

None. The plugin has no environment variables and no plugin settings.

## Opinionated defaults

| Default | Change it with |
|---|---|
| Notify when the task finishes and when Claude is blocked on you | say when you want to be notified, e.g. "only ping me if the tests fail" |
| Title "Task done" or "Claude needs input"; default sound when done, an alert sound such as `Ping` when blocked | ask for a different title or sound |

## Example

```bash
claude-notifier -t "Task done" -m "Build finished, all tests pass" -S default
```

See `skills/desktop-notify/SKILL.md` for the full flag reference.
