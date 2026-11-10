---
name: push-guard
description: Install, uninstall, or check the ui-change-guard pre-push guard for the current git repository, so every push is gated by the review-ui-change safety review — both pushes Claude makes and pushes from the terminal. Use when the user wants to "review before every push", "add a pre-push hook", "run the UI review automatically on push", "turn off / remove the push check", or asks whether the guard is on.
argument-hint: "install | uninstall | status"
---

Manage the pre-push guard for the git repository in the current directory. `$ARGUMENTS` is `install`, `uninstall`, or `status`; if it is empty or anything else, ask which one.

Run from the repository root:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/push-guard/scripts/push_guard.py <install|uninstall|status>
```

Relay the script's output. If it exits with an error, show the error and stop — in particular, never delete or overwrite an existing `pre-push` hook it refused to touch; tell the user what it said and let them decide.

After `install`, tell the user in two lines what now happens:
- When Claude runs `git push`, the push is blocked until `/ui-change-guard:review-ui-change` passes for that commit (SAFE or NEEDS ENGINEER REVIEW).
- When they push from a terminal, git runs the review through `claude -p` (takes a few minutes and uses tokens) and blocks on UNSAFE. `git push --no-verify` skips it once.

The guard is per clone: it lives in `.git/`, nothing is committed, and teammates install it themselves.
