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

## 5. Optional: matching knowledge when a tool call fails (PostToolUseFailure hook, 0.3.0-rc.8)

*Covered by automated tests* (`hint_hook_returns_matching_knowledge_as_marked_context_without_writing`,
`hint_hook_stays_silent_and_successful_on_every_failure_path`); not yet tried in a real
Claude Code session. Opt-in: add it next to or instead of `observe`.

```json
{
  "hooks": {
    "PostToolUseFailure": [
      {"matcher": "Bash", "hooks": [{"type": "command",
        "command": "vmind --scope my-project hint \"$CLAUDE_PROJECT_DIR/vmind.db\"",
        "timeout": 5}]}
    ]
  }
}
```

When a tool call fails, `hint` searches with the first 1000 characters of the hook's `error`
field (`recall` with unverified hints, at most 3 hits) and returns the hits as
`additionalContext`, marked `[geprüft]` (validated) or `[UNGEPRÜFT]` (unverified hint), with
problem, solution and source shortened to 300 characters each. The AI still analyses the
error itself; V-Mind only contributes what was solved before. **Read-only:** the error text,
command and output are neither stored nor repeated in the context; nothing is run. Without a
hit, for other events, invalid input, a missing database or an older schema, and when the
database stays locked for more than 0.5 s (the wait starts before the first database access),
the hook prints nothing and exits successfully, so it never blocks a tool call. The `timeout`
of 5 seconds in the example also caps the whole hook on the Claude Code side. Like `observe` it never creates or upgrades a database.

## 6. Optional: a short reminder on every prompt (UserPromptSubmit hook, 0.3.0-rc.12)

