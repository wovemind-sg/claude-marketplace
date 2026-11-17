# token-utilization

A Claude Code mod that stops the agent when usage reaches a limit you name in the prompt. Write `Do XXX until /session-token-utilization gets to 90%` and the run stops once the 5-hour session window reaches 90%. It can stop at once, or let the agent wrap up first and save handoff notes, so a long unattended run does not use up the whole session or weekly window.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install token-utilization@wovemind
```

## Requirements

- A Claude Code version that loads plugin mods (the plugin registers a TypeScript module through `hooks/hooks.json`, not a skill).
- A claude.ai subscription, so Claude Code reports the session (5-hour) and weekly usage windows.

## Usage

| You write | What it does |
|---|---|
| `... until /session-token-utilization gets to 90%` | Stop when the session (5-hour) window reaches 90%. |
| `... until /weekly-token-utilization gets to 70%` | Stop when the weekly window reaches 70%. |
| both, joined by `or` / `and` | Stop at whichever is reached first. One mode covers both. |
| the phrase in a slash command's arguments | The same, e.g. `/plan-tools:plan-implement-complete plan.md until /session-token-utilization gets to 80%`. |
| `/token-utilization` | Show the limit, its current reading, the mode and the state. |
| `/token-utilization off` | Remove the limit. |

The phrase, from "until" through the percentage, is removed before the model or the command reads the prompt. When the prompt is sent, a question asks what should happen at the limit:

- **Stop immediately**: the running turn is cancelled and every running subagent is stopped.
- **Wrap up first**: the agent may finish a small remaining piece or record where it stands, then stops.

While a limit is set the status line shows it, e.g. `stop at session 90% (now 62%), wrap-up`. One transcript line marks the moment the limit is reached.

The limit lasts until it is reached, until a new prompt names another limit, or until `/token-utilization off`. Follow-up prompts you type keep it.

The prompt is not sent, with the reason shown, when:

- the percentage is missing or outside 1 to 100;
- the window is already at or past the limit;
- the mode question is closed with Esc;
- the prompt comes from `claude -p`, where nobody can answer the question.

## What happens at the limit

In **wrap-up** mode:

- **Main agent working, no subagents**: its turn is interrupted and a wrap-up prompt follows. The prompt tells the agent to finish a small remainder or stop and leave the work easy to continue, and to end with handoff notes.
- **Subagents running**: nobody is interrupted. Each running subagent gets the wrap-up message inside its run and reports what is done and what is left. The main agent reads its wrap-up message with the result of its next tool call. If it makes no further tool call, it never sees the message, and its ordinary final answer is saved as the handoff. When a subagent the mod messaged reports back after the stop, that report goes through without the restart question.
- **Main agent idle**: running background subagents get the wrap-up message, and the session is marked stopped. With none running, nothing is sent.
- **Hard ceiling**: usage is cut off 5 points above the limit, at most 100%. If usage reaches the ceiling during the wrap-up, the main turn is cancelled and every running subagent is stopped.

The main agent's final wrap-up message is saved by the mod as `.claude/handoffs/HANDOFF-<first 8 characters of the session id>.md` under the project root, and the transcript line gives the path. Each session writes its own file, so parallel sessions never overwrite each other's notes. The mod also writes `.claude/handoffs/.gitignore` containing `*`, so the folder stays out of git. To resume later, ask the agent to read that file first.

## After the stop

A prompt you type runs normally and clears the stop. Something else may try to restart the agent: a background task's notification, a scheduled task, `/loop`, or auto-resume's `continue`. Then the mod sends a notification through Claude Code's own notification channel (your `preferredNotifChannel` setting) and asks whether to run it:

- **Yes, run it**: it runs, and later automatic prompts run without asking.
- **No** or Esc: it is dropped, and the next one asks again.

Notifications about subagents the mod stopped are dropped without a question or a notification. They only report the stop.

## Limits

- Usage readings arrive with model responses and move in whole points, so the stop can land a point or two above the number you named.
- A new session has no reading until its first response, so a limit that is already passed is not caught when the prompt is sent. The limit is set, and the first reading stops the agent.
- The session must be open for the mod to act.
- Background shell commands keep running. They spend no tokens.
- If no usage reading has arrived yet (for example, no subscription), the status line says `no reading yet`, and a transcript line warns after the first turn that the limit cannot take effect.
- No environment variables or settings. State is kept in the plugin's own store and survives a reload.
