# Changelog

## Unreleased: candidate 0.3.0-rc.18 (on `main`)

Not released yet. The source now reports version `0.3.0-rc.18` (`vmind --version`, MCP
server info); there is no tag, no published download and no installation of it. The
earlier candidates `0.3.0-rc.1` to `0.3.0-rc.17` did not yet contain all changes below
(rc.1 lacked #40, #42, #43; rc.2 lacked #44; rc.3 lacked #46; rc.4 lacked #47; rc.5 lacked
#48; rc.6 lacked #53; rc.7 lacked #54; rc.8 lacked the stale-task and open-hint warnings;
rc.9 lacked the journal search; rc.10 lacked retrieval with all terms of long queries;
rc.11 lacked the `nudge` hook; rc.12 lacked the automatic conversation history; rc.13
stored `<system-reminder>` blocks as part of imported user text; rc.14 stopped a history
import permanently at a complete line with invalid JSON; rc.15 lacked the Codex import and
the origin of history messages; rc.16 lacked the configured automatic Codex import; rc.17
lacked the OpenCode snapshot import and schema 9).
Development builds made before this change still report `0.2.0` but are not the
released 0.2.0; identify them by commit or SHA-256, not by `--version`.

The next version requires a database migration to schema 9 (from 5, 6, 7 or 8, step by step);
the automatic verified backup from #10 runs first (see "Upgrading" below). Release
acceptance steps: [docs/release-0.3-abnahme.md](docs/release-0.3-abnahme.md) (German).

### Added in rc.18

