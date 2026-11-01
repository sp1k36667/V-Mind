# Changelog

## 0.2.0 – unreleased (draft)

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
