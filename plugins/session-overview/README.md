# session-overview

A Claude Code mod that shows every open Claude Code session on the machine in a side pane, grouped by project, with each session's goal and state.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install session-overview@wovemind
```

## Requirements

- A Claude Code version that loads plugin mods (the plugin registers a TypeScript module through `hooks/hooks.json`, not a skill).
- Optional: `tmux`. Clicking a session switches your tmux client to it; outside tmux the list is read-only.
- Works wherever Claude Code keeps its session files under `~/.claude/`.

## What it sends to a model

On the first prompt of a session that has no title yet, the plugin sends up to the first 4000 characters of that prompt to the Haiku model and uses the 3-to-6-word reply as the session title. It skips prompts that start with `/`, prompts that did not come from you, and sessions that already have a title (for example one set with `/rename`).

## Opinionated defaults

| Default | Change it with |
|---|---|
| The pane opens only when you run `/sessions` | `/sessions auto on` opens it, unfocused, on every new session (including after `/clear`); `/sessions auto off` turns that off |
| Untitled sessions are named by Haiku from their first prompt | `/rename <title>` sets your own title, which always wins |
| All session types are shown | the per-type toggle buttons or the `1`-`9` hotkeys |

## Usage

Run `/sessions` to open the pane. It refreshes every 3 seconds while open.

Run `/sessions auto on` to open the pane (unfocused) on every new session, including after `/clear`; `/sessions auto off` turns it off. The choice is remembered.

- Sessions are grouped by run directory; worktrees (`<repo>/.claude/worktrees/<name>`) appear under their repo with the worktree name. Home is shown as `~`.
- Goal: a title you set with `/rename <title>`, else the session's AI title, else the first line of its first prompt, else the registry name.
- State: `running`, `waiting` (with what it waits for, e.g. permission prompt), `idle` (finished, awaiting next prompt), `ended` (leftover registry entry whose process is gone).
- One toggle button per session type (`cli`, `bg`, `sdk-cli`, ...) hides or shows that type; the choice is remembered across restarts and shown in every open session within a few seconds.
- A count at the top shows how many sessions need you; projects with a waiting or running session are listed first. ◆ waiting, ● running, ○ idle, ✕ ended. A dim "today" after the title marks a session active today; click the ☆ before a title to star it (★, saved across restarts and shown in every open session within a few seconds) and starred sessions lead their project; this session's title is bold and tagged "(this one)".
- Click a session running in tmux to switch this tmux client to it (`tmux switch-client`); sessions outside tmux, and ended ones, are not clickable.
- Toggles have hotkeys `1`-`9` (type order, shown on each button). They work while the pane has the keyboard: `/sessions` opens it focused, otherwise click it or press ctrl+x tab. Arrows scroll a tree taller than the pane; Esc returns to the prompt.

## Example

The pane with three sessions in one project:

```
1 need you   1 running   1 idle

my-app  ~/workspace
  ◆ Fix login redirect
    waiting: permission prompt
  ● GDPR and PECR compliance audit
    worktree wt-1
  ○ Add pricing page

1: bg  2: cli  3: sdk-cli (hidden)
```

## Environment variables and settings

No environment variables and no plugin settings. It only reads `~/.claude/sessions/*.json` and `~/.claude/projects/<encoded-cwd>/<sessionId>.jsonl`.
