## What changed and why

## Review checklist

See [CONTRIBUTING.md](../CONTRIBUTING.md) and the Review Checklist in [CLAUDE.md](../CLAUDE.md#review-checklist).

- [ ] Plugin directory created under plugins/<plugin-name>/
- [ ] .claude-plugin/plugin.json present with at least name and description
- [ ] Component dirs (skills/, agents/, hooks/, etc.) at the PLUGIN ROOT — not inside .claude-plugin/
- [ ] skills/ used (not commands/) for any new skill definitions
- [ ] Each SKILL.md has a description in its YAML frontmatter
- [ ] README.md present with purpose, usage, env vars, and an example
- [ ] No secrets or credentials committed
- [ ] Plugin entry added to .claude-plugin/marketplace.json with name and source
- [ ] Plugin name is kebab-case (lowercase letters, digits, hyphens only)
- [ ] version bumped in plugin.json if modifying an existing plugin
- [ ] version NOT set in both plugin.json and the marketplace entry
- [ ] JSON validated: claude plugin validate . passes with no errors
- [ ] Tested locally: plugin installs and skill/command works as expected
- [ ] ${CLAUDE_PLUGIN_ROOT} used in any hook or MCP server paths (not hardcoded absolute paths)
- [ ] PR description explains what changed and why
