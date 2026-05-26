# clawc

Python-native Claude Code compression and memory hook system.

Hooks Claude Code's `PostToolUse` event to compress tool output **before it enters the context window** — achieving significant token reduction via SHA-256 content-addressed deduplication, an 8-stage compression pipeline, per-runner formatters, and a safe-mode router that passes secrets and stack traces through unmodified.

## Why clawc

Claude Code accumulates context fast. Every `cat`, `grep`, `pytest run`, and `git diff` dumps raw output directly into the context window. Over a long session, this crowds out room for actual reasoning.

`clawc` sits between the tool and Claude via Claude Code's hook system. It compresses, deduplicates, and summarises output — so Claude sees the same information in far fewer tokens.

### clawc vs sqz

| Feature | sqz (Rust) | clawc (Python) |
|---------|-----------|----------------|
| Compresses `Bash` output | ✓ | ✓ |
| Compresses `Read` / `Edit` output | ✗ (PreToolUse only) | ✓ (`PostToolUse.updatedToolOutput`) |
| Exact token counting | ✗ (bytes/4 heuristic) | ✓ (calibrated heuristic, SDK path) |
| Per-runner formatters | Generic only | pytest, jest, vitest, go test, ruff, eslint, git, cargo, npm, docker, kubectl, unittest |
| Install without Rust/C compiler | ✗ | ✓ (`pip install clawc`) |
| Stats / reset | ✗ | ✓ (`clawc stats`) |

---

## Requirements

- Python ≥ 3.11
- Claude Code ≥ v2.1.121 (required for `PostToolUse.updatedToolOutput` support)

---

## Installation

```bash
pip install clawc
# or for an editable dev install
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# 1. Install
pip install clawc

# 2. Wire hooks into your global Claude Code settings
clawc init --scope global

# 3. Restart Claude Code
# Hooks are now active — no further config needed

# 4. Check savings after a session
clawc stats
```

---

## How It Works

Claude Code fires a `PostToolUse` hook after **every** tool call. `clawc` is registered as that hook and receives the raw tool output on stdin. It then:

```
stdin (raw tool output)
        │
        ▼
  [1] Cache lookup  ──── hit? ──▶  §ref:abcd1234§  (~13 tokens)
        │ miss
        ▼
  [2] Near-dup check (simhash Hamming ≤ 8)
        │ near-dup? ──▶  §ref:BASE§ + unified diff
        │ unique
        ▼
  [3] Safe-mode router
        │ unsafe? ──▶  passthrough (0% compression)
        │ safe
        ▼
  [4] Formatter detection
        │ matched? ──▶  apply per-runner formatter (pytest, git, …)
        │ no match
        ▼
  [5] 8-stage compression pipeline
        │
        ▼
  [6] Persist to SQLite cache
        │
        ▼
stdout: {"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": "…"}}
```

Claude Code replaces what Claude sees with the compressed `updatedToolOutput`.

---

## Commands

### `clawc init`

Wire hooks into Claude Code's `settings.json`. Safe to run multiple times — it deep-merges without clobbering existing hooks.

```bash
clawc init --scope global    # ~/.claude/settings.json (all projects)
clawc init --scope project   # .claude/settings.json   (current project only)
clawc init --scope local     # .claude/settings.local.json (gitignored)

clawc init --dry-run         # Preview what would be written, don't write
```

After running, `settings.json` will contain hook wiring like:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash|Read|Edit|MultiEdit|Grep|Glob",
        "hooks": [{"type": "command", "command": "clawc hook PostToolUse", "timeout": 15}]
      }
    ],
    "PreToolUse":   [{"matcher": "Bash", "hooks": [{"type": "command", "command": "clawc hook PreToolUse", "timeout": 10}]}],
    "SessionStart": [{"hooks": [{"type": "command", "command": "clawc hook SessionStart", "timeout": 5}]}],
    "PreCompact":   [{"hooks": [{"type": "command", "command": "clawc hook PreCompact", "timeout": 5}]}],
    "Stop":         [{"hooks": [{"type": "command", "command": "clawc hook Stop", "timeout": 10}]}]
  }
}
```

Restart Claude Code after running `init`.

---

### `clawc stats`

Show a summary of token savings across all sessions (or one session).

```bash
clawc stats                  # All sessions
clawc stats --session s123   # Filter to one session ID
clawc stats --json           # Machine-readable JSON output
```

Example output:

```
          clawc Compression Stats
