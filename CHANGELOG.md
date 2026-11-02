# Changelog

## Unreleased (on `main`)

### Added

- `vmind doctor DB`: read-only check of schema version, integrity, foreign keys and
  required tables; never creates or upgrades a database. (#10)
- `vmind backup DB TARGET`: consistent SQLite backup that never overwrites an existing
  file and is verified before it counts as done. (#10)
- Automatic verified backup before every schema upgrade; if it cannot be written or
  checked, the upgrade does not happen. `VMIND_BACKUP_DIR` chooses another folder. (#10)
- `vmind report DB`: readable Markdown project report for people, strictly read-only,
  verified knowledge and unverified proposals in separate sections. (#12)
- English start instructions (`prompts/start.en.md`, `vmind start-prompt en`) with the
  same sections, operations and limits as the German original, checked by a test; German
  stays the default. English Claude Code guide `docs/claude-code.en.md` (MCP, start
  instructions, hooks) that says what is tested. Release packages must contain both.

### Changed

- `resume` no longer lists superseded goals, next steps and task states among the recent
  events; the full history stays in `journal`. Found through the continuity pilot. (#14)

### Experiments

- Continuity pilot with Gemma 4 12B: pre-registered criteria missed, published with all
  raw data and a re-check of every lost point. (#13)
- Retrieval corpus v1 (synthetic, pre-registered, no model): scope, status and withdrawal
  limits held in all 45 queries; exact-wording queries 10/10 at rank 1; longer inflected
  query forms are not found by partial-word search. Report:
  `docs/experiments/abruf-korpus.md` (German).

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
