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

> Status: experimental prototype, MIT license. Detailed docs, CLI help texts and the AI
> start prompt are currently in German.

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
- **An AI can only propose knowledge.** Approval is deliberately not available through AI
  tools, only through the command line or an executable check.
- **Nothing is silently overwritten.** Outdated entries are withdrawn; every change stays
  traceable in the history.
- **Scopes** (`--scope`) keep projects apart; the `global` scope applies to all of them.
- **Fully local:** one SQLite file, no cloud service, no GPU required.

**The idea behind it: learning across runs, without training.** A model finds an error
through a real test, fixes it, and proposes the lesson. Once a check confirms it, every
later run can retrieve it and avoid the mistake from the start.

Related approaches such as Reflexion, Voyager or mem0 mostly store what the model
*believes*. V-Mind stores what *verifiably worked*.
[Detailed comparison (German)](docs/design.md#abgrenzung-zu-ähnlichen-ansätzen).

## What is it for?

- **Coding with AI:** solved errors and proven solutions stay available, also for other models.
- **Long-running projects:** after every restart the AI knows what is done and what comes next.
- **Turning small local models into specialists:** a general model plus verified domain
  knowledge, e.g. for science, with sources and without training. This is a hypothesis so
  far; [opportunities and limits (German)](docs/design.md#spezialisierung-kleiner-lokaler-modelle).

## Use it with Claude (Claude Desktop / Claude Code)

With V-Mind as an MCP server, Claude loads the project state at startup, looks up verified
knowledge before making changes, and records finished work in the project journal. This
works in the **Code tab of the Claude desktop app** and in **Claude Code in the terminal**.

### 1. Install V-Mind

Requirements: Rust/Cargo, Git and SQLite with FTS5. On Ubuntu:

```sh
sudo apt install build-essential pkg-config libsqlite3-dev
```

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
via MCP, so an AI cannot slip a command into V-Mind. Make sure a check really tests
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
learns or solves new tasks. A pre-registered follow-up experiment is in progress: does a
small model get better over a series of *different* tasks when it stores its own fixed
errors as lessons that only count after a passing check?
[Setup, measurements and limits (German)](docs/experiments/e2b-pilot.md).

## Limits

- Search (SQLite FTS5) finds whole words and parts of words (e.g. "Filter" in
  "Testfilter"), but not meanings: no synonyms and no translation.
- A validation documents a check; V-Mind does not itself prove that a solution is correct.
- Scopes organize knowledge but are not access control. Data is stored unencrypted in a
  local file.
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