┌──────────────────────┬────────────┐
│ Metric               │      Value │
├──────────────────────┼────────────┤
│ Total compressions   │        847 │
│ Original tokens      │    412,300 │
│ Compressed tokens    │    189,450 │
│ Tokens saved         │    222,850 │
│ Reduction %          │      54.1% │
│ Cache hits           │        213 │
│ Safe-mode passes     │         42 │
└──────────────────────┴────────────┘
```

---

### `clawc compress`

Manually run text through the compression pipeline. Useful for testing or previewing what `clawc` would do to a given file.

```bash
clawc compress myfile.txt
cat myfile.txt | clawc compress -
clawc compress myfile.txt --tool Read   # Pretend output came from the Read tool
```

Prints the compressed text to stdout and a stats line to stderr:

```
<compressed output>
(1240 → 310 tokens, 75.0% reduction, stages: strip_ansi,condense_logs,flatten_json)
```

---

### `clawc expand`

Look up a `§ref:HASH§` token and print the compressed content it stands for.

```bash
clawc expand "§ref:abcd1234§"
```

Useful when you see a ref token in a transcript and want to know what it refers to.

---

### `clawc memory`

Manage the three-tier `CLAUDE.md` memory system (capped at 100 lines per tier).

```bash
clawc memory --show                      # Print the current project CLAUDE.md
clawc memory --tier global --show        # Print ~/.claude/CLAUDE.md
clawc memory --tier local --show         # Print .claude/CLAUDE.local.md

clawc memory --sync                      # Auto-detect build commands and write them to CLAUDE.md
clawc memory --tier global --sync        # Write build commands to global memory
```

`--sync` scans `pyproject.toml`, `package.json`, `Cargo.toml`, and `Makefile` for build/test commands, then writes a `## Build & Test Commands` section into the target CLAUDE.md.

**Tier paths:**

| Tier | Path | Scope |
|------|------|-------|
| `global` | `~/.claude/CLAUDE.md` | All projects |
| `project` | `<project>/CLAUDE.md` | This project (committed) |
| `local` | `<project>/.claude/CLAUDE.local.md` | This project (gitignored) |

---

### `clawc daemon`

Start a background daemon that keeps all imports warm for sub-5ms hook dispatch. Without the daemon, each hook call pays a ~100ms Python startup cost.

```bash
clawc daemon          # Start daemon (forks to background, Unix socket at ~/.clawc/daemon.sock)
clawc daemon --stop   # Remove the socket (daemon exits on next I/O)
```

The hook automatically uses the daemon if the socket exists; falls back to in-process otherwise.

---

### `clawc mcp`

Start an MCP (Model Context Protocol) stdio server. Register it with Claude Code to expose `clawc_read_file` and `clawc_expand_ref` as tools.

```bash
clawc mcp
```

---

### `clawc hook`

Internal command — called by the hooks in `settings.json`. You don't call this directly, but you can test it:

```bash
# Test PostToolUse compression
echo '{
  "hook_event_name": "PostToolUse",
  "session_id": "test",
  "tool_name": "Bash",
  "tool_input": {"command": "pytest"},
  "tool_result": "FAILED tests/test_foo.py::test_bar\nFAILED tests/test_foo.py::test_baz\n"
}' | clawc hook PostToolUse

# Test safe-mode passthrough (PEM key → no rewrite)
echo '{
  "hook_event_name": "PostToolUse",
  "session_id": "test",
  "tool_name": "Read",
  "tool_result": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n"
}' | clawc hook PostToolUse
# Expected: empty stdout, exit 0 (passthrough — Claude sees the original)
```

---

## Compression Pipeline

Content passes through up to 8 stages in order. Each stage is skipped if it has nothing to do.

| # | Stage | What it does |
|---|-------|-------------|
| 1 | `strip_ansi` | Remove ANSI escape codes (colours, cursor movement) |
| 2 | `strip_nulls` | Drop `null` / `None` fields from JSON objects |
| 3 | `strip_fields` | Remove noisy debug/meta fields (`debug`, `_internal`, `metadata`, …) |
| 4 | `condense_logs` | RLE on repeated lines — keeps the first 3 occurrences, summarises the rest |
| 5 | `truncate_strings` | Clamp string values in JSON to 200 chars |
| 6 | `flatten_json` | Collapse deeply nested objects into `parent.child` dot-notation |
| 7 | `collapse_arrays` | Uniform JSON arrays (≥ 5 items, same keys) → ASCII table (or TOON if installed) |
| 8 | `prose_textrank` | PageRank sentence ranking for prose-heavy output (> 500 chars, > 8 sentences) |

Content shorter than 100 bytes skips the pipeline entirely.

---

## Safe Mode

Some content must never be modified. `clawc` routes to **0% compression** when it detects:

| Trigger | Example |
|---------|---------|
| Shannon entropy > 5.2 bits/byte | Binary data, base64 blobs |
| PEM key header | `-----BEGIN RSA PRIVATE KEY-----` |
| JWT token | `eyJ...` header·payload pattern |
| SQL DDL | `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE` |
| Python traceback | `  File "foo.py", line 42, in bar` |
| JS/Node stack frame | `  at Object.<anonymous> (index.js:10:5)` |
| Env-var blocks | `SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxx` |

In safe mode, `clawc` exits 0 with **empty stdout** — Claude Code uses the original tool output unchanged.

---

## Deduplication

On the first call with a given content block, `clawc` compresses it and stores it in SQLite keyed by `sha256(original)`.

On any subsequent call with **identical content**, `clawc` returns:

```
§ref:abcd1234§
```

That's ~13 Claude tokens instead of the full body. Claude Code is instructed (via `SessionStart`) that `§ref:HASH§` means "same as the last time you saw this content — skip re-reading it."

