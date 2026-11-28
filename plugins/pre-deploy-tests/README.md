# pre-deploy-tests

Tests an app before it is deployed. The plan skill writes a test plan for the app's logic and its UI on every platform, screen size, orientation and browser it supports, and splits it into test sessions, each with the model that suits it.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install pre-deploy-tests@wovemind
```

## Commands

| Command | What it does |
|---|---|
| `/pre-deploy-tests:plan [--full]` | Detects the app type (web, Capacitor, native iOS / Android), confirms it with you along with device sizes, orientations, browsers, the test target and the highest model, then writes `.pre-deploy-tests/SPEC.md` and splits it into test sessions with `/plan-tools:split-plan`, each with a model from `/model-picker:pick-model`. Uses `user-flows.md` when present. A later run plans only what changed since the last plan; `--full` plans everything again. Commits only `.pre-deploy-tests/record.json` (after asking) and publishes a `pre-deploy-tests` commit status. |

## Example

```
/pre-deploy-tests:plan
```

1. Answer the questions: app type, device sizes, orientations, Firefox, the test target (default branch locally, or an integration environment URL), the highest model.
2. Read the coverage summary (areas, platforms, sizes, sessions with their models) and say go.
3. The sessions are in `.pre-deploy-tests/sessions/` and the record is committed.

## Requirements

- Plugins `plan-tools`, `model-picker` and `user-flows` (installed with this plugin).
- `git`, and `gh` signed in for the commit status (optional: a failed status is reported, not fatal).

## Environment variables and settings

None. Test credentials are named by environment variables in `.pre-deploy-tests/record.json`; secrets are never stored.

## Opinionated defaults

| Default | Change it with |
|---|---|
| Chromium and WebKit are tested; Firefox only when you say you support it. | the Firefox question |
| Sizes: desktop 1440x900, tablet 820x1180, phone 390x844, small phone 360x640, in every orientation you choose (desktop has no landscape variant). | the device-class and orientation questions |
| The highest model a session gets is Opus; a pick above it gets Opus with one more effort level. | the highest-model question, asked every run |
| Only `.pre-deploy-tests/record.json` is committed; everything else in `.pre-deploy-tests/` stays local. | the `.gitignore` question on the first run |
| A later plan tests only what changed since the last plan; if most of the change is shared code, it plans everything. | `--full` |
