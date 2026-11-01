# V-Mind

**English** · [Deutsch](README.de.md)

[![Rust checks](https://github.com/sp1k36667/V-Mind/actions/workflows/ci.yml/badge.svg)](https://github.com/sp1k36667/V-Mind/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**A verifiable memory for AI that survives restarts.**

AI assistants forget everything after each session, and sometimes state wrong things with
confidence. V-Mind is a small local store (Rust + SQLite) where an AI can keep two things
and find them again later:

1. **Verified knowledge:** solved errors and proven solutions, each with a source and
   evidence. New knowledge starts out *unverified* and only becomes valid after a real check.
2. **Project memory:** goal, tasks, decisions, next step and conversation history, so an AI
   knows where the work stands, even in a brand-new session.

V-Mind is model-agnostic. It works as an **MCP server** (e.g. with Claude), from the command
line, through a simple JSONL protocol, and with local models via Ollama.

> Status: experimental prototype, version 0.2.0, MIT license. What is built and how it was
> tested: [project status](#project-status-what-is-built-and-how-it-was-tested). Detailed
> docs, CLI help texts and the AI start prompt are currently in German.

## What makes V-Mind different

Most AI memories store whatever the model considers important. V-Mind strictly separates
*assumed* from *verified*:

```
  propose / add            validate (human/CLI, with evidence)       invalidate
 ───────────────▶ pending ─────────────────────────────────▶ validated ──────────▶ invalidated
                  never retrieved                             retrieved             never retrieved again,
                                                                                    history is kept
```

- **Only validated knowledge** is retrieved, always with source, reviewer and evidence.
- **Through MCP, an AI can only propose knowledge.** Approval is deliberately not offered
  as an MCP tool, only on the command line or through an executable check. An AI that can
  also run shell commands can call that command line too; see
  [Trust, privacy and backups](#trust-privacy-and-backups).
- **V-Mind's commands never silently overwrite.** Outdated entries are withdrawn; every
  change made through V-Mind stays traceable in the history.
- **Scopes** (`--scope`) keep projects apart; the `global` scope applies to all of them.
- **Fully local:** one SQLite file, no cloud service, no GPU required.

**The idea behind it: learning across runs, without training.** A model finds an error
through a real test, fixes it, and proposes the lesson. Once a check confirms it, later
runs can retrieve it. Whether that makes a model avoid the mistake on *new* tasks is not
shown yet; our experiments so far did not find a learning curve (see below). What works
today is reliable continuation of projects and reuse of verified solutions.

In V-Mind, a stored lesson is not used until a person or an executable check has
confirmed it, and the confirmation is kept with the entry.
[How this relates to other approaches (German)](docs/design.md#abgrenzung-zu-ähnlichen-ansätzen).

## What is it for?

- **Coding with AI:** solved errors and proven solutions stay available, also for other models.
- **Long-running projects:** after every restart the AI knows what is done and what comes next.
- **Turning small local models into specialists:** a general model plus verified domain
  knowledge, e.g. for science, with sources and without training. This is a hypothesis so
  far; [opportunities and limits (German)](docs/design.md#spezialisierung-kleiner-lokaler-modelle).

## Is it useful today? An honest answer

**Yes, for one thing: keeping an AI's project state reliable across sessions and between
different AI tools. The bigger promise, that an AI learns from experience, is not proven.**

What works in daily use, not only in tests:

- **Continuing a project after a restart.** A session-start hook hands the AI the goal, open
  tasks and decisions, so it picks up where it stopped. V-Mind is developed this way itself.
- **Two different AIs sharing one working state.** Claude and Codex coordinated the work on
  V-Mind through a V-Mind conversation, with almost 70 messages, handovers and mutual
  reviews. Normally two AI tools know nothing about each other.
- **Knowledge with provenance.** An entry only counts after a test or a person confirmed
  it, and you can always see who confirmed it, when and how.
- **Solid basics:** local, one file, automated tests, verified backups before every
  upgrade, ready-made programs for Linux, macOS and Windows.

What is not there yet:

- **Learning is not shown.** Our experiments found no learning curve on new tasks.
- **Continuation by a small local model is not shown either.** In our test, Gemma 4 12B
  did worse with `resume` than with the same data as a plain list; the main cause is fixed,
  the follow-up test has not run yet.
- **Logging still depends on the AI.** It has to remember to record what it did; automatic
  logging through a Claude Code hook is built but not merged.
- **Search finds words and word parts, not meanings.** Most detailed docs are in German.

**In short:** if you work with Claude Code or similar tools on longer projects, V-Mind is
useful today to make continuing and handing over work more reliable and traceable. It is
not yet a finished product for a broad audience.

## Project status: what is built and how it was tested

*As of 1 November 2026.* Every point below comes with the test or check behind it. Open
questions are listed as open.

**Released: [version 0.2.0](https://github.com/sp1k36667/V-Mind/releases/tag/v0.2.0)**
with ready-made programs for Linux x86_64, macOS arm64 and Windows x86_64 and SHA-256
checksums. Contents: MCP server, check commands with `revalidate`, partial-word search,
compact `resume`, bundled SQLite. See the [changelog](CHANGELOG.md).

**On `main` since 0.2.0, not released yet:**

| Feature | What it does |
|---|---|
| `vmind doctor DB` | Read-only check of schema, integrity, foreign keys and required tables |
| `vmind backup DB TARGET` | Verified SQLite backup that never overwrites an existing file |
| Automatic backup before upgrades | Every schema upgrade first writes and verifies a backup; if that fails, nothing is changed |
| `vmind report DB` | Readable Markdown report for people; strictly read-only, verified knowledge and unverified proposals kept apart |
| Cleaner `resume` | Superseded goals, next steps and task states no longer appear next to the current ones |

**Automated tests:** 75 tests run on every change in GitHub Actions on Linux, together with
Clippy (all warnings are errors) and a formatting check; macOS and Windows builds are
checked too. Among other things they cover:

- upgrades from older schemas without data loss, and failed upgrades that leave the
  database untouched;
- backups that never overwrite, and an automatic backup whose failure blocks the upgrade;
- 16 separate processes writing at the same time without losing an entry;
- check commands: no shell, time limit also while reading output, a timeout or error never
  validates an entry;
- scope and status filters for every search path, including partial-word search;
- the MCP and JSONL protocols, including malformed and oversized input;
- `report` leaving the database byte for byte unchanged, also on an older schema.

**Checked by hand:** the published Linux download (checksum and first start); the upgrade of
a real project database from schema 4 to 5 with a verified backup, integrity check and
matching row counts; installation from the release on a fresh user profile without Rust or
SQLite tools.

**Test list: all experiments, done and planned** (details below, all raw data in the
repository):

| # | Question | Model | Status | Result |
|---|---|---|---|---|
| 1 | Does a stored, verified solution help a small model? | Gemma 4 E2B | done | Yes for reuse of the same solution (7/7 instead of 2/7 checks); says nothing about learning. [Report](docs/experiments/e2b-pilot.md) |
| 2 | Does a model get better from its own checked lessons? | Gemma 4 E2B | done, pre-registered | No learning curve; 0 of 108 task runs solved; about one in five unchecked lessons clearly wrong. [Report](docs/experiments/lernkurve.md) |
| 3 | Same question as 2 | Gemma 4 12B | done, exploratory | No learning curve either, but 12B fixed errors itself and its unchecked lessons were rarely wrong. [Report](docs/experiments/lernkurve.md#explorativer-lauf-mit-gemma-4-12b) |
| 4 | Can a fresh session continue a project from `resume`? | Gemma 4 12B | done, pre-registered | Criteria missed: 117/165 vs. 133/165 for the same data as a flat list; cause found and fixed. [Report](docs/experiments/continuity-pilot.md) |
| 5 | Does the fix help, and does the format matter? | Gemma 4 12B | pre-registered and frozen, not run yet | – [Plan](https://github.com/sp1k36667/V-Mind/blob/exp/continuity-2x2/docs/experiments/continuity-2x2-plan.md) |
| 6 | Does one correct, verified lesson help on *new* tasks? | Gemma 4 12B | draft | – [Draft](docs/experiments/transfer-pilot-plan.md) |

New experiments use **Gemma 4 12B only**. In tests 2 and 3, 12B fixed its own errors far more
often and wrote far fewer wrong lessons than E2B, so it is the better basis for testing
whether lessons help at all. Test 6 starts with a hand-written correct lesson: if even that
does not help, self-written lessons cannot be the answer.

**In progress** (open pull requests, under review): observing Claude Code tool calls through
a hook (only tool, result and project path; never commands, output or file contents), new
database files readable only by their owner, clearer error messages, and the follow-up
continuity test. [Open pull requests](https://github.com/sp1k36667/V-Mind/pulls).

**How it is developed:** the maintainer sets goals and priorities. Two AI assistants, Claude
(Anthropic) and Codex (OpenAI), write and review the code. Only one of them writes code at a
time; the other reviews every change and re-checks reported numbers independently. They
coordinate through a V-Mind conversation, so V-Mind is used to build V-Mind.

## Use it with Claude (Claude Desktop / Claude Code)

With V-Mind as an MCP server, Claude loads the project state at startup, looks up verified
knowledge before making changes, and records finished work in the project journal. This
works in the **Code tab of the Claude desktop app** and in **Claude Code in the terminal**.

### 1. Install V-Mind

**Option A: download** a ready-made program for Linux, macOS or Windows from the
[Releases page](https://github.com/sp1k36667/V-Mind/releases), unpack it and put `vmind`
(`vmind.exe` on Windows) somewhere on your `PATH`. SQLite is built in; nothing else is
needed. `SHA256SUMS.txt` lists the checksums. The programs are not code-signed; on macOS
you may have to allow it once with `xattr -d com.apple.quarantine vmind`.

**Option B: build from source.** Requirements: Rust/Cargo, Git and a C compiler (SQLite is
compiled in). On Ubuntu `sudo apt install build-essential`, then:

```sh
git clone https://github.com/sp1k36667/V-Mind.git
```

```sh
cargo install --path V-Mind/crates/vmind-cli --locked
```

The `vmind` command is now available (`vmind --help` lists all commands).

### 2. Create a database in your project

In the folder of the project Claude should work on:

```sh
vmind init vmind.db
```

The database is local and does not belong in the Git repository (`*.db` in `.gitignore`).

### 3. Register the MCP server

Create a `.mcp.json` file in the project folder. Replace `my-project` with a name for the
project scope:

```json
{
  "mcpServers": {
    "vmind": {
      "command": "vmind",
      "args": ["--scope", "my-project", "mcp", "vmind.db"]
    }
  }
}
```

Alternatively with the Claude Code CLI, only for you and this project:

```sh
claude mcp add vmind -- vmind --scope my-project mcp vmind.db
```

### 4. Restart Claude and approve the server

The next time a session starts in the project, Claude asks whether the `vmind` server may
be used. After that Claude has these tools:

| Tool | Purpose |
|---|---|
| `resume` | Load project state: goal, tasks, decisions, next step |
| `recall` | Find verified knowledge via full-text search |
| `get` | Show an entry with its full history, active check and recent check runs |
| `propose` | Propose a new lesson as *unverified* |
| `log` | Record a task, decision, next step or note |
| `journal` | Read the project journal page by page |
| `pending`, `stats` | Show unverified entries and counts |
| `session_new`, `sessions`, `message`, `messages` | Store and read conversations |

**Claude desktop app, chat (outside the Code tab):** chat sessions do not read
`.mcp.json`. Add the server to `claude_desktop_config.json` (Settings → Developer → Edit
Config; on macOS `~/Library/Application Support/Claude/`, on Windows `%APPDATA%\Claude\`)
and use **absolute paths**, because the app does not start in your project folder. This is
a manual example; we have not tested it on every platform yet:

```json
{
  "mcpServers": {
    "vmind": {
      "command": "/absolute/path/to/vmind",
      "args": ["--scope", "my-project", "mcp", "/absolute/path/to/project/vmind.db"]
    }
  }
}
```

**Check the setup.** In a terminal in the project folder:

```sh
vmind --scope my-project stats vmind.db
```

It should print the schema version and counts. If Claude does not list the `vmind` tools:

| Symptom | Likely cause and fix |
|---|---|
| Server fails to start, "command not found" | `vmind` is not on the `PATH` of the app. Use the absolute path to the program in `command`. |
| Server fails to start, database not found | The server only opens an existing database and never creates one because a path was mistyped. The path in `args` is relative to the folder the app starts in. Use an absolute path, or run `vmind init` there first. |
| No approval prompt in Claude Code | Check the server state with `/mcp`; if the project server was declined, reset its approval choices with `claude mcp reset-project-choices` and start a new session. See the [official Claude Code MCP documentation](https://code.claude.com/docs/en/mcp). |
| Old behaviour after an update | A running MCP server keeps the old program until Claude is restarted. Restart Claude after installing a new version. |

### 5. Optional: load the project state automatically

A SessionStart hook hands Claude the project state right at session start, without Claude
having to remember to ask. File `.claude/settings.local.json` in the project folder
(personal, do not commit it):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "vmind --scope my-project resume \"$CLAUDE_PROJECT_DIR/vmind.db\""
          }
        ]
      }
    ]
  }
}
```

Development version after 0.2.0 (schema 6): Claude Code can also report every Bash, Edit
and Write call through a `PostToolUse` hook to `vmind observe`. V-Mind then keeps only the
tool, whether it completed or failed, and the project-relative file path; never commands,
output, error text or file contents. `resume` shows the last three sessions in summary,
marked as observed, not verified. Setup and limits (German):
[docs/cli.md](docs/cli.md#beobachtungen-aus-claude-code-ab-schema-6).

### 6. Get started

Tell Claude, for example:

- "Load the project state from V-Mind and continue with the next step."
- "Record in V-Mind what you finished, with the test result as evidence."
- "Propose the fix for this error to V-Mind as an unverified entry."

You approve knowledge yourself after you have really tested the solution:

```sh
vmind pending vmind.db
```

```sh
vmind validate vmind.db 1 'Your name' 'Which test ran and what the result was'
```

Or let a real test decide, see the next section.

To see where the project stands without asking an AI, `vmind --scope my-project report
vmind.db` prints a readable Markdown report: goal, next step, tasks, recent decisions,
verified knowledge with its last check, and unverified proposals listed separately
(development version after 0.2.0).

### Checks: tests decide what counts

An entry can get an executable **check**, for example the test that found the error. If it
passes, an unverified entry becomes valid automatically, with command, exit code and
duration as evidence. This is the core of the learning loop: the AI proposes, the test
decides.

```sh
vmind check-set vmind.db 1 'Your name' . pytest tests/test_app.py -k corrupt
```

```sh
vmind check vmind.db 1
```

`revalidate` re-runs all checks of a scope, for example after an update. If a valid entry
fails, it is reported. It is only withdrawn with `--invalidate`, because withdrawal is
permanent:

```sh
vmind --scope my-project revalidate vmind.db
```

Security: checks run without a shell (no `;`, `&&` or redirects), in a fixed directory and
with a timeout. Setting and running checks is **only possible from the command line**, not
via MCP, so an AI that only has the MCP tools cannot store a command in V-Mind. Read a check
before you set it, like any command you are about to run. Make sure a check really tests
something: `cargo test` with a mistyped test name runs zero tests and still reports success.
Details (German): [docs/cli.md](docs/cli.md#prüfbefehle).

The same applies to other MCP-capable programs: server command
`vmind --scope SCOPE mcp /absolute/path/vmind.db`. Where the configuration lives depends on
the program. Technical details (German): [docs/protocol.md](docs/protocol.md).

## Other ways to use V-Mind

**Command line:** store, verify and retrieve knowledge, and keep the project journal.

```sh
vmind --scope my-project recall vmind.db 'SQLite migration'
```

```sh
vmind --scope my-project task vmind.db database done 'Migration implemented' 'cargo test: all tests passed'
```

**Local models via Ollama:** `ask` retrieves matching knowledge and the project state and
sends the question to a local model (default: Gemma 4 E2B, see `setup/Modelfile`). Answers
are stored, but never automatically turned into knowledge.

```sh
vmind --scope my-project ask vmind.db 'How do I prevent missing tables on first start?'
```

**JSONL protocol:** `vmind serve vmind.db` processes one JSON object per line over
stdin/stdout, for your own programs without MCP. See [docs/protocol.md](docs/protocol.md).

All commands, the workflow for long projects, configuration and limits are described in
detail in **[docs/cli.md](docs/cli.md)** (German).

## First experiment: does verified knowledge help a small model?

The small local model Gemma 4 E2B had to build a Python task planner, once without and once
with V-Mind. The store contained a solution previously generated and verified with Gemma 4
12B. Task, settings and checks were identical.

| Result | Without V-Mind | With V-Mind |
|---|---:|---:|
| Independent functional checks | 2 of 7 | 7 of 7 |
| Model's own test suite at the end | not runnable | 10 of 10 |
| Model time, both attempts combined | 46.5 s | 17.1 s |

**Honest assessment:** this shows that a small model can reliably reuse a stored, verified
solution. The output was byte-identical to the reference. It does *not* show that the model
learns or solves new tasks.
[Setup, measurements and limits (German)](docs/experiments/e2b-pilot.md).

## Second experiment: does a model improve from its own checked lessons?

Over a series of six *different* tasks, the model stored the errors it fixed as lessons.
In condition B a lesson counted only after a passing check, in C it counted unchecked.
**Result: no learning curve.** Gemma 4 E2B (pre-registered) solved none of 108 task runs;
the hypotheses are not supported. Gemma 4 12B (exploratory) solved some tasks but showed no
improvement from checked lessons either.

What the runs did show: unchecked memory collects wrong lessons when the model is weak
(about one in five sampled E2B lessons was clearly wrong), and confirming a lesson with
"the check that failed before now passes" is too coarse, because one fix often flips many
checks at once. A smaller follow-up that measures transfer of a single verified lesson is
drafted but not run.
[Report (German)](docs/experiments/lernkurve.md),
[follow-up draft (German)](docs/experiments/transfer-pilot-plan.md).

## Third experiment: can a fresh session continue a project?

This tests what V-Mind is mainly used for. Gemma 4 12B answered eleven fixed questions about
three synthetic projects (current goal, task states, the replaced backend decision, the
next step, two questions with no answer in the data), in 45 pre-registered runs: without any
history, with the same data as a flat field list, and with V-Mind's `resume` output.

| | No history | Flat list | V-Mind `resume` |
|---|---:|---:|---:|
| Correct answers (strict, of 165) | 6 | 133 | 117 |

**Result: the pre-registered criteria were missed**, and the result is published as is.
Re-checking the raw answers showed where the 16 points went: 7 were real errors, because
`resume` showed old "next step" entries next to the current one and the model sometimes
picked an old one; most of the rest were correct facts in the wrong form (a quoted folder
with a trailing full stop, "Backend SQLite" instead of "SQLite"). The old entries are now
filtered out of `resume`. A follow-up that separates this fix from the presentation format
is pre-registered with new projects and seeds, but has not been run yet.
[Report (German)](docs/experiments/continuity-pilot.md),
[follow-up plan (German)](https://github.com/sp1k36667/V-Mind/blob/exp/continuity-2x2/docs/experiments/continuity-2x2-plan.md).

## Trust, privacy and backups

**What V-Mind guarantees:** only entries marked *validated* are retrieved; every
validation, withdrawal and check run made through V-Mind is recorded with who, when and
with what evidence; V-Mind's commands never silently overwrite; a failed migration leaves
the database unchanged. These guarantees cover V-Mind's own commands. A program that writes
to the SQLite file directly bypasses them, and the history itself is not tamper-proof.

**What it does not guarantee:**

- **Validation is auditable, not tamper-proof.** The MCP tools cannot validate. But any
  program or AI that can run shell commands or write files on your machine can call
  `vmind validate` or edit the SQLite file directly. If an AI works with shell access, the
  history shows what happened; it does not prevent it.
- **A passing check confirms what the check tests**, not that the explanation in the entry
  is right. Our experiments found lessons whose wording was wrong although their check
  passed.
- **Scopes are not access control.** Anyone who can read the file can read all scopes.

**Privacy:** everything is stored unencrypted in one local SQLite file: knowledge, project
journal and conversations. The store stays on your machine. `ask` sends the question and
the retrieved context to the Ollama endpoint in `VMIND_OLLAMA_URL` (by default a local
server; any other address you set receives that data). MCP clients pass what they read from
V-Mind to their model, which may run in the cloud. From the development version after
0.2.0, a new database file is created readable only by its owner on Linux and macOS (0600);
existing files keep their permissions, and on Windows the folder permissions apply. Do not
store passwords or keys. There is currently no command to
delete an entry's content; if a secret ends up in the file, restore an earlier backup or
remove it with SQLite tools, and treat the secret as exposed.

**Backups and upgrades:** the database is one file; while it is being written, SQLite may
keep temporary `-journal` (or `-wal`/`-shm`) files next to it. Copy the file only while no
client is running, or use SQLite, which makes a consistent copy at any time:

```sh
sqlite3 vmind.db ".backup vmind-backup.db"
```

Before installing a new version, make a backup and stop or restart every client that uses
the database (MCP servers keep running the old program). The new version upgrades the
database on first use; the [changelog](CHANGELOG.md) lists schema changes. The development
version after 0.2.0 adds `vmind backup` (verified, never overwrites), `vmind doctor`
(read-only check) and an automatic verified backup before every schema upgrade; see
[docs/operations.md](docs/operations.md) (German).

## Limits

- Search (SQLite FTS5) finds whole words and parts of words (e.g. "Filter" in
  "Testfilter"), but not meanings: no synonyms and no translation.
- `resume` shows a bounded snapshot (open tasks, the latest decisions and events). Older
  details stay in the journal and must be read with `journal`.
- No learning effect is proven; see the experiments above.
- No automatic integration with Codex or ChatGPT; V-Mind does not observe other programs.

Full list (German): [docs/cli.md](docs/cli.md#konfiguration-und-grenzen).

## Project

| File | Contents (currently German) |
|---|---|
| [docs/cli.md](docs/cli.md) | All commands, long projects, configuration, development |
| [docs/protocol.md](docs/protocol.md) | JSONL protocol and MCP server |
| [docs/design.md](docs/design.md) | Architecture and decisions |
| [docs/start-prompt.md](docs/start-prompt.md) | Start prompt for AI clients |
| [AGENTS.md](AGENTS.md) | Working rules for AIs that work on V-Mind itself |
| [CHANGELOG.md](CHANGELOG.md) | Changes per release (English) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributions and checks |

Layout: `crates/vmind-core` (SQLite store and retrieval, no model dependency) and
`crates/vmind-cli` (command line, JSONL, MCP, Ollama adapter).

Checks before every contribution, one at a time:

```sh
cargo test --workspace --locked
```

```sh
cargo clippy --workspace --all-targets --locked -- -D warnings
```

```sh
cargo fmt --all -- --check
```

## License

MIT, see [LICENSE](LICENSE).
