# Security

## Reporting a vulnerability

Report security problems privately through GitHub: open the repository's
**Security** tab and choose **Report a vulnerability** (GitHub private
vulnerability reporting). Please do not open a public issue for a
vulnerability.

Include the plugin name and version, what an attacker could do, and the steps
to reproduce it. We will reply in the advisory thread.

## What plugins can do on your machine

Plugins in this marketplace run with your permissions:

- skills and commands tell Claude to run shell commands (for example `git`,
  `gh`, `curl`, package managers);
- some plugins install hooks that run on every matching Claude Code event
  (for example `ui-change-guard` checks every Bash call) or git hooks;
- some ship scripts that are put on your `PATH` (for example `ntfy-send`).

Read a plugin's README, and its `hooks/` and `bin/` folders, before you
install it, and install only the plugins you need.
