# Review Checklist and Best Practices

Read before opening a pull request.

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
