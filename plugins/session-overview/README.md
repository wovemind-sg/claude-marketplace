# session-overview

A Claude Code mod that shows every open Claude Code session on the machine in a side pane, grouped by project, with each session's goal and state.

## Install

```
/plugin install session-overview@wovemind
```

## Usage

Run `/sessions` to open the pane. It refreshes every 3 seconds while open.

Run `/sessions auto on` to open the pane (unfocused) on every new session, including after `/clear`; `/sessions auto off` turns it off. The choice is remembered.

- Sessions are grouped by run directory; worktrees (`<repo>/.claude/worktrees/<name>`) appear under their repo with the worktree name. Home is shown as `~`.
- Goal: a title you set with `/rename <title>`, else the session's AI title, else the first line of its first prompt, else the registry name.
- State: `running`, `waiting` (with what it waits for, e.g. permission prompt), `idle` (finished, awaiting next prompt), `ended` (leftover registry entry whose process is gone).
- One toggle button per session type (`cli`, `bg`, `sdk-cli`, ...) hides or shows that type; the choice is remembered across sessions.
- A count at the top shows how many sessions need you; projects with a waiting or running session are listed first. ◆ waiting, ● running, ○ idle, ✕ ended. A dim "today" after the title marks a session active today; click the ☆ before a title to star it (★, saved across restarts) and starred sessions lead their project; this session's title is bold and tagged "(this one)".
- Click a session running in tmux to switch this tmux client to it (`tmux switch-client`); sessions outside tmux, and ended ones, are not clickable.
- Toggles have hotkeys `1`-`9` (type order, shown on each button). They work while the pane has the keyboard: `/sessions` opens it focused, otherwise click it or press ctrl+x tab. Arrows scroll a tree taller than the pane; Esc returns to the prompt.

Example:

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

## Configuration

No environment variables. It only reads `~/.claude/sessions/*.json` and `~/.claude/projects/<encoded-cwd>/<sessionId>.jsonl`.
