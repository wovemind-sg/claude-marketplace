# Plugin Components — skills, commands, agents, hooks, MCP

Read when adding or editing a skill, command, agent, hook or MCP server.

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
