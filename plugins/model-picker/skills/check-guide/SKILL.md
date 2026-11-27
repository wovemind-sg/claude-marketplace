---
name: check-guide
description: Check whether Anthropic's model guide behind the pick-model skill has changed in meaning, using a content hash for a fast no-change answer. Use when the user asks whether the model guidelines are still correct or up to date, or before relying on pick-model after a long time.
---

# check-guide

Checks the live guide against `${CLAUDE_SKILL_DIR}/../pick-model/references/guide.md`.

## Steps

1. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/guide_hash.py`. It prints JSON `{status, sha256}`, plus `text_file` only when `status` is `changed`.
   - Exit 2 / `status: "error"`: the guide could not be fetched. Report the error and stop.
   - `status: "unchanged"`: report "guide unchanged" and stop. This is the fast path.
2. `status: "changed"`: read `text_file` (the live page text) and `guide.md`. Compare meaning only: recommendations, task table rows, models, effort levels, prices, defaults, escalation rules. Ignore wording, layout, navigation, dates and related-post changes.
3. No meaningful difference: run `python3 ${CLAUDE_SKILL_DIR}/scripts/guide_hash.py --write-hash` (saves the new hash and date) and report "no meaningful change".
4. Meaningful difference: report each changed recommendation, price or rule (old vs new). Write nothing.

The hash is stored in `pick-model/references/guide.lock.json`. For installed users it lives in the plugin cache and is lost on plugin update.