Use `clawc expand "§ref:abcd1234§"` to look up what a ref token resolves to.

---

## Near-Duplicate Handling

When new content is similar but not identical to cached content (simhash Hamming distance ≤ 8), `clawc` returns:

```
§ref:abcd1234§
--- a/cached
+++ b/current
@@ -3,4 +3,4 @@
 unchanged line
-old line
+new line
```

This shows Claude only what changed, not the full content again.

---

## Per-Runner Formatters

When `clawc` recognises the tool output format, it applies a specialised formatter **before** the generic pipeline stages.

| Formatter | Detects |
|-----------|---------|
| `pytest` | `PASSED` / `FAILED` / `ERROR` test lines, coverage tables |
| `unittest` | `ok` / `FAIL` / `ERROR` from Python unittest |
| `jest` | `✓` / `✗` / `PASS` / `FAIL` Jest output |
| `vitest` | Vitest-specific patterns |
| `go_test` | `--- PASS` / `--- FAIL` from `go test` |
| `ruff` | Ruff lint output with file:line:col |
| `eslint` | ESLint output |
| `git` | `git diff`, `git log`, `git status` |
| `cargo` | Rust cargo build/test |
| `npm` | npm install / run output |
| `docker` | Docker build / run logs |
| `kubectl` | kubectl output |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAWC_DB_PATH` | `~/.clawc/sessions.db` | SQLite database path |

---

## Database

`clawc` uses a single SQLite database (`~/.clawc/sessions.db`) with WAL mode and FTS5:

- **`sessions`** — one row per Claude Code session
- **`cache_entries`** — compressed content keyed by SHA-256 hash
- **`compressions`** — one row per compression event (tokens in/out, stages applied)
- **`deltas`** — near-duplicate patches (simhash + difflib unified diff)
- **`cache_fts`** — FTS5 virtual table over cache content

---

## Development

```bash
# Install with dev extras
pip install -e ".[dev]"

# Run tests
pytest tests/ -v --tb=short

# Lint
ruff check .

# Type check
mypy clawc/
```

### Running Tests

```bash
pytest tests/unit/          # Unit tests (no I/O)
pytest tests/integration/   # End-to-end hook roundtrips (uses subprocess)
pytest tests/ -k "dedup"    # Filter by name
pytest tests/ --hypothesis-seed=0  # Property tests with fixed seed
```

### Benchmark Gates (verified)

| Scenario | Result | Gate |
|----------|--------|------|
| Repeated log lines (20× same line) | **76.8% reduction** | ≥ 50% |
| Repeat call (identical content) | **96.8% reduction** via `§ref§` | ≥ 90% |
| Stack trace (safe mode) | **0% modification** | = 0% |
| JSON array (10 uniform objects) | TOON/table format applied | ≥ 30% |

---

## Architecture

```
clawc/
├── hooks/           # One handler per Claude Code hook event
│   ├── _protocol.py      # HookInput / HookOutput dataclasses, stdin/stdout contract
│   ├── posttooluse.py    # Core dispatch logic (cache → near-dup → safe → format → pipeline)
│   ├── pretooluse.py     # PreToolUse (Bash guard)
│   ├── sessionstart.py   # Session init, §ref§ instruction injection
│   ├── precompact.py     # PreCompact (inject memory context)
│   └── stop.py           # Stop (write MEMORY.md, log final stats)
├── pipeline/
│   ├── __init__.py       # CompressionPipeline orchestrator
│   ├── safemode.py       # Entropy + regex unsafe detector
│   └── stages/           # 8 individual stage modules
├── formatters/           # Per-tool-runner output formatters
├── cache/
│   ├── store.py          # SQLite + WAL + FTS5 cache store
│   ├── dedup.py          # SHA-256 keying + §ref:HASH§ tokens
│   └── delta.py          # Simhash near-dup + difflib patch generation
├── tokens/
│   └── counter.py        # Token counting (heuristic + SDK path)
├── memory/
│   ├── claude_md.py      # Three-tier CLAUDE.md read/write/sync
│   └── auto_memory.py    # Automatic memory extraction
├── budget/
│   └── tracker.py        # Context window budget tracking
├── router/
│   ├── model.py          # Model suggestion based on content complexity
│   └── confidence.py     # Routing confidence (safe/normal/aggressive)
├── mcp/
│   └── server.py         # MCP stdio server
├── daemon/
│   └── server.py         # Unix socket daemon for low-latency dispatch
└── cli.py                # Typer CLI entry point
```

---

## Hook Protocol Reference

Claude Code sends JSON on stdin for every hook event:

```json
{
  "hook_event_name": "PostToolUse",
  "session_id": "abc123",
  "tool_name": "Bash",
  "tool_input": {"command": "pytest tests/"},
  "tool_result": "<raw tool output>",
  "cwd": "/home/user/project"
}
```

To rewrite what Claude sees, respond with:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "updatedToolOutput": "<compressed text or §ref:abcd1234§>"
  }
}
```

Empty stdout = passthrough (Claude sees the original output).

Exit codes: `0` = continue, `1` = warn (shown to user, not Claude), `2` = block tool call.
