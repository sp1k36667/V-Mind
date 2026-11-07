# Changelog

## Unreleased: candidate 0.3.0-rc.7 (on `main`)

Not released yet. The source now reports version `0.3.0-rc.7` (`vmind --version`, MCP
server info); there is no tag, no published download and no installation of it. The
earlier candidates `0.3.0-rc.1` to `0.3.0-rc.6` did not yet contain all changes below
(rc.1 lacked #40, #42, #43; rc.2 lacked #44; rc.3 lacked #46; rc.4 lacked #47; rc.5 lacked
#48; rc.6 lacked unverified hints in `recall`).
Development builds made before this change still report `0.2.0` but are not the
released 0.2.0; identify them by commit or SHA-256, not by `--version`.

The next version requires a database migration from schema 5 to 6;
the automatic verified backup from #10 runs first (see "Upgrading" below). Release
acceptance steps: [docs/release-0.3-abnahme.md](docs/release-0.3-abnahme.md) (German).

### Added

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
  corpora: byte-identical). Nothing becomes validated by this.

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
   example `stats`, `resume` or `add`) migrates schema 5 → 6 and first writes a verified
   backup next to the file (or in `VMIND_BACKUP_DIR`); without a verified backup there is
   no migration. `doctor` and `report` only read and never migrate; the `observe` hook
   refuses an old schema instead of upgrading it.
3. Confirm with `vmind doctor vmind.db` that `schema_version` is 6 and the database is
   healthy. Older binaries refuse a schema 6 database.
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
