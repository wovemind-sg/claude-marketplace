# model-picker

Recommends which Claude model and effort level to use for a job, based on Anthropic's guide "Which Claude model should you build with?", and checks that the guide has not changed.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install model-picker@wovemind
```

## Commands

| Command | What it does |
|---|---|
| `/model-picker:pick-model <job description>` | Claude reads the stored guide and your job, then returns model, effort, the matched guide row, a reason and what to try if it falls short. It recommends only; it does not run the job. |
| `/model-picker:check-guide` | Fetches the live guide, hashes its text and compares the hash with the stored one. Unchanged: done. Changed: compares meaning against the stored copy and reports changed recommendations, prices or rules. |

## How check-guide works

`skills/pick-model/references/guide.md` holds the guide as decision rules. `guide.lock.json` next to it holds the sha256 of the guide page's visible text and the date checked. `scripts/guide_hash.py` fetches the page and compares hashes (fast path). A hash miss can come from wording or layout, so the model then compares meaning; if only wording changed, it saves the new hash and reports no meaningful change. A meaningful change is reported; `check-guide` itself writes nothing. This repo's finalize-pr hook then updates `guide.md`, the lock and `plugin.json`.

## Requirements

- Network access to claude.dev for `check-guide`.
- Python 3 (standard library only).

## Environment variables and settings

None.

## Opinionated defaults

| Default | Change it with |
|---|---|
| A job that fits no guide row gets Opus 5.5 at medium. | edit the "You aren't sure yet" row in `guide.md` |
