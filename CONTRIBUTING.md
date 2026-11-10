# Contributing

Thanks for helping. The full conventions for this repository (file layout,
manifest fields, skills, hooks, MCP servers, versioning) are in
[`CLAUDE.md`](CLAUDE.md). This page is the short version.

## Propose a new plugin

Open an issue with the **Plugin proposal** template first, so we can agree on
scope before you write it. Then:

1. Create `plugins/<plugin-name>/` with a `.claude-plugin/plugin.json` that has
   at least `name` and `description`. Names are kebab-case and must not start
   with `claude-`, `anthropic-` or `cc-plugin-`.
2. Put component folders (`skills/`, `agents/`, `hooks/`, …) at the plugin
   root, not inside `.claude-plugin/`. Use `skills/<name>/SKILL.md` for new
   skills.
3. Write `README.md`: purpose, install, requirements, environment variables
   (or "None"), and an example.
4. Add an entry with `name` and `source` to `.claude-plugin/marketplace.json`.
   Do not set `version` there.
5. Validate and test locally (see below), then open a pull request.

Details: [Adding New Plugins](CLAUDE.md#adding-new-plugins).

## Change an existing plugin

Bump `version` in the plugin's `plugin.json` once per pull request:

- patch (`1.0.0` → `1.0.1`): bug fixes, wording, examples;
- minor (`1.0.0` → `1.1.0`): new skills, arguments or settings, nothing removed;
- major (`1.0.0` → `2.0.0`): renamed or removed skills, changed arguments.

Installed users only get an update when the version changes. Keep existing
behaviour working when someone runs a skill without your new arguments.
Details: [Modifying Existing Plugins](CLAUDE.md#modifying-existing-plugins).

## Validate and test

```bash
claude plugin validate .                    # the whole marketplace
claude plugin validate plugins/<name>       # one plugin
```

In Claude Code, from the root of your clone:

```
/plugin marketplace add ./
/plugin install <name>@wovemind
/reload-plugins
```

Pull requests run the same validation and the scripts' `--selftest` checks
(`.github/workflows/validate.yml`).

## Before you open the pull request

Go through the [Review Checklist](CLAUDE.md#review-checklist); the pull
request template repeats it. Never commit secrets, tokens or personal paths;
read them from environment variables or plugin settings and document them in
the README.

By contributing you agree that your work is released under the
[MIT licence](LICENSE).
