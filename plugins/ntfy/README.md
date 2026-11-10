# ntfy

Send push notifications to your phone/desktop via [ntfy](https://ntfy.sh)
([source](https://github.com/binwiederhier/ntfy), [docs](https://docs.ntfy.sh/))
over its plain-HTTP publish API.

## What it does

Teaches Claude how to publish notifications — with titles, priority, tags,
action buttons, attachments, scheduled delivery, and markdown — to
ntfy.sh or a self-hosted ntfy server, so Claude can ping you when a long-running task
finishes, a build fails, or anything else worth interrupting you for.

## Usage

Ask Claude to notify you, e.g.:

> "Ping me on ntfy when this build finishes"
> "Send me a push notification if the tests fail, topic `ci-alerts`"

Defaults to the `claude` topic unless you name a different one.

## Setup

Set the plugin's `server` setting with `/plugin configure ntfy@wovemind` (or the
dialog shown when the plugin is enabled):

- **Server**: `server` setting, default `https://ntfy.sh` (public, no account
  needed). Point it at your own instance if you self-host.
- **Auth token** (optional): if `~/.ntfy` exists, its one line (a `tk_...`
  access token generated with `ntfy token add` on the server) is sent as a
  Bearer token. Leave it out for public ntfy.sh.
- **Default topic**: `claude`

The plugin also puts `ntfy-send` on your `PATH`:

```bash
ntfy-send -s https://ntfy.sh "Build finished" -t "my-repo" -p 4 -o my-topic
ntfy-send --help   # self-check: prints usage and exits 0
```

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