- **OpenCode history import from a SQLite snapshot (schema 9):** `vmind --scope NAME
  history-import DB SNAPSHOT --tool opencode [--session ID]` reads a standalone SQLite
  snapshot of OpenCode's `opencode.db` (OpenCode 1.18.15) that the user created; the scope must
  be given explicitly, and `--session` limits the import to one session. V-Mind never searches
  for OpenCode files and never runs `opencode` (`opencode export` writes to the tool database);
  no hook, no timer. The source is opened only as `file:PATH?mode=ro&immutable=1` (path
  percent-encoded), so SQLite creates no `-wal`/`-shm` and writes nothing; a non-empty `-wal`
  or any `-journal` next to the snapshot is refused before opening ("active WAL/journal file,
  please pass a consistent standalone snapshot, e.g. sqlite3 .backup"). The V-Mind database
  itself as source (same canonical path, also via symlink; on Unix also a hard link) is
  refused before the database is opened, so nothing is migrated, recorded or written; on
  Windows paths compare case-insensitively and hard links are not detected (known limit).
  Windows paths (`\\?\C:\…`, `\\?\UNC\…`) become `file:/C:/…` or `file:////server/…`.
  Required tables and columns are checked
  (`session.id/parent_id`, `message.id/session_id/time_created/data`,
  `part.id/message_id/session_id/data`); a missing one, non-JSON `data` or an unknown role
  imports nothing and names the table, column or id (exit 1, recorded in `history-status`).
  Only `text` parts of user and assistant messages in root sessions are kept (a part belongs
  to a message only when both `session_id` and `message_id` match); `synthetic` and
  `ignored` text parts, all other part types (reasoning, tool calls and results, files,
  snapshots, patches, steps, compaction, unknown), the `system` text, compaction summaries
  (`summary: true`), unfinished assistant messages (no `time.completed`) and child sessions
  (`parent_id`, e.g. sub-agents) are skipped. Key `opencode:SESSION:MESSAGE`; repeating the
  same or a newer snapshot adds only new messages. `created_at` from `message.time_created`
  (milliseconds → UTC ISO with milliseconds); `model` = `provider/model` only when the
  message itself names both, else `null`; `tool` = `opencode`. Secrets are redacted as before.
  `history-search` (CLI `--tool`, JSONL/MCP `tool`) accepts `opencode`. Migration 0009 rebuilds
  both history tables only to allow the new tool name; ids, search index, warnings and import
  state are kept, after the verified backup. Tested with synthetic snapshots only; the layout of
  `data` and the millisecond unit of `time_created` are derived from the export format, not
  confirmed against a real database. Hermes is not included.

### Added in rc.17

- **Configured automatic Codex import (`history-watch`):** `vmind history-watch [--config
  PATH]` runs once over the Codex sessions as configured in `$XDG_CONFIG_HOME/vmind/history.json`
  (otherwise `~/.config/vmind/history.json`; JSON, no new dependency): an existing database,
  the session root (default `~/.codex/sessions`), a window in days (default 7) and a list
  `cwd` → scope. Without a configuration file no source is read and the run ends with
  `not_configured` (exit 0). Each file's scope comes from `cwd` in its first line
  (`session_meta`), matched component-wise by the longest prefix (`/a/project-extra` does not
  belong to `/a/project`); equal paths with different scopes are rejected as ambiguous, and
  there is no `global` fallback: unmatched files are only counted. Only the dated folders
  `YYYY/MM/DD` from today − N to today + 1 (UTC) are scanned, and only regular, uncompressed
  `rollout-*.jsonl` files inside the root; symbolic links are never followed (files, day,
  month or year folders), a linked root is rejected, `.jsonl.zst` is ignored. Import uses the
  incremental rc.16 Codex import; an error in one source is reported (summary and
  `history-status`) and the others continue. A run holds an OS file lock (`flock`) on the
  configuration file; a second concurrent run is skipped with `locked` and exit 0, and
  nothing is left behind after a crash. Summary: sources, imported, new messages, skipped,
  unassigned, failed, ignored. `vmind history-watch-units [--config PATH] [--interval
  MINUTES] [--output DIR] [--vmind PATH]` prints (or writes, never overwriting) a systemd user
  service and timer; it installs and enables nothing. No schema change. Tested with
  synthetic session trees and synthetic unit files only; not tested with real Codex sessions
  or a real systemd.

### Added in rc.16

- **Codex history import and message origin (schema 8):** `vmind --scope NAME
  history-import DB FILE --tool codex` imports exactly one uncompressed Codex rollout
  `.jsonl` file incrementally; the scope must be given explicitly (`--scope` or
  `VMIND_SCOPE`). Only `event_msg/item_completed` is read: `UserMessage` with a non-empty
  `client_id` (text blocks only; the documented context envelopes `<app-context>` and
  `<in-app-browser-context …>`, also with attributes, are removed with all nested content,
  counting nesting per tag name; an unterminated envelope drops the text from its tag on;
  other tags stay; no general filter on a leading `<`) and synchronous
  `AgentMessage` with phase `final_answer` (`Text` blocks). Commentary, async messages,
  `response_item`, tools, context and compaction are skipped. The session comes from
  `session_meta`; the key is `item.id`, `ordinal` only as a separate fallback, and messages
  with neither are skipped and counted (`unkeyed_lines`) without raw text. Each message stores
  `tool` (`claude-code` or `codex`) and `model`; for Codex only when a `turn_context` with
  the same `turn_id` names exactly one model, for Claude Code only from the assistant line
  itself, otherwise `null`. Deduplication and the import position are separate per tool, also
  for the same path. `history-search` (CLI `--tool`, JSONL/MCP `tool`) shows `tool` and
  `model` and can filter; without a filter it behaves as before in the exact scope. The
  default tool stays `claude-code`, so the existing Claude path and the `history-hook` are
  unchanged. **Not included:** automatic Codex import (no scan of `~/.codex`, no mapping of
  working directories to scopes, no hook, no timer) is an explicit follow-up step; `.jsonl.zst`
  files are not read. Migration 0008 rebuilds both history tables, keeps ids, the search
  index and warnings, and marks existing rows `claude-code`. Tested with synthetic files only.

### Fixed

- **Damaged history lines no longer stop the import for good:** a complete,
  newline-terminated line with invalid JSON is skipped. The count and the byte position of the
  last damaged line are stored with the valid messages and the position in one transaction,
  never the line content, and appear in `history-status` (text and JSON). The warning stays
  across later runs without new data and the same line is not counted twice. An incomplete
  last line still waits; valid JSON with an unknown structure still stops the file; the line
  size limit is unchanged. No schema change.
- **Conversation history no longer takes over system reminders:** `<system-reminder>` blocks
  inserted into imported user text (including `queued_command` messages) are removed before
  redaction, storing and indexing; a message with nothing left is not stored and the import
  continues. An unterminated block is dropped from its opening tag on, a closing tag without
  a start drops the text before it. Assistant text is unchanged. **Rows imported earlier stay
  as they are: existing databases are not cleaned up.**

### Added

- **Automatic conversation history (schema 7):** after being switched on once via Claude
  Code's Stop and PreCompact hooks, `vmind history-hook DB` imports new transcript lines
  incrementally; no import is ever started by hand. Only user and assistant text is stored, including user messages queued during a turn;
  tool calls and results, thinking and meta or sidechain lines are not. Known secret formats
  are replaced before storing (known formats only, no guarantee), messages are cut to 8000
  characters, repeats are removed by message UUID. An unexpected line structure stops the
  file visibly in `vmind history-status DB`. `vmind history-search DB TEXT [--limit N]` and
  JSONL/MCP `history_search` read one scope only and mark hits as unverified history; they
  never appear in `resume`, `recall`, `nudge` or `hint`. `vmind history-import DB FILE` is
  a test and repair tool. The transcript format is not an official interface. Tested with
  synthetic transcripts only, not yet in a real Claude Code session.
- `vmind doctor DB`: read-only check of schema version, integrity, foreign keys and
  required tables; never creates or upgrades a database. (#10)
- `vmind backup DB TARGET`: consistent SQLite backup that never overwrites an existing
  file and is verified before it counts as done. (#10)
- Automatic verified backup before every schema upgrade; if it cannot be written or
  checked, the upgrade does not happen. `VMIND_BACKUP_DIR` chooses another folder. (#10)
- `vmind report DB`: readable Markdown project report for people, strictly read-only,
  verified knowledge and unverified proposals in separate sections. (#12)
- **Observations (schema 6):** `vmind observe DB` for Claude Code hooks records only
  session, call id, tool (Bash/Edit/Write), result and project-relative paths, never
  commands, output, error text or file contents, in its own table `observations`.
  `resume` and `report` summarise the last three sessions as "observed, not checked";
  a completed call is not a passed test. The hook never creates or upgrades a database.
  Not yet tried in a real Claude Code session with an installed release. (#15)
- Retrieved knowledge carries the evidence of its active check: `none`, `not_run`,
  `passed`, `failed` or `error`, with time and the last pass/fail verdict of the same
  definition, in CLI, report, JSONL, MCP and the local model prompt. Retrieval runs no
  commands; an old `passed` is no proof for today's code. (#23)
- English start instructions (`prompts/start.en.md`, `vmind start-prompt en`) with the
  same sections, operations and limits as the German original, checked by a test; German
  stays the default. English Claude Code guide `docs/claude-code.en.md` (MCP, start
  instructions, hooks) that says what is tested. Release packages must contain both. (#28)
- Release packages contain the changelog, guides, prompts and examples the READMEs link
  to. Each platform build extracts its own archive and smoke-tests links, help,
  init, persistence across processes, doctor, backup and restore. (#24)
- `vmind audit-secrets DB`: explicit read-only search for known secret formats across
  supported schema versions. Reports numeric locations and format types, never values;
  rejects incomplete required schemas. Heuristics may miss secrets or flag examples;
  an empty result is no secrecy guarantee. No deletion or write blocking. (#29)
- `vmind recall DB TEXT --limit N` (1 to 20, as in JSONL and MCP); the default stays 5. An
  invalid limit is rejected before the database is opened. (#40)
- `recall` finds other word forms: after the existing full-text and partial matches, word
  stems ("Zertifikate" → `zertifikat*`) fill only the remaining places. Existing hits and
  their order are unchanged; scope, status and withdrawal filters apply as before; accents
  match in both directions. Retrieval corpora: longer word forms 0/10 → 9/10 and separated
  word pairs 1/7 → 6/7 at rank 1, no previous hit lost in 82 queries, 6 extra unrelated
  hits. (#43)
- `vmind journal-mode DB wal|delete`: explicit switch of SQLite's journal mode with a
  verified backup first; never automatic, new databases keep the default `delete`. Fails
  with a clear message and keeps the mode if another process uses the file. `vmind doctor`
  reports the journal mode. Read-only tools, backup and doctor work on WAL databases also
  after all connections are closed; the `-wal`/`-shm` files get the database's permissions.
  In a two-writer load test WAL took 8–9 s instead of 32–34 s. (#44) On Linux `ntfs3` two
  processes starting at once on a WAL database without a `-shm` file often failed with "disk
  I/O error" (70 of 200 opens, ext4 0 of 200); keep the default `delete` there and on network
  drives (documented in `docs/cli.md`).
- Repair proposals: `vmind repairs DB` (also JSONL/MCP `repairs`) lists, read-only, check
  commands of visible entries that failed and passed in the directly following run.
  `vmind propose-repair DB RUN PROBLEM SOLUTION` (`propose_repair`) stores exactly one
  `pending` entry per repair in the caller's scope (also for a global check; global only
  when called in `global`), with problem and solution from the caller and a source V-Mind
  builds from the IDs; no check output or command is copied and nothing is validated.
  Concurrent calls create no second entry. The source deduplicates but is no tamper-proof
  evidence. V-Mind only sees checks on its own entries, not a project's other tests. (#46)
- `resume` (CLI, JSONL, MCP, local model context) and `report` show `open_repairs`: the true
  number of visible repairs without a proposal in the scope and at most three newest failed
  run IDs, with a hint to `propose-repair`. IDs only, read-only. (#47)
- `vmind check` and `revalidate` name a repair at the moment it happens: when a run passes
  directly after a failure of the same active check, the output shows the run IDs and the
  `propose-repair` call (JSON `repair` / `repairs`), unless the scope already has a proposal.
  Read-only; if the hint cannot be computed, the stored run and its result stay unchanged. (#48)
- `recall` (CLI, JSONL, MCP, local model context) also returns unverified (`pending`) entries
  as hints, only in places left free after all validated search stages, marked in every
  output and kept apart in the model context. Validated hits and their order are unchanged;
  `--validated-only` / `validated_only: true` gives exactly the previous result (retrieval
  corpora: byte-identical). Nothing becomes validated by this. (#53)
- `vmind hint DB`: opt-in Claude Code hook for `PostToolUseFailure`. It searches with the
  failed call's error text and returns matching knowledge (validated and unverified, marked,
  at most 3 hits) as additional context, so the AI gets earlier solutions without having to
  think of `recall`. Read-only; the error text, command and output are not stored or
  repeated. Any problem (no hit, invalid input, missing or older database, lock longer than
  0.5 s) ends silently and successfully. Not yet tried in a real Claude Code session. (#54)
- `resume` (CLI, JSONL, MCP, local model context) and `report` warn about stale state:
  `stale_tasks` lists shown tasks whose last status `in_progress` or `blocked` is at least two
  full days old (marked in the text output), and `open_hints` gives the number and newest IDs
  of active unverified entries in the exact scope. Read-only; missing, invalid or future
  timestamps never fail `resume` or warn.
- Journal search: `vmind journal-search DB QUERY [--limit N]`, JSONL operation and MCP tool
  `journal_search`. Read-only search in the project journal of exactly one scope (never
  `global` or other scopes, unlike `recall`). An entry matches when every word of the query
  occurs in its body, source or task key; partial words count, case is ignored (umlauts
  included), accents are not folded (`é` ≠ `e`). Newest first, limit 1 to 20 (default 5),
  checked before the database is opened. Linear scan without an index that stops after
  `limit` matches. The start instructions describe what a good journal entry contains and
  the retrieval order `resume` → `journal_search` → `recall` → `get`/`show`.
- `vmind nudge DB`: opt-in Claude Code hook for `UserPromptSubmit`. Adds one short line of
  context: a fixed reminder to use `journal_search` and `recall`, plus counts of tasks in
  progress or blocked ("mindestens" when the snapshot limit is reached), possibly stale
  tasks, repairs without a proposal, unverified entries, and a note when the stored next
  step is older than the newest task. Fixed words and numbers only: the prompt text is
  neither used, stored nor printed, and no stored text appears. Read-only; every failure
  path exits silently with status 0. Covered by automated tests, not yet tried in a real
  Claude Code session.

### Changed

- `resume` no longer lists superseded goals, next steps and task states among the recent
  events; the full history stays in `journal`. Found through the continuity pilot. (#14)
- New database files are created readable only by their owner (0600) on Linux and macOS;
  existing files keep their permissions. On Windows the folder permissions apply. (#16)
- Validation errors show only V-Mind's message, without SQLite's misleading
  "Invalid parameter name:" prefix, in CLI, JSONL and MCP. (#17)

### Fixed

- A relative database or backup name shaped like a SQLite URI (`file:...?mode=rw`) could
  redirect a backup onto an existing database. Persistent file names are now always
  taken literally by CLI, JSONL, MCP, hook, doctor and backup. (#22)
- Two processes writing continuously could make one writer fail with "database is
  locked". Single writes outside an explicit transaction are now retried a few times;
  load test 72,000 writes without error or duplicate (before: 6 errors in 24,000). (#42)
- Creating a conversation while another process held a read lock could report a new
  conversation id although nothing was stored. The id is now generated first and the
  insert reports commit errors. (#42)
- Long queries now use all terms instead of only the first 24. The ranking of long
  queries can change: a mixed sample showed gains but also shifts (for one task two
  previously shown hints dropped out, for another an off-topic one was added). Queries of
  up to 24 terms are unchanged.

### Experiments

- Continuity pilot with Gemma 4 12B: pre-registered criteria missed, published with all
  raw data and a re-check of every lost point. (#13)
- Retrieval corpus v1 (synthetic, pre-registered, no model): scope, status and withdrawal
  limits held in all 45 queries; exact-wording queries 10/10 at rank 1; longer inflected
  query forms are not found by partial-word search. Report:
  `docs/experiments/abruf-korpus.md` (German). (#26)
- Continuity follow-up with all 80 runs: fewer stale next steps in answers, no gain in
  overall accuracy. (#21)
- Stem-based partial search (#27) is not part of this version: it missed one of its
  pre-registered criteria and showed new weaknesses.
- Transfer pilot with Gemma 4 12B (pre-registered, 170 calls, frozen at `970d2dd`): one
  correct lesson in the prompt did not pass its criteria (target check 2/40 → 13/40,
  placebo 10/40; counter-case limit formally violated). Post hoc, the targeted error
  vanished with the lesson, but an unrelated naming error dominated. Report:
  `docs/experiments/transfer-pilot.md` (German). (#35)
- R1 repair pilot with Gemma 4 12B (pre-registered, 108 calls, frozen at `defea2d`): pilot
  thresholds missed (fully repaired 7/36 without hint, 6/36 unrelated text, 9/36 V-Mind hints).
  Retrieval 25 correct, 11 correctly empty, 0 wrong. Post hoc: for the JSON-key error the target
  check passed 0/8 without and 8/8 with the hint. Report: `docs/experiments/r1.md` (German).

### Upgrading

1. Stop all clients that use the database (MCP server, `serve`, hooks, scripts).
2. Install the new binary. The first command that opens the database normally (for
   example `stats`, `resume` or `add`) migrates to schema 9 and first writes a verified
   backup next to the file (or in `VMIND_BACKUP_DIR`); without a verified backup there is
   no migration. `doctor` and `report` only read and never migrate; the `observe` and
   `history-hook` hooks refuse an old schema instead of upgrading it.
3. Confirm with `vmind doctor vmind.db` that `schema_version` is 9 and the database is
   healthy. Older binaries refuse a schema 9 database.
4. Restart MCP clients so they use the new binary.

## 0.2.0 – 2026-11-01

First tagged release. Requires a database migration to schema 5; back up `vmind.db`
before the first start of the new version (see "Upgrading").

### Added

- **MCP server** (`vmind mcp DB`): the same operations as the JSONL protocol, over stdio
  for Claude Desktop, Claude Code and other MCP clients. There is no validate tool;
  validation stays outside the model. (#1)
- **Check commands** (schema 4): `check-set` stores a fixed command for an entry,
  `check` runs it, `revalidate` runs all checks in a scope. A passing check validates a
  pending entry with command, exit code and duration as evidence; a failing check on a
  validated entry is only reported unless `--invalidate` is given. Commands run without
  a shell, in a fixed directory, with a time limit. (#2)
- **Partial-word search** (schema 5): recall also finds inflected and compound words
  (for example "Migration" in "Schemamigrationen"). Whole-word hits rank first; scope
  and status filters apply unchanged. (#7)
- **Prebuilt binaries** for Linux x86_64, macOS arm64 and Windows x86_64 with SHA-256
  checksums, built from a version tag. SQLite is bundled, so `libsqlite3-dev` is no
  longer needed. (#5)

### Changed

- `resume` output is about one third smaller without truncating any text. (#6)
- English is the main README; German moved to `README.de.md`. (#4)

### Fixed

- A check whose process exits but leaves a child holding the output open could exceed
  the time limit and still count as passed. The time limit now also covers reading the
  output; exceeding it is an error and never validates an entry. Known limit: the
  lingering child process is not terminated. (#8)

### Experiments

- Learning-curve experiment with Gemma 4 E2B (pre-registered) and 12B (exploratory):
  hypotheses not supported. Report: `docs/experiments/lernkurve.md` (German). (#3)

### Upgrading

1. Stop all clients that use the database (MCP server, scripts).
2. Back up: `sqlite3 vmind.db ".backup vmind-before-0.2.0.db"` and check the copy with
   `sqlite3 vmind-before-0.2.0.db "PRAGMA integrity_check"`.
3. Install the new binary. The first command migrates schema 4 → 5 automatically.
4. Confirm with `vmind stats vmind.db` that `schema_version` is 5.
