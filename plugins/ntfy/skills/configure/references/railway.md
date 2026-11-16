# ntfy on Railway

Same settings as `references/self-hosted.md`, applied as `NTFY_*` service
variables. Use the `use-railway` skill's commands for reading/setting
variables, volumes and deploys; the only command spelled out here is
`railway ssh --service <svc> -- <cmd>`, which runs one command in the running
container.

## 1. Find the service and read its current state

Link the project if needed and identify the ntfy service. Read, without
changing anything:

- its variables (look for existing `NTFY_*` values, especially
  `NTFY_AUTH_FILE` and `NTFY_DATABASE_URL`),
- its volumes and their mount paths,
- its public domain (this is the server URL).

## 2. Plan the changes and get the user's OK

Show the user the exact list before applying. Set only what is missing or
wrong:

| Variable | Value |
|---|---|
| `NTFY_BASE_URL` | `https://<public domain>` |
| `NTFY_AUTH_FILE` | a file inside the volume, e.g. `/var/lib/ntfy/auth.db` (skip if `NTFY_DATABASE_URL` is set: users then live in Postgres) |
| `NTFY_AUTH_DEFAULT_ACCESS` | `deny-all` |
| `NTFY_BEHIND_PROXY` | `true` (Railway's edge proxies every request) |
| `NTFY_UPSTREAM_BASE_URL` | `https://ntfy.sh` (if the user has an iPhone) |

**Volume**: without `NTFY_DATABASE_URL`, the auth database must sit on a
volume, or every user and token disappears on the next deploy. If no volume
is mounted on the directory of `NTFY_AUTH_FILE`, add one there (or point
`NTFY_AUTH_FILE` at the existing volume's mount path).

## 3. Apply and redeploy

Apply the variables and volume, then make sure a new deployment runs with
them. Wait until that deployment is live before any `railway ssh`, or the
user/token lands in the old container.

Things you may not be able to do from the CLI (for example a setting that
only exists in the dashboard): list them for the user with exact
instructions and wait.

## 4. Create the user (user's terminal)

`railway ssh` here is non-interactive, so it cannot answer the password
prompt, and passing `NTFY_PASSWORD` on the command line would put the
password in the transcript. Ask the user to run, in their own terminal:

```bash
railway ssh --service <svc>
ntfy user add --role=admin <user>    # inside the container; prompts for the password
exit
```

Only if the user explicitly accepts the password showing in the transcript,
run it yourself instead:
`railway ssh --service <svc> -- env NTFY_PASSWORD='<pw>' ntfy user add --role=admin <user>`.

## 5. Create the token (you)

The container has `NTFY_AUTH_FILE` in its environment, so the CLI finds the
database. Use the pipe from step 4 of SKILL.md, with
`railway ssh --service <svc> -- ntfy token add --label claude-code <user>`
as the command.

If that does not print `ok`, run
`railway ssh --service <svc> -- ntfy user list` to see the error (it prints
no secrets; rerunning `token add` would leave another live token on the
server). A `Host key verification failed` error means `ssh.railway.com` is
missing from `~/.ssh/known_hosts`; with the user's OK, add it with
`ssh-keyscan -t ed25519 ssh.railway.com >> ~/.ssh/known_hosts`.
