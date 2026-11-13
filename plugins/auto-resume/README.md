# auto-resume

A Claude Code mod that types `continue` into a session that stopped on the usage limit (the 5-hour session limit or the weekly limit), once that limit resets. Long unattended runs, such as `/plan-tools:plan-implement-complete`, pick up where they stopped.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install auto-resume@wovemind
```

## Requirements

- A Claude Code version that loads plugin mods (the plugin registers a TypeScript module through `hooks/hooks.json`, not a skill).
- A claude.ai subscription, so Claude Code reports the rate-limit windows and their reset times.

## Usage

| Command | What it does |
|---|---|
| `/auto-resume on` | Resume every session automatically. Kept across restarts. |
| `/auto-resume off` | Turn it off and cancel any pending `continue`. |
| `... /auto-resume` inside a prompt | Resume only the task that prompt starts, e.g. `/plan-tools:plan-implement-complete plan.md /auto-resume`. The word is removed before the prompt or command runs. The task ends at the next prompt you type without it. |
| `/auto-resume` alone | Show whether it is on and when the next `continue` is due. |

While a `continue` is pending, the status line shows `auto-resume at <time>`.

## How it works

1. When the main conversation stops with a `rate_limit` error, the mod reads the windows Claude Code reports and takes the latest reset time among the exhausted ones.
2. Three minutes after that reset it submits `continue` as a normal prompt. The wait lets Claude Code's built-in auto-continue go first. If anything starts a turn before then (the built-in auto-continue or you), the pending `continue` is dropped.
3. With no reset time reported, it tries again in 30 minutes. A `continue` that hits the limit again schedules the next one.

It checks the wall clock every minute, so a laptop that slept through the reset catches up when it wakes. Limits hit by subagents are ignored; only the main conversation's stop counts.

## Limits

- It can only type into a session that is open. If you close the terminal, the pending `continue` is saved and fires when you reopen that session with `claude --resume`.
- No environment variables or settings. State is kept in the plugin's own store.
