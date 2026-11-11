# Plugin Sources and Distribution

Read when a marketplace entry points outside this repo (`source` object), or when changing how the marketplace is hosted, pinned, or pre-seeded.

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
