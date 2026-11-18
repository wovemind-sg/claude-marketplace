# CLAUDE.md — Claude Code Plugin Marketplace

Claude Code auto-reads this file every session start. Core rules here; detailed reference in `.claude/docs/` — read the matching file when the trigger applies.

| Read | When |
|------|------|
| `.claude/docs/manifests.md` | Editing `marketplace.json` or `plugin.json` (full field schemas), or fixing a validator error/warning |
| `.claude/docs/components.md` | Adding/editing a skill, command, agent, hook, or MCP server (formats + examples) |
| `.claude/docs/versioning.md` | Deciding how version resolves, or setting up release channels |
| `.claude/docs/sources-distribution.md` | Marketplace entry with external `source` (GitHub, git URL, git-subdir, npm), or hosting/pinning/private repos/CI seeding |
| `.claude/docs/review-checklist.md` | Writing a new plugin or skill (best practices), and before opening a pull request (checklist) |

---

## Repository Overview

Repo = Claude Code **plugin marketplace** — catalog for users to discover + install plugins from this team or community. Claude Code reads `.claude-plugin/marketplace.json` for plugin list. Each plugin = self-contained directory with own `.claude-plugin/plugin.json` manifest. This marketplace is `wovemind`.

Contributor guide: `CONTRIBUTING.md` (short version of this file). Security reports: `SECURITY.md`.

**Website**: https://marketplace.wovemind.com/ — built by `site/build.py` from the manifests, skill/command frontmatter and one how-to spec per skill, command or mod in `site/specs/<plugin>/<item>.json`. `.github/workflows/site.yml` rebuilds it and deploys it to webbie on every push to `main`. Keep it in sync in the same PR as the change:
- New skill or command: add its spec (write it with `/help-me-understand:help-me-understand`, page type `how-to`, usage only — what it does and how to use it, not how it works). The build fails without it.
- New mod command (no SKILL.md/command file): add its spec too and mention `/<name>` in the plugin's `README.md`, or the build rejects the spec. Nothing fails if you forget the spec, so check yourself.
- Changed usage (arguments, options, requirements, output) of an existing one: update its spec.
- Removed or renamed one: delete or rename its spec. The build fails on an orphan spec, unless the plugin README still mentions `/<name>` (then it passes as a mod page), so also fix the README.
- New plugin: nothing extra for its card and plugin page; specs for its skills as above.

**Change the site**: edit `site/build.py` (Python string templates), `site/assets/site.css`, `site/assets/site.js`. Build: `python3 site/build.py --out <dir>`. Check: `python3 site/build.py --selftest` (build also fails on broken or absolute links).

**Upload a preview** (staging only; live site untouched until a push to `main`):
1. Build and zip: `python3 site/build.py --out <dir> && (cd <dir> && zip -qr <zip> .)`
2. Get a one-time upload URL. The webbie MCP is configured only in `~/workspace/webbie`: `cd ~/workspace/webbie && claude -p 'Use the webbie MCP import_zip tool for site slug "marketplace" and return ONLY the one-time upload URL.'`
3. Upload: `curl -sS --fail-with-body -X PUT --data-binary @<zip> <upload-url>`. The reply is the staging preview URL. Form submissions on staging are test-only, not emailed.

**Reserved marketplace names** — reserved by Anthropic, unusable: `claude-code-marketplace`, `claude-code-plugins`, `claude-plugins-official`, `anthropic-marketplace`, `anthropic-plugins`, `agent-skills`, `knowledge-work-plugins`, `life-sciences`. Names impersonating official marketplaces (e.g. `official-claude-plugins`, `anthropic-tools-v2`) also blocked.

**Reserved plugin names** — plugin name cannot start with `claude-`, `anthropic-`, `anthropics-`, or `cc-plugin-`, be `claude`/`anthropic`/`anthropics`/`claude-code`/`claude-mods`, or pair `official` with `claude`/`anthropic`.

---

## File Structure

```
/
├── CLAUDE.md                          ← You are here
├── .claude/docs/                      ← Detailed reference (see table above)
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

## Commands

```bash
# Validate marketplace + all plugins (needs no sign-in)
claude plugin validate .

