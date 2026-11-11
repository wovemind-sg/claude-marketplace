# Versioning

Read when deciding whether and how to set or bump a `version`, or setting up release channels.

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
