# Self-hosted ntfy: auth config, users and tokens

Source: https://docs.ntfy.sh/config/ (access control, iOS instant
notifications, config options table). Every `server.yml` key has an
environment-variable twin (`auth-file` = `NTFY_AUTH_FILE`, and so on), for
servers run from Docker or a PaaS.

## server.yml

Usually `/etc/ntfy/server.yml`. Add or change only these keys:

```yaml
base-url: "https://ntfy.example.com"   # the public URL the phone uses
auth-file: "/var/lib/ntfy/auth.db"     # setting this turns on auth (SQLite)
auth-default-access: "deny-all"        # default is read-write: anyone could read/post
behind-proxy: true                     # only if behind nginx/Caddy/Traefik/a PaaS edge
upstream-base-url: "https://ntfy.sh"   # needed for instant iOS pushes
```

| Key | Env var | Why |
|---|---|---|
| `base-url` | `NTFY_BASE_URL` | public URL of the server |
| `auth-file` | `NTFY_AUTH_FILE` | user/ACL/token database; must be on persistent storage |
| `auth-default-access` | `NTFY_AUTH_DEFAULT_ACCESS` | `read-write` (default), `read-only`, `write-only`, `deny-all` |
| `behind-proxy` | `NTFY_BEHIND_PROXY` | use forwarded headers for the visitor IP (rate limiting) |
| `upstream-base-url` | `NTFY_UPSTREAM_BASE_URL` | forwards a poll request (message ID only, not the text) via ntfy.sh so iOS gets instant pushes |

If the server already uses `database-url` (`NTFY_DATABASE_URL`, PostgreSQL),
users live there and `auth-file` is not needed.

Restart ntfy after editing (e.g. `sudo systemctl restart ntfy`, or restart
the container).

## Users and access (run on the server)

These commands edit the auth database directly, so run them on the server
host (or inside the container), as a user that can write `auth-file`. They
read `auth-file` from `server.yml`; if it errors that auth-file is not set,
pass `--auth-file <path>` or set `NTFY_AUTH_FILE`.

Simplest: one admin user (admins can read/write every topic):

```bash
ntfy user add --role=admin <user>     # prompts for the password
```

Or a regular user limited to the topic:

```bash
ntfy user add <user>
ntfy access <user> <topic> rw
```

The interactive prompt keeps the password out of shell history and out of
Claude's transcript. `NTFY_PASSWORD=... ntfy user add <user>` also works
non-interactively, but only use it if the user accepts that the password is
visible wherever the command is shown.

## Token for Claude

```bash
ntfy token add --label claude-code <user>
# prints: token tk_... created for user <user>, never expires
```

`--expires=30d` makes it expire. `ntfy token list <user>` lists tokens,
`ntfy token remove <user> tk_...` revokes one. Save it to `~/.ntfy` as in
step 4 of SKILL.md.

## Declarative alternative

Users, ACL entries and tokens can also be provisioned in `server.yml` with
`auth-users` (`<user>:<bcrypt-hash>:<role>`, hash from `ntfy user hash`),
`auth-access` and `auth-tokens` (`<user>:tk_...[:label]`, token from
`ntfy token generate`). Users removed from the config are deleted from the
database on restart, and the token would then sit in the config file in
plain text, so prefer the CLI unless the user already manages ntfy this way.