# Script self-tests (same list as CI; needs: pip install pillow numpy)
for f in \
  plugins/ui-audit/skills/capture/scripts/dep_hash.py \
  plugins/ui-audit/skills/capture/scripts/diff_images.py \
  plugins/ui-audit/skills/capture/scripts/build_report.py \
  plugins/ui-audit/skills/capture/scripts/capture.py \
  plugins/compliance-audit/skills/audit/scripts/detect_signals.py \
  plugins/compliance-audit/skills/audit/scripts/license_scan.py \
  plugins/compliance-audit/skills/apply/scripts/parse_cards.py \
  plugins/design-inspiration/skills/mockup/scripts/strip_wrapper.py \
  plugins/help-me-understand/skills/help-me-understand/scripts/build_page.py \
  site/build.py; do
  python3 "$f" --selftest || break
done
```

Validate passes for the whole marketplace. Validator checks `plugin.json`, skill/agent/command frontmatter, `hooks/hooks.json` for syntax + schema errors. Adding a script with `--selftest`: also add it to `.github/workflows/validate.yml`.

Test locally (inside session):

```
/plugin marketplace add ./
/plugin install <plugin-name>@wovemind
/reload-plugins          # after edits
```

---

## Adding New Plugins

1. Create directory under `plugins/<plugin-name>/`.
2. Create `.claude-plugin/plugin.json` with at minimum `name` and `description`.
3. Add component directories (`skills/`, `agents/`, `hooks/`, etc.) at plugin root — not inside `.claude-plugin/`.
4. Write `README.md` with purpose, usage, configuration.
5. Add entry to `.claude-plugin/marketplace.json` with `name` and `source`. Add a website spec per skill/command (see **Website** above).
6. Validate: `claude plugin validate .` (or `/plugin validate .` inside session).
7. Test locally: `/plugin marketplace add ./` then `/plugin install <name>@<marketplace-name>`.
8. Open pull request — CI (`.github/workflows/validate.yml`) runs `claude plugin validate .` and the scripts' `--selftest` checks.

---

## Modifying Existing Plugins

### Non-breaking changes (patch bump)

Bug fixes, better descriptions, new examples — bump `version` from `1.0.0` to `1.0.1` in `plugin.json`.

### Additive changes (minor bump)

New skills or agents, nothing removed — bump to `1.1.0`.

### Breaking changes (major bump)

Renaming or removing skill, changing argument contracts — bump to `2.0.0`. Consider keeping previous version in separate directory (e.g. `plugins/my-plugin-v1/`) so existing users not break.

**Never edit published plugin's behaviour without version bump.** Installed users get updates only when version string changes (or, if no version set, when new commit pushed).

Any of these that changes how a skill/command is used also updates its website spec (see **Website** above).

---

## Core Conventions

- **Do not set `version` in both `plugin.json` and marketplace entry.** `plugin.json` always wins silently, masks marketplace value.
- Use `skills/<name>/SKILL.md` for new skills, not `commands/`.
- `SKILL.md` frontmatter: only valid keys `name`, `description`, `argument-hint`, `compatibility`, `context`, `disable-model-invocation`, `license`, `metadata`, `user-invocable`. Others (e.g. `allowed-tools`) silently ignored or flagged. `description` = full sentence saying *when* to use — drives auto-invocation.
- Always use `${CLAUDE_PLUGIN_ROOT}` in hook + MCP paths (plugin runs from cache, hardcoded paths break). `${CLAUDE_PLUGIN_DATA}` for state surviving updates.
- Never commit secrets — env var references only, documented in plugin `README.md`.

## Gotchas

- Malformed `hooks/hooks.json` blocks entire plugin from loading — validate before commit.
- Relative `source` paths must start with `./`, resolve from marketplace root, no `../`.
- When skill scripts call external HTTP API, test exact curl command against real endpoint before trusting — 3xx redirect (e.g. Railway-hosted service force-redirecting http→https) fails silently with `curl -d` (empty output, exit 0, no error) unless you add `-L`.
