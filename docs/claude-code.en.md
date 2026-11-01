# V-Mind with Claude Code: MCP, start instructions and hooks

A short English guide to connecting V-Mind to Claude Code. The full reference is in
German: [docs/cli.md](cli.md). Each section says how far it has been tested.

## 1. MCP server

*Tested:* Claude Code in the Code tab of the Claude desktop app with `.mcp.json` in the
project folder; the project itself is developed this way. The handshake and journal
writes are covered by an automated test (`mcp_server_handshakes_and_writes_journal_in_configured_scope`).
Claude Code in the terminal reads the same `.mcp.json`; we have not run a separate
documented test there.

```sh
vmind init vmind.db
```

```sh
claude mcp add vmind -- vmind --scope my-project mcp vmind.db
```

Or create `.mcp.json` in the project folder:

```json
{"mcpServers": {"vmind": {"command": "vmind", "args": ["--scope", "my-project", "mcp", "vmind.db"]}}}
```

Start a new session and approve the `vmind` server. If the tools do not appear, see the
troubleshooting table in the [README](../README.md#3-register-the-mcp-server).

*Not yet tested on every platform:* the Claude desktop app **chat** (outside the Code tab)
via `claude_desktop_config.json` with absolute paths.

## 2. Start instructions for the AI

*Tested:* both texts are built into the program and checked for the same sections,
operations and check states by an automated test.

```sh
vmind start-prompt en
```

prints the English start instructions ([prompts/start.en.md](../prompts/start.en.md));
`vmind start-prompt` or `vmind start-prompt de` prints the German original. With
`--json` the text is under `prompt` and the language under `language`. Put the text into
your host's system or project instructions (for Claude Code, for example, `CLAUDE.md`).
The built-in Ollama client always uses the German text.

*Not tested:* whether a given model follows the instructions reliably. Instructions
describe what V-Mind can do; they do not give a model tool access.

## 3. Optional: project state at session start (SessionStart hook)

*Tested by the maintainers in their own setup; no automated test.* In
`.claude/settings.local.json` (personal, do not commit):

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command",
  "command": "vmind --scope my-project resume \"$CLAUDE_PROJECT_DIR/vmind.db\""}]}]}}
```

## 4. Optional: record tool calls (PostToolUse hook, schema 6)

*Covered by automated tests* (`observe_hook_stores_tool_and_path_but_never_content_command_or_error`
and the observation tests); available from the development version after 0.2.0. The
maintainers' own database still uses schema 5, so this hook has not run in their daily
setup yet.

```json
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Bash|Edit|Write", "hooks": [{"type": "command",
        "command": "vmind --scope my-project observe \"$CLAUDE_PROJECT_DIR/vmind.db\""}]}
    ],
    "PostToolUseFailure": [
      {"matcher": "Bash|Edit|Write", "hooks": [{"type": "command",
        "command": "vmind --scope my-project observe \"$CLAUDE_PROJECT_DIR/vmind.db\""}]}
    ]
  }
}
```

`observe` reads the hook message from stdin and stores only the session ID, call ID, tool,
result (`completed` or `failed`) and, for Edit/Write, the file path relative to the project
folder. **Commands, output, error text and file contents are neither stored nor run.**
Paths outside the project are left out; the project folder and file path must be absolute.
The same message twice gives no second entry. `observe` never creates a database or
upgrades its schema; with an older database the hook reports an error until you upgrade
deliberately.

`resume` and `report` summarise the last three sessions. **Observed does not mean
checked:** a completed Bash call is not a passed test, a finished task or a validation.
File paths and session IDs are metadata that can be confidential. Observations are
currently never deleted automatically.
