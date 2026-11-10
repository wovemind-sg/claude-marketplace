#!/usr/bin/env python3
"""Install, uninstall, or check the ui-change-guard pre-push guard for the current git repo.

usage: push_guard.py install | uninstall | status | gate

The guard has two halves, both switched on per repo by the `enabled` file in
<git-dir>/ui-change-guard/:
  - Claude Code: the plugin's PreToolUse hook calls `gate`, which blocks Claude's
    `git push` until /ui-change-guard:review-ui-change has passed for HEAD.
  - git: a pre-push hook that runs the review via `claude -p` for pushes made
    outside Claude Code, and blocks on an UNSAFE verdict.
A passed review for a commit is recorded as <state>/reviewed-<sha>, so a commit
is reviewed once no matter which half sees the push first.
"""
import json
import os
import re
import subprocess
import sys

MARK = "# ui-change-guard pre-push hook"

GIT_HOOK = MARK + """ (installed by /ui-change-guard:push-guard; remove with /ui-change-guard:push-guard uninstall)
# Skip once with: git push --no-verify
state=$(git rev-parse --git-path ui-change-guard)
[ -f "$state/enabled" ] || exit 0
# ponytail: checks HEAD only, pushing another branch than HEAD reviews HEAD's diff
head=$(git rev-parse HEAD)
[ -f "$state/reviewed-$head" ] && exit 0
if ! command -v claude >/dev/null 2>&1; then
  echo "ui-change-guard: claude CLI not found, push blocked. Skip with: git push --no-verify" >&2
  exit 1
fi
echo "ui-change-guard: reviewing UI changes before push (skip with: git push --no-verify)..." >&2
out=$(claude -p "/ui-change-guard:review-ui-change" --allowedTools "Read Grep Glob Bash" --disallowedTools "Edit Write NotebookEdit" </dev/null)
status=$?
printf '%s\\n' "$out" >&2
if [ $status -ne 0 ]; then
  echo "ui-change-guard: review did not run (exit $status), push blocked. Skip with: git push --no-verify" >&2
  exit 1
fi
case "$out" in
  *"# UI change review — UNSAFE"*)
    echo "ui-change-guard: verdict UNSAFE, push blocked. Fix the blockers above, or skip with: git push --no-verify" >&2
    exit 1 ;;
esac
mkdir -p "$state" && : > "$state/reviewed-$head"
"""

PUSH_RE = re.compile(r"\bgit\b[^;&|\n]*\bpush\b")


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def paths(cwd=None):
    state = git("rev-parse", "--path-format=absolute", "--git-path", "ui-change-guard", cwd=cwd)
    hooks = git("rev-parse", "--path-format=absolute", "--git-path", "hooks", cwd=cwd)
    return state, hooks and os.path.join(hooks, "pre-push")


def ours(hook):
    with open(hook) as f:
        return MARK in f.read()


def install():
    state, hook = paths()
    if os.path.exists(hook) and not ours(hook):
        sys.exit(f"Not installed: {hook} already exists and is not ours. "
                 "Add a call to `claude -p /ui-change-guard:review-ui-change` to it by hand, or remove it and re-run.")
    os.makedirs(state, exist_ok=True)
    open(os.path.join(state, "enabled"), "w").close()
    os.makedirs(os.path.dirname(hook), exist_ok=True)
    with open(hook, "w") as f:
        f.write("#!/bin/sh\n" + GIT_HOOK)
    os.chmod(hook, 0o755)
    print(f"Installed.\n  git pre-push hook: {hook}\n  Claude Code push gate: on (state in {state})")


def uninstall():
    state, hook = paths()
    if os.path.isdir(state):
        for name in os.listdir(state):
            os.remove(os.path.join(state, name))
        os.rmdir(state)
    removed = os.path.exists(hook) and ours(hook)
    if removed:
        os.remove(hook)
    print("Uninstalled.\n  git pre-push hook: " + ("removed" if removed else "none of ours found")
          + "\n  Claude Code push gate: off")


def status():
    state, hook = paths()
    on = os.path.exists(os.path.join(state, "enabled"))
    has_hook = os.path.exists(hook) and ours(hook)
    reviewed = len([n for n in os.listdir(state) if n.startswith("reviewed-")]) if os.path.isdir(state) else 0
    print(f"Claude Code push gate: {'on' if on else 'off'}\n"
          f"git pre-push hook: {'installed' if has_hook else 'not installed'} ({hook})\n"
          f"reviewed commits recorded: {reviewed}")


def gate():
    """PreToolUse hook: exit 2 (block, message to Claude) on an unreviewed git push."""
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not PUSH_RE.search(cmd):
        return
    cwd = data.get("cwd") or None
    state, _ = paths(cwd)
    if not state or not os.path.exists(os.path.join(state, "enabled")):
        return
    marker = os.path.join(state, "reviewed-" + (git("rev-parse", "HEAD", cwd=cwd) or "none"))
    if os.path.exists(marker):
        return
    sys.stderr.write(
        "ui-change-guard: push blocked until the UI change review passes for this commit.\n"
        "1. Run /ui-change-guard:review-ui-change and show the report to the user.\n"
        f"2. If the verdict is SAFE or NEEDS ENGINEER REVIEW, record it with: touch '{marker}' — then push again.\n"
        "3. If the verdict is UNSAFE, do not push and do not create the file; the blockers must be fixed first.\n")
    sys.exit(2)


if __name__ == "__main__":
    actions = {"install": install, "uninstall": uninstall, "status": status, "gate": gate}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit(__doc__)
    if sys.argv[1] != "gate" and git("rev-parse", "--git-dir") is None:
        sys.exit("Not inside a git repository.")
    actions[sys.argv[1]]()
