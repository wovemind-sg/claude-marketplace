# record.json

`.pre-deploy-tests/record.json` is the only committed file of the plugin. The plan skill writes it at the end of every plan; the next plan reads it to test only what changed. The run skill reads the profile, target and launch commands from it.

## Schema

```json
{
  "schema": 1,
  "planned_at": "2026-11-28",
  "mode": "full",
  "last_planned_sha": "<full sha of HEAD when the plan was made>",
  "base_sha": null,
  "profile": {
    "app_type": "web | web+native | native",
    "native_platforms": ["ios", "android"],
    "web": true,
    "device_classes": ["desktop", "tablet", "phone", "small-phone"],
    "orientations": ["portrait", "landscape"],
    "browsers": ["chromium", "webkit"],
    "dark_mode": false,
    "rtl": false,
    "languages": [],
    "user_flows": true,
    "template": "fastapi-template | go-webapp-template | null"
  },
  "platform_copies": ["chromium", "webkit", "ios", "android"],
  "target": {
    "kind": "local | integration",
    "branch": "main",
    "url": null
  },
  "model_cap": "opus",
  "launch": {
    "start": "uvicorn app.main:app --port {port}",
    "db_setup": "createdb {db} && DATABASE_URL=postgresql:///{db} alembic upgrade head",
    "ready_url": "http://localhost:{port}/health",
    "test_account": "make seed-test-user, or env vars TEST_EMAIL / TEST_PASSWORD",
    "native_build": {"ios": "npx cap run ios --target <sim>", "android": "npx cap run android --target <avd>"}
  },
  "shared_paths": ["static/css/app.css", "templates/base.html", "src/components/**"],
  "sessions": [
    {
      "id": "01",
      "title": "Sign-up and login",
      "model": "opus",
      "effort": "high",
      "capped_from": null,
      "platform_copies": ["chromium", "webkit", "ios"],
      "items": ["T-001", "T-002"],
      "flows": ["UF-001", "UF-002"],
      "screens": ["/login", "/signup"],
      "files": ["app/routes/auth.py", "templates/auth/*.html"]
    }
  ]
}
```

Field notes:

- `mode` is `full` or `incremental`; `base_sha` is the `last_planned_sha` an incremental plan diffed from, `null` for a full plan.
- `launch` is `null` for an integration target and for template projects (they use `make worktree-env`). Never store a secret in it: test credentials are named by their environment variables.
- `shared_paths` lists code that many screens use: global stylesheets, the base layout or template, the design system or shared components, the router, the API client, auth middleware. Record it at planning time; the incremental rules below rely on it.
- `sessions[].files` are paths or globs of the source each session's items trace to. Be complete: a file missing here is a change the next plan cannot route to a session.
- An incremental plan writes a full record again: the sessions it planned, plus the earlier record's sessions it did not touch (carried over unchanged), so the next diff still maps to every session.

## Incremental selection

1. **Baseline.** `git merge-base --is-ancestor <last_planned_sha> HEAD`. If it fails (history rewritten, commit gone), fall back to a full plan. Cross-check the commit status: `gh api repos/{owner}/{repo}/commits/<last_planned_sha>/statuses --jq '.[] | select(.context=="pre-deploy-tests") | .description'`. A missing status is reported in one line and does not block; the record is the baseline.
2. **Changed files.** `git diff --name-only <last_planned_sha>..HEAD -- . ':!.pre-deploy-tests'`. Only commits from the last plan to HEAD count. No changed file and no bug to re-test: tell the user nothing needs testing and stop before step 3 of the skill.
3. **Sessions whose files changed.** A session is selected when a changed file matches one of its `files`, or a changed flow in `user-flows.md` is in its `flows` (compare the `### UF-NNN` blocks at both commits).
4. **Sessions using changed shared code.** A changed file in `shared_paths`, or one that other covered files import or include (search for its module, template or stylesheet name), selects every session whose files use it. Where that cannot be told, select every session that shows UI on the affected platform copies.
5. **New screens and flows.** A changed or added file that matches no session's `files` (a new route, page, screen, component or `UF-NNN`) gets new test items, in a new session or added to the closest selected one.
6. **Bugs to re-test.** See below; each becomes a test item in the session that covers its place, or in a re-test session of its own.
7. **Mostly shared.** If the selected sessions are more than half of the recorded sessions, or most changed lines are in shared code, plan in full instead and say so in one line: a diff that wide is a full re-test anyway.
8. **New platform.** If the diff adds a native platform or a web build, ask the app-type question again; new platform copies get every session's items, not only the changed ones.

Each selected session is re-planned from the current code (its items may have changed), not copied from the old session file.

## Bugs to re-test

Bug files are not committed, so look for them in this order:

1. Local `.pre-deploy-tests/bugs/BUG-NNN/bug.md` (before step 2 of the skill archives them).
2. Otherwise the latest bug review page: Artifact `action: "list"`, the newest artifact titled "… Pre-deploy Tests" whose `data-repo` matches this repo. Read its cards.

Read each bug's choice from the page's shared state (Artifact `read_db`, collection `choice`, doc id = bug id, value `fix` or `skip`). Re-test every bug whose choice is `fix` or that has no choice yet (undecided). Skip those marked `skip`. If no page exists, re-test every local bug. Each re-test item quotes the bug's steps and expected result and traces to its `BUG-NNN`.
