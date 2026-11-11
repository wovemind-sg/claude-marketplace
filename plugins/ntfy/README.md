# ntfy

Send push notifications to your phone/desktop via [ntfy](https://ntfy.sh)
([source](https://github.com/binwiederhier/ntfy), [docs](https://docs.ntfy.sh/))
over its plain-HTTP publish API.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install ntfy@wovemind
```

## Requirements

- `curl` and `bash` (the `ntfy-send` script uses both).
- An ntfy app or web client subscribed to your topic, to receive the notifications.

## What it does

Teaches Claude how to publish notifications — with titles, priority, tags,
action buttons, attachments, scheduled delivery, and markdown — to
ntfy.sh or a self-hosted ntfy server, so Claude can ping you when a long-running task
finishes, a build fails, or anything else worth interrupting you for.

Other plugins in this marketplace use it: `plan-tools` (`drain-issues`) and
`compliance-audit` (`apply`) send their "finished" and "stuck" alerts through it.

## Usage

Ask Claude to notify you, e.g.:

> "Ping me on ntfy when this build finishes"
> "Send me a push notification if the tests fail, topic `ci-alerts`"

Or use the command, which keeps working and sends the push once the condition is met
(priority 4 unless you name another):

```
/ntfy:notify-me when you finish the implementation
```

## Settings and environment variables

Set the plugin's `server` and `topic` settings with `/plugin configure ntfy@wovemind` (or the
dialog shown when the plugin is enabled):

| Setting | Default | What it does |
|---|---|---|
| `server` | `https://ntfy.sh` | The ntfy server every notification is published to. Point it at your own instance if you self-host. |
| `topic` | `claude` | The topic notifications go to unless you name another one in a request. |

The defaults only take effect after you save the dialog once; until then the
skill and command fall back to `https://ntfy.sh` and `claude` themselves
(except when `~/.ntfy` exists, see below).

No environment variables are used. One file is:

- **Auth token** (optional): if `~/.ntfy` exists, its one line (a `tk_...`
  access token generated with `ntfy token add` on the server) is sent as a
  Bearer token **to whatever `server` is configured, including the public
  ntfy.sh**. So while `~/.ntfy` exists, the skill and command send nothing
  until you have saved the `server` setting once (to your own server, or to
  `https://ntfy.sh` if that is where the token belongs); they ask you to run
  `/plugin configure ntfy@wovemind` instead. Without `~/.ntfy` they fall back
  to `https://ntfy.sh` as described above. Do not point `server` at a server
  you do not trust with the token, or move the file away first.

The plugin also puts `ntfy-send` on your `PATH`:

```bash
ntfy-send -s https://ntfy.sh "Build finished" -t "my-repo" -p 4 -o my-topic
ntfy-send --help   # self-check: prints usage and exits 0
```

## Opinionated defaults

| Default | Change it with |
|---|---|
| Server `https://ntfy.sh` | the `server` setting |
| Topic `claude` | the `topic` setting; for one message, name another topic in your request, or `-o <topic>` with `ntfy-send` |
| `/ntfy:notify-me` sends at priority 4 (high) | name a priority in the command, e.g. `urgent` |

On the public ntfy.sh, anyone who subscribes to a topic name receives its
messages, and `claude` is an easy name to guess. Treat the topic like a
password: if you use ntfy.sh, set the `topic` setting to a long random name
(the `plan-tools` and `compliance-audit` alerts use it too), or run your own
server with access control.

## Example

```bash
curl -H "Title: Build failed" \
     -H "Priority: high" \
     -H "Tags: warning,rotating_light" \
     -d "CI pipeline failed on main branch" \
     https://ntfy.sh/ci-alerts
```

See `skills/ntfy/references/options.md` for the full header reference
(action buttons, attachments, scheduled delivery, JSON publishing).