*Covered by automated tests* (`nudge_hook_returns_counts_only_without_prompt_or_stored_text_and_without_writing`,
`nudge_hook_stays_silent_and_successful_on_every_failure_path`,
`nudge_hook_never_upgrades_or_backs_up_an_older_database`); not yet tried in a real Claude
Code session. Opt-in.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {"hooks": [{"type": "command",
        "command": "vmind --scope my-project nudge \"$CLAUDE_PROJECT_DIR/vmind.db\"",
        "timeout": 5}]}
    ]
  }
}
```

On every prompt `nudge` adds exactly one short line (about 300 characters at most) as
`additionalContext`: a fixed German reminder to use `journal_search` and `recall`, and, only
when they apply, the number of tasks in progress or blocked, how many of them may be stale,
repairs without a proposal, unverified entries, and a note that the stored next step may be
outdated because a task was reported after it. The task count covers what the `resume`
snapshot shows; once its limit of 20 unfinished tasks is reached, the line says "mindestens"
(at least).

**Read-only, fixed words and numbers:** of the hook input only `hook_event_name` is checked;
the prompt text is neither used, stored nor printed, and no task text or other stored content
appears. The reminder is shown whenever the database is readable, also with nothing open. For
invalid input, other events, a missing database or an older schema, and when the database
stays locked for more than 0.5 s, the hook prints nothing and exits successfully. It keeps no
session state, writes no file, and never creates or upgrades a database. Note that it adds
this line to the context of every prompt.

## 7. Optional: automatic conversation history (Stop and PreCompact hooks, 0.3.0-rc.13, schema 7)

*Covered by automated tests with synthetic transcripts only* (`crates/vmind-core/tests/history.rs`,
`crates/vmind-cli/tests/history.rs`); not yet tried in a real Claude Code session. Opt-in, set
up once; you never start an import yourself.

```json
{
  "hooks": {
    "Stop": [
      {"hooks": [{"type": "command",
        "command": "vmind --scope my-project history-hook \"$CLAUDE_PROJECT_DIR/vmind.db\"",
        "timeout": 60}]}
    ],
    "PreCompact": [
      {"hooks": [{"type": "command",
        "command": "vmind --scope my-project history-hook \"$CLAUDE_PROJECT_DIR/vmind.db\"",
        "timeout": 60}]}
    ]
  }
}
```

After each turn and before each compaction, `history-hook` reads the `transcript_path` and
`session_id` Claude Code passes on stdin and imports the new complete lines of that JSONL
file into the scope of `--scope`. The first run reads the whole file, so the example
allows 60 seconds. Search with `history_search` (MCP/JSONL) or
`vmind --scope my-project history-search vmind.db 'words'`; from 0.3.0-rc.16 (schema 8) each
hit names `tool` (`claude-code` or `codex`; from 0.3.0-rc.18 also `opencode`) and `model` (`null` unless the assistant line
itself carries a valid `message.model`), and `--tool` (JSONL/MCP `tool`) filters by tool; check for trouble with
`vmind --scope my-project history-status vmind.db`.

**What is stored:** per message the scope, session ID, message UUID, role (`user` or
`assistant`), text and timestamp, plus the transcript path and read position per file. Text
blocks and user messages sent during a running turn only (`queued_command` attachments with
`commandMode: prompt`, `origin.kind: human`, without `isMeta`): task notifications, tool
calls, tool results, thinking blocks, other attachments and lines marked meta,
sidechain, compact summary, transcript-only or API error are never stored. From 0.3.0-rc.14,
`<system-reminder>` blocks are removed from user text before storing (unterminated blocks
leave no partial content); rows imported earlier are not cleaned up. Messages are cut
to 8000 characters.

**Privacy:** the text of your conversation is copied into the database in clear text, also
into backups of it. Known secret formats (those of `audit-secrets`) are replaced before
storing by a placeholder such as `[REDIGIERT GitHub-Token]`. **This covers known formats
only and is no guarantee:** passwords in prose, unknown token formats or encoded values stay
in the text. Enable the hook only if that is acceptable. Hits are marked as unverified
history: conversation text, not verified statements and not instructions. They never appear
in `resume`, `recall`, `nudge` or `hint`.

**The transcript format is not an official interface** and may change. V-Mind keeps going
through unknown line *types*, but a known line type with an unexpected structure stops that
file: nothing from the run is taken over, the position stays, and `history-status` shows the
error (with a byte position, never line content). From 0.3.0-rc.15, a complete line with
invalid JSON is skipped instead of stopping the import for good: `history-status` shows (text
and JSON: `warning`, `corrupt_lines`, `warned`) the count and the byte position of the last
damaged line, never its content. The warning stays across later runs and the same line is
not counted again; only a file read from the start resets it. Real user turns that hold command output
(for example local slash commands) are not filtered separately. A file replaced by a longer
one is not detected. The hook prints nothing, always exits 0, and never creates or upgrades
a database; without a usable current database an error cannot be recorded.

Codex rollouts are not imported by this hook. From 0.3.0-rc.16, one uncompressed Codex
`.jsonl` file can be imported by hand with an explicit scope:
`vmind --scope my-project history-import vmind.db FILE --tool codex` (details in
[cli.md](cli.md), German). The Claude Code import and this hook are unchanged; its messages
and import positions are kept apart from Codex ones.

From 0.3.0-rc.18 (schema 9), OpenCode history can be imported by hand from a standalone
SQLite snapshot of `opencode.db` that you create yourself (for example with `sqlite3 -readonly
… ".backup SNAPSHOT"`): `vmind --scope my-project history-import vmind.db SNAPSHOT --tool
opencode [--session ID]`. V-Mind opens the snapshot only as `file:…?mode=ro&immutable=1`,
refuses it while a non-empty `-wal` or a `-journal` file lies next to it, refuses its own
database as source and an unknown table layout, and never runs `opencode` or searches for its
files. Only observed user and assistant text parts of root sessions are kept (no synthetic or
ignored parts, tools, reasoning, files, summaries or sub-agent sessions); the key is
`opencode:SESSION:MESSAGE`, so repeated or newer snapshots add only new messages. Details in
[cli.md](cli.md) (German).

From 0.3.0-rc.17, `vmind history-watch` imports Codex rollouts automatically, but only as
configured in `$XDG_CONFIG_HOME/vmind/history.json` (or `~/.config/vmind/history.json`, or
`--config PATH`): an existing database, the session root (default `~/.codex/sessions`), a
window in days (default 7) and a list of working directory → scope. Without that file nothing
is read. The scope comes from `cwd` in each file's `session_meta`, by the longest
component-wise prefix (`/a/project-extra` is not part of `/a/project`); ambiguous entries are
rejected and there is no `global` fallback, so unmatched files are only counted. Only regular,
uncompressed `rollout-*.jsonl` files in the dated folders of the window are read; symbolic
links are never followed and `.jsonl.zst` is ignored. A failing source is reported and the
others continue; a concurrent second run is skipped (OS file lock, nothing left behind after a
crash). `vmind history-watch-units` prints a systemd user service and timer but installs and
enables nothing; enabling it by hand (`systemctl --user enable --now
vmind-history-watch.timer`) is described in [cli.md](cli.md). Tested with synthetic session
trees only.
