# CLAUDE.md — Claude Code Plugin Marketplace

Claude Code auto-reads this file every session start. Covers structure, conventions, guidelines for developing, modifying, publishing plugins (skills, agents, hooks, MCP servers) in this marketplace.

---

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [File Structure](#file-structure)
3. [The Marketplace File](#the-marketplace-file)
4. [Plugins](#plugins)
5. [Skills](#skills)
6. [Commands & Agents](#commands--agents)
7. [Hooks](#hooks)
8. [MCP Servers](#mcp-servers)
9. [Plugin Sources](#plugin-sources)
10. [Adding New Plugins](#adding-new-plugins)
11. [Modifying Existing Plugins](#modifying-existing-plugins)
12. [Versioning](#versioning)
13. [Testing & Validation](#testing--validation)
14. [Distribution](#distribution)
15. [Best Practices](#best-practices)
16. [Review Checklist](#review-checklist)

---

## Repository Overview

Repo = Claude Code **plugin marketplace** — catalog for users to discover + install plugins from this team or community. Claude Code reads `.claude-plugin/marketplace.json` for plugin list. Each plugin = self-contained directory with own `.claude-plugin/plugin.json` manifest.

Users add marketplace:

```bash
/plugin marketplace add <owner/repo>          # GitHub shorthand
/plugin marketplace add <git-url>             # Any git host
/plugin marketplace add ./path/to/marketplace # Local path for testing
```

Then install plugins:

```bash
/plugin install <plugin-name>@<marketplace-name>
```

**Reserved marketplace names** — reserved by Anthropic, unusable: `claude-code-marketplace`, `claude-code-plugins`, `claude-plugins-official`, `anthropic-marketplace`, `anthropic-plugins`, `agent-skills`, `knowledge-work-plugins`, `life-sciences`. Names impersonating official marketplaces (e.g. `official-claude-plugins`, `anthropic-tools-v2`) also blocked.

**Reserved plugin names** — plugin name cannot start with `claude-`, `anthropic-`, `anthropics-`, or `cc-plugin-`, be `claude`/`anthropic`/`anthropics`/`claude-code`/`claude-mods`, or pair `official` with `claude`/`anthropic`. This marketplace is `wovemind`.

---

## File Structure

```
/
├── CLAUDE.md                          ← You are here
├── .claude-plugin/
│   └── marketplace.json               ← REQUIRED: marketplace manifest
├── plugins/
│   └── <plugin-name>/
│       ├── .claude-plugin/
│       │   └── plugin.json            ← REQUIRED: plugin manifest
│       ├── skills/
│       │   └── <skill-name>/
│       │       └── SKILL.md           ← Skill definition
│       ├── commands/                  ← Flat .md skill files (legacy; prefer skills/)
│       ├── agents/                    ← Agent definitions
│       ├── hooks/
│       │   └── hooks.json             ← Hook configurations
│       ├── .mcp.json                  ← MCP server configurations
│       ├── .lsp.json                  ← LSP server configurations
│       ├── monitors/
│       │   └── monitors.json          ← Background monitor configs
│       ├── bin/                       ← Executables added to PATH
│       ├── settings.json              ← Default settings for the plugin
│       └── README.md                  ← Human-readable documentation
└── README.md                          ← Marketplace-level documentation
```

**Critical layout rule**: `commands/`, `agents/`, `skills/`, `hooks/`, other component directories must sit at **plugin root level** — not inside `.claude-plugin/`. Only `plugin.json` goes inside `.claude-plugin/`.

**Plugin isolation**: On install, Claude Code copies plugin directory to local versioned cache at `~/.claude/plugins/cache`. Plugins **cannot** reference files outside own directory via paths like `../shared-utils` — those not copied. Use symlinks to share files across plugins.

---

## The Marketplace File

`.claude-plugin/marketplace.json` = entry point for whole marketplace. **Must** exist at `.claude-plugin/marketplace.json` relative to repo root.

### Minimal example

```json
{
  "name": "my-marketplace",
  "owner": {
    "name": "Your Name",
    "email": "you@example.com"
  },
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./plugins/my-plugin",
      "description": "Does something useful"
    }
  ]
}
```

### Full marketplace schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Marketplace identifier (kebab-case, no spaces). Public-facing — users see during install (e.g. `/plugin install tool@your-marketplace`). |
| `owner` | object | ✅ | Maintainer info. Needs `name`; `email` optional. |
| `plugins` | array | ✅ | Plugin entries (see below). |
| `$schema` | string | — | JSON Schema URL for editor validation. Ignored by Claude Code at runtime. |
| `description` | string | — | Brief marketplace description. |
| `version` | string | — | Marketplace manifest version. |
| `metadata.pluginRoot` | string | — | Base directory prepended to relative plugin source paths (e.g. `"./plugins"` allows `"source": "my-plugin"` instead of `"source": "./plugins/my-plugin"`). |
| `allowCrossMarketplaceDependenciesOn` | array | — | Other marketplaces this marketplace's plugins may depend on. |

---

## Plugins

Each plugin lives in own directory, needs manifest at `.claude-plugin/plugin.json`.

### Plugin manifest (`plugin.json`)

```json
{
  "name": "my-plugin",
  "description": "A brief description shown in the plugin manager",
  "version": "1.0.0",
  "author": {
    "name": "Your Name",
    "email": "you@example.com"
  },
  "homepage": "https://docs.example.com/my-plugin",
  "repository": "https://github.com/org/my-plugin",
  "license": "MIT"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Unique identifier + skill namespace. Skills prefixed with it (e.g. `/my-plugin:hello`). |
| `description` | — | Shown in plugin manager. |
| `version` | — | If set, users get updates only when field changes. If omitted + distributed via git, commit SHA used; every commit = new version. |
| `author` | — | Attribution. Needs `name`; `email` optional. |
| `homepage` | — | Documentation URL. |
| `repository` | — | Source code URL. |
| `license` | — | SPDX identifier (e.g. `MIT`, `Apache-2.0`). |
| `dependencies` | — | Plugins this one needs (bare names resolve in this marketplace); installed along with it. E.g. plan-tools needs `ntfy`, `fastapi-template`, `htmx-vs-alpine`. |

### Plugin entry in `marketplace.json`

Each `plugins` array entry may include any `plugin.json` field, plus marketplace-specific fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Plugin identifier (kebab-case). Public-facing. |
| `source` | string\|object | ✅ | Where to fetch plugin (see [Plugin Sources](#plugin-sources)). |
| `description` | string | — | Shown in marketplace UI. |
| `version` | string | — | Pins plugin. `plugin.json` version always takes precedence if set. |
| `author` | object | — | `name` required, `email` optional. |
| `homepage` | string | — | Documentation URL. |
| `category` | string | — | Category for organisation (e.g. `"development"`, `"productivity"`). |
| `tags` | array | — | Tags for searchability. |
| `strict` | boolean | — | When `false`, marketplace entry = entire definition; plugin need not have `plugin.json`. Default: `true`. |
| `skills`, `commands`, `agents`, `hooks`, `mcpServers`, `lspServers` | string\|array\|object | — | Custom paths or inline config for components. |

**Avoid version conflicts**: never set `version` in both `plugin.json` and marketplace entry. `plugin.json` value always wins silently, can mask `marketplace.json` version.

---

## Skills

Skills extend Claude's capabilities; Claude invokes automatically based on task context. Live under `skills/<skill-name>/SKILL.md` inside plugin directory.

Skill names namespaced to plugin: skill at `skills/hello/SKILL.md` in plugin `my-plugin` becomes `/my-plugin:hello`.

### `SKILL.md` structure

```markdown
---
description: Reviews code for best practices and potential issues. Use when reviewing code, checking PRs, or analysing code quality.
disable-model-invocation: true
---

When reviewing code, check for:
1. Code organisation and structure
2. Error handling and edge cases
3. Security concerns
4. Test coverage

Be concise and actionable.
```

YAML frontmatter `description` critical — Claude uses it to decide when to auto-invoke skill. `disable-model-invocation: true` flag stops Claude calling model on own within skill.

Only valid frontmatter keys: `name`, `description`, `argument-hint`, `compatibility`, `context`, `disable-model-invocation`, `license`, `metadata`, `user-invocable`. Fields like `allowed-tools` (Claude.ai / API convention, not this repo's) silently ignored or flagged by editor.

Skills accept user input via `$ARGUMENTS` placeholder:

```markdown
---
description: Greet the named user warmly
---

Greet "$ARGUMENTS" warmly and ask how you can help them today.
```

Users invoke: `/my-plugin:hello Alex`

---

## Commands & Agents

### Commands (`commands/`)

Commands = flat Markdown files — use `skills/` directory for new plugins unless simple flat commands needed. Each `.md` file becomes slash command namespaced to plugin.

### Agents (`agents/`)

Agent definitions live in `agents/` directory. Each file defines specialised sub-agent Claude can delegate to.

```
my-plugin/
└── agents/
    ├── security-reviewer.md
    └── compliance-checker.md
```

Reference agents in marketplace entry:

```json
{
  "name": "my-plugin",
  "source": "./plugins/my-plugin",
  "agents": ["./agents/security-reviewer.md", "./agents/compliance-checker.md"]
}
```

---

## Hooks

Hooks live in `hooks/hooks.json`, run at specific points in Claude Code workflow (e.g. after tool use, before commit).

```json
{
  "PostToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh"
        }
      ]
    }
  ]
}
```

Use `${CLAUDE_PLUGIN_ROOT}` to reference files in plugin's installed location. Use `${CLAUDE_PLUGIN_DATA}` for state surviving plugin updates.

Malformed `hooks/hooks.json` blocks entire plugin from loading — always validate JSON before commit.

---

## MCP Servers

MCP server configs live in `.mcp.json` at plugin root.

```json
{
  "my-server": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/my-server",
    "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"]
  }
}
```

Can also declare MCP servers inline in marketplace entry:

```json
{
  "name": "my-plugin",
  "source": "./plugins/my-plugin",
  "mcpServers": {
    "my-server": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/my-server"
    }
  }
}
```

---

## Plugin Sources

`source` field in each plugin entry tells Claude Code where to fetch plugin. Once fetched, cached at `~/.claude/plugins/cache`.

### Relative path (plugins in this repo)

```json
{ "source": "./plugins/my-plugin" }
```

Paths must start with `./`, resolve relative to **marketplace root** (directory containing `.claude-plugin/`), not relative to `marketplace.json` itself. No `../` to escape marketplace root.

Relative paths work only when marketplace added via git. If users add via direct URL to `marketplace.json`, use external source instead.

### GitHub

```json
{
  "source": {
    "source": "github",
    "repo": "owner/plugin-repo",
    "ref": "v2.0.0",
    "sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
  }
}
```

`ref` (branch/tag) and `sha` (full 40-char commit SHA) both optional.

### Git URL

```json
{
  "source": {
    "source": "url",
    "url": "https://gitlab.com/team/plugin.git",
    "ref": "main"
  }
}
```

### Git subdirectory (monorepos)

```json
{
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/acme/monorepo.git",
    "path": "tools/my-plugin",
    "ref": "v2.0.0"
  }
}
```

Uses sparse checkout to minimise bandwidth.

### npm

```json
{
  "source": {
    "source": "npm",
    "package": "@acme/my-plugin",
    "version": "2.1.0",
    "registry": "https://npm.example.com"
  }
}
```

`version` and `registry` optional.

---

## Adding New Plugins

1. Create directory under `plugins/<plugin-name>/`.
2. Create `.claude-plugin/plugin.json` with at minimum `name` and `description`.
3. Add component directories (`skills/`, `agents/`, `hooks/`, etc.) at plugin root — not inside `.claude-plugin/`.
4. Write `README.md` with purpose, usage, configuration.
5. Add entry to `.claude-plugin/marketplace.json` with `name` and `source`.
6. Validate: `claude plugin validate .` (or `/plugin validate .` inside session).
7. Test locally: `/plugin marketplace add ./` then `/plugin install <name>@<marketplace-name>`.
8. Open pull request — CI re-validates all manifests.

---

## Modifying Existing Plugins

### Non-breaking changes (patch bump)

Bug fixes, better descriptions, new examples — bump `version` from `1.0.0` to `1.0.1` in `plugin.json`.

### Additive changes (minor bump)

New skills or agents, nothing removed — bump to `1.1.0`.

### Breaking changes (major bump)

Renaming or removing skill, changing argument contracts — bump to `2.0.0`. Consider keeping previous version in separate directory (e.g. `plugins/my-plugin-v1/`) so existing users not break.

**Never edit published plugin's behaviour without version bump.** Installed users get updates only when version string changes (or, if no version set, when new commit pushed).

---

## Versioning

Claude Code resolves plugin version from **first** set of:

1. `version` in plugin's `plugin.json`
2. `version` in plugin's marketplace entry
3. Git commit SHA of plugin source

**Omit `version`** for internal or actively-developed plugins — every commit auto-treated as new version via commit SHA.

**Set `version`** for stable, released plugins — users get updates only when you bump field. Prevents accidental updates.

**Do not set `version` in both places.** `plugin.json` value always wins silently.

### Release channels

For stable + latest channels, create two marketplace entries pointing at different refs:

```json
// stable entry
{ "name": "formatter", "source": { "source": "github", "repo": "org/formatter", "ref": "stable" } }

// latest entry (separate marketplace file)
{ "name": "formatter", "source": { "source": "github", "repo": "org/formatter", "ref": "latest" } }
```

Each channel must resolve to different version string; else Claude Code treats them identical, skips update.

---

## Testing & Validation

### Validate all manifests

```bash
claude plugin validate .
```

Or inside session:

```
/plugin validate .
```

Validator checks `plugin.json`, skill/agent/command frontmatter, `hooks/hooks.json` for syntax + schema errors.

### Common validation errors

| Error | Cause | Fix |
|-------|-------|-----|
| `File not found: .claude-plugin/marketplace.json` | Missing manifest | Create file |
| `Invalid JSON syntax` | Malformed JSON | Fix commas, quotes, brackets |
| `Duplicate plugin name "x"` | Two plugins share name | Give each unique `name` |
| `Plugin name "x" is reserved` | Name starts with `claude-` etc. | Rename for what it does |
| `Path contains ".."` | Source path escapes repo root | Use only `./`-relative paths |
| `YAML frontmatter failed to parse` | Bad YAML in `SKILL.md` | Fix frontmatter block |
| `Invalid JSON syntax` in hooks.json | Malformed hooks file | Fix JSON — malformed file blocks entire plugin |

### Common validation warnings

| Warning | Fix |
|---------|-----|
| `Marketplace has no plugins defined` | Add at least one entry to `plugins` |
| `No marketplace description provided` | Add top-level `description` |
| `Plugin name "x" is not kebab-case` | Rename to lowercase letters, digits, hyphens only |

When skill scripts call external HTTP API, test exact curl command against real endpoint before trusting — 3xx redirect (e.g. Railway-hosted service force-redirecting http→https) fails silently with `curl -d` (empty output, exit 0, no error) unless you add `-L`.

### Test locally before sharing

```bash
# Add the local marketplace
/plugin marketplace add ./

# Install a specific plugin
/plugin install my-plugin@my-marketplace

# Reload plugins after edits
/reload-plugins
```

---

## Distribution

### Hosting on GitHub (recommended)

Push repo to GitHub. Users add marketplace with `owner/repo` shorthand:

```
/plugin marketplace add your-org/your-marketplace
```

Pin to branch or tag with `@ref`:

```
/plugin marketplace add your-org/your-marketplace@v2.0
```

### Other git hosts (GitLab, Bitbucket, self-hosted)

```
/plugin marketplace add https://gitlab.com/company/plugins.git
```

### Requiring the marketplace for your team

Add to project's `.claude/settings.json` so team members get install prompt when they trust project folder:

```json
{
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": {
        "source": "github",
        "repo": "your-org/claude-plugins"
      }
    }
  },
  "enabledPlugins": {
    "code-formatter@company-tools": true,
    "deployment-tools@company-tools": true
  }
}
```

### Private repositories

Manual installs: Claude Code uses existing git credential helpers (e.g. `gh auth login`). Background auto-updates: set matching token env var:

| Provider | Environment variable |
|----------|---------------------|
| GitHub | `GITHUB_TOKEN` or `GH_TOKEN` |
| GitLab | `GITLAB_TOKEN` or `GL_TOKEN` |
| Bitbucket | `BITBUCKET_TOKEN` |

### Container / CI pre-population

Pre-populate plugins at image build time via `CLAUDE_CODE_PLUGIN_SEED_DIR`. Build seed:

```bash
CLAUDE_CODE_PLUGIN_CACHE_DIR=/opt/claude-seed claude plugin marketplace add your-org/plugins
CLAUDE_CODE_PLUGIN_CACHE_DIR=/opt/claude-seed claude plugin install my-tool@your-plugins
```

Then set `CLAUDE_CODE_PLUGIN_SEED_DIR=/opt/claude-seed` at runtime. Seed directory read-only — auto-updates disabled for seed-managed marketplaces.

---

## Best Practices

### General

- **Write `README.md` first.** Can't explain what plugin does + when to use → design needs more thought.
- **One responsibility per plugin.** Plugin doing 10 unrelated things harder to discover, test, maintain.
- **Never commit secrets.** Use env var references; document required env vars in `README.md`.
- **Use `skills/` over `commands/`** for new skill definitions — skills use `<name>/SKILL.md` pattern, current standard.

### Skills

- Write `description` frontmatter as complete sentence explaining *when* Claude should use skill. Claude relies on it for auto-invocation.
- Write instructions in imperative second-person voice ("Do X", "Return Y"), not descriptive.
- Use `disable-model-invocation: true` when skill should not trigger extra model calls internally.
- Use `$ARGUMENTS` for dynamic input; document expected argument format in `README.md`.
- Scope skills narrow — "Write a technical post-mortem" useful; "Write anything" not.

### Plugins

- Always use `${CLAUDE_PLUGIN_ROOT}` in hook + MCP server configs for bundled files — plugin copied to cache location on install, hardcoded paths break.
- Use `${CLAUDE_PLUGIN_DATA}` for state/data persisting across plugin updates.
- Validate `hooks/hooks.json` carefully — JSON syntax error blocks entire plugin from loading.
- Keep MCP server binaries inside plugin directory so they copy to cache with everything else.
- Never put component directories (`skills/`, `agents/`, `hooks/`, etc.) inside `.claude-plugin/` — only `plugin.json` belongs there.

### Versioning

- Follow [Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`.
- Never silently change plugin behaviour without version bump — users miss update if version string unchanged.
- Avoid setting `version` in both `plugin.json` and marketplace entry; `plugin.json` always wins, marketplace value silently ignored.
- Stable releases: always bump `version`. Internal dev plugins: omit `version`, rely on git commit SHAs.

### Documentation

- Every `README.md` must include: purpose, installation/usage, required env vars, worked example.
- Keep `SKILL.md` instructions focused on what Claude does at runtime — not installation steps (those belong in `README.md`).

---

## Review Checklist

Before opening pull request, confirm every item:

```
[ ] Plugin directory created under plugins/<plugin-name>/
[ ] .claude-plugin/plugin.json present with at least name and description
[ ] Component dirs (skills/, agents/, hooks/, etc.) at the PLUGIN ROOT — not inside .claude-plugin/
[ ] skills/ used (not commands/) for any new skill definitions
[ ] Each SKILL.md has a description in its YAML frontmatter
[ ] README.md present with purpose, usage, env vars, and an example
[ ] No secrets or credentials committed
[ ] Plugin entry added to .claude-plugin/marketplace.json with name and source
[ ] Plugin name is kebab-case (lowercase letters, digits, hyphens only)
[ ] version bumped in plugin.json if modifying an existing plugin
[ ] version NOT set in both plugin.json and the marketplace entry
[ ] JSON validated: claude plugin validate . passes with no errors
[ ] Tested locally: plugin installs and skill/command works as expected
[ ] ${CLAUDE_PLUGIN_ROOT} used in any hook or MCP server paths (not hardcoded absolute paths)
[ ] PR description explains what changed and why
```