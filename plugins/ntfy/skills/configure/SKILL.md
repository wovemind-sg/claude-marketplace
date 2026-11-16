---
name: configure
description: >
  Walk the user step by step from zero to ntfy push notifications arriving on
  their phone: choose public ntfy.sh or a self-hosted server, turn on auth on a
  self-hosted server (with extra help when it runs on Railway), create a user and
  access token, save the token to ~/.ntfy, set up the iOS/Android app, save the
  plugin settings and send a test push. Use this whenever the user wants to set
  up, configure, connect or fix ntfy — e.g. "set up ntfy", "configure
  notifications", "connect the ntfy app", "notifications aren't arriving on my
  phone", "add auth/a token to my ntfy server" — even if they don't say "ntfy".
argument-hint: "[ntfy.sh | self-hosted | railway]"
---

# Set up ntfy notifications

Get the user from nothing to "a test push arrived on my phone". Go one step at
a time: say what the step does and why, do what you can yourself, and wait for
the user to confirm before moving past any step that needs their hands (phone,
dashboard, plugin dialog). `$ARGUMENTS` may already name the path; skip the
questions it answers.

Never print a token or password into the transcript: no `cat ~/.ntfy`, no
echoing command output that contains `tk_...`. Pipe tokens straight into the
file and check the file instead.

## 1. Find out where the user stands

- **Saved settings**: server `${user_config.server}`, topic
  `${user_config.topic}`. A value that still contains the text `user_config`
  or is empty was never saved (same rule as the `ntfy` skill in this plugin).
  Do not stop when they are unsaved, as the `ntfy` skill does: saving them is
  part of this walkthrough.
- **Token file**: `[ -f ~/.ntfy ] && echo yes` (test only, never print it).
- Ask, in one message: public ntfy.sh or their own server? If their own: is it
  on Railway or somewhere else, and its public URL? Phone: iOS or Android? If
  `~/.ntfy` exists: which server does that token belong to?

## 2. Public ntfy.sh

No server work and no token: anyone who knows the topic name can read and
send to it, so the topic name is the password.

- If `~/.ntfy` exists and belongs to another server, `ntfy-send` would send it
  to ntfy.sh too. With the user's OK, move it aside:
  `mv ~/.ntfy ~/.ntfy.bak` (check first that no `~/.ntfy.bak` would be
  overwritten).
- Suggest a long random topic, e.g. `claude-$(openssl rand -hex 12)`, and
  show it (a topic is not a token; the user needs to type it on the phone).
  Plain `claude` is easy to guess.

Server = `https://ntfy.sh`. Go to step 5.

## 3. Self-hosted server: turn on auth

The server is already installed; this step only configures access control so
strangers can't read or post to the user's topics.

- **Railway**: suggest the user run `/use-railway` (or
  `/railway:use-railway`, depending on how it was installed) so its Railway
  CLI know-how is loaded, then read `references/railway.md` and follow it.
  You make the Railway changes yourself, with the user's OK.
- **Anywhere else**: read `references/self-hosted.md` and guide the user
  through `server.yml` and the `ntfy user` / `ntfy token` commands on their
  server. You usually have no shell there, so give exact commands and wait.

Pick the topic first (any name, e.g. `claude`: with `deny-all`, only
logged-in users can use it); a non-admin user needs access to it.

Both end with: an auth-enabled server, a user the phone logs in as, and a
`tk_...` token for Claude.

## 4. Save the token to `~/.ntfy`

`ntfy-send` sends the one line in `~/.ntfy` as a Bearer token. If `~/.ntfy`
already exists and belongs to another server, ask before overwriting.

- When you can run the token command yourself (Railway, or a server you can
  reach over ssh), pipe it straight into the file:

  ```bash
  (umask 077; <command that runs: ntfy token add --label claude-code <user>> \
    | grep -oE 'tk_[A-Za-z0-9]+' > ~/.ntfy.new) \
    && mv ~/.ntfy.new ~/.ntfy && echo ok || rm -f ~/.ntfy.new
  ```

  (`ntfy token add` prints `token tk_... created for user <user>, ...`.
  Writing to `~/.ntfy.new` first keeps an existing `~/.ntfy` intact when the
  command fails, and the new file is created mode 600.)
- When the user creates it on the server by hand, ask them to run this
  locally in their own terminal (the token then never passes through Claude):

  ```bash
  bash -c 'umask 077; read -rs -p "Token: " t && [[ $t == tk_* ]] && printf "%s\n" "$t" > ~/.ntfy.new && mv ~/.ntfy.new ~/.ntfy || echo " not saved: expected tk_..."'
  ```

  (`bash -c` because zsh's `read -p` means something else. Anything not
  starting with `tk_`, such as an empty line or the password, leaves an
  existing `~/.ntfy` untouched.)

  Then check it with `grep -q '^tk_' ~/.ntfy && echo ok`.

## 5. Phone app

- **iOS**: install "ntfy" from the App Store.
- **Android**: install "ntfy" from Google Play or F-Droid.

Then, in the app:

- Self-hosted: add the server URL and the username/password from step 3
  (the app's settings let you set a default server and add users; when
  subscribing you can also pick another server than ntfy.sh). Menu labels
  vary by app version, so describe what to look for rather than an exact path.
- Subscribe to the topic chosen for this setup.
- Android, self-hosted: keep "instant delivery" on for the subscription and
  let the app ignore battery optimization, or pushes can arrive late. (Google
  Play builds use Firebase only for ntfy.sh; F-Droid always uses instant
  delivery.)
- iOS, self-hosted: instant pushes only work when the server sets
  `upstream-base-url: https://ntfy.sh` (step 3). Without it, delivery can
  take hours.

Wait for the user to confirm the app is subscribed.

## 6. Plugin settings

Claude cannot open the plugin dialog. Ask the user to run
`/plugin configure ntfy@wovemind` and set:

- `server`: `https://ntfy.sh` or their server's URL (no trailing topic).
- `topic`: the topic from step 2 or 3, the one subscribed to in step 5.

The new values reach this plugin's skills after `/reload-plugins` or a new
session; for the test below use the values the user just entered.

## 7. Test push

Send it only if `~/.ntfy` is absent or holds the token for `<server>`:
`ntfy-send` sends that token to whatever server it is given. If the user
kept a token for another server (declined to move or overwrite it in step 2
or 4), skip the test and say why, and warn that every later push to
`<server>` would send that token too until `~/.ntfy` is moved.

```bash
ntfy-send -s <server> -o <topic> -t "ntfy configured" -- "Test from Claude Code"
```

Success prints a JSON line with an `"id"`. Ask the user whether it arrived.

| Symptom | Likely cause |
|---|---|
| HTTP 401 | `~/.ntfy` empty, wrong, or for another server |
| HTTP 403 | `~/.ntfy` missing (anonymous on a `deny-all` server), or the user has no write access to the topic (`ntfy access <user> <topic> rw`, or make the user admin) |
| `"id"` printed but nothing on the phone | phone subscribed to another server/topic, or not logged in as a user with read access |
| arrives on Android, not (or hours late) on iOS | `upstream-base-url` not set on the server |
| late on Android | instant delivery off or battery optimization on |

Once it arrives, tell the user `/ntfy:notify-me` and the `ntfy` skill now
use these settings.
