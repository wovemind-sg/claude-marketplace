# Manifests — marketplace.json and plugin.json

Read when creating or editing `.claude-plugin/marketplace.json` or a plugin's `plugin.json`, or fixing a validator error.

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
| `source` | string\|object | ✅ | Where to fetch plugin (see [sources-distribution.md](sources-distribution.md)). |
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

## Validator messages

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
