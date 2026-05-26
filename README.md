# clawc

Python-native Claude Code compression and memory hook system.

Hooks Claude Code's `PostToolUse` event to compress tool output (Bash, Read, Edit, Grep, …) before it enters the context window — achieving significant token reduction via SHA-256 content-addressed deduplication, an 8-stage compression pipeline, per-runner formatters, and a safe-mode router that passes secrets and stack traces through unmodified.

## Why clawc vs sqz

| Feature | sqz (Rust) | clawc (Python) |
|---------|-----------|----------------|
| Compresses Bash output | ✓ | ✓ |
| Compresses Read/Edit output | ✗ (PreToolUse only) | ✓ (`PostToolUse.updatedToolOutput`) |
| Exact token counting | ✗ (bytes/4 heuristic) | ✓ (calibrated heuristic) |
| Per-runner test formatters | Generic only | pytest, jest, vitest, go test, ruff… |
| Install without Rust/C compiler | ✗ | ✓ (`pip install clawc`) |
| Stats reset | ✗ (open issue #17) | ✓ |

## Quick start

```bash
pip install clawc
clawc init --scope global   # wires hooks into ~/.claude/settings.json
# Restart Claude Code
clawc stats
```

## How it works

1. Claude Code fires `PostToolUse` after every tool call (Bash, Read, Edit, Grep, Glob, …)
2. `clawc hook PostToolUse` reads the raw output on stdin
3. Pipeline: SHA-256 dedup check → near-dup delta → safe-mode router → formatter → 8-stage compressor
4. Returns `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": "…"}}`
5. On repeat reads of identical content: returns `§ref:abcd1234§` (~13 tokens) instead of the full body

## Commands

```
clawc hook <event>     # Called by settings.json hooks
clawc compress [file]  # Manual compression test
clawc expand <ref>     # Expand §ref:HASH§ to compressed content
clawc stats            # Show token savings
clawc init             # Write hook wiring to settings.json
clawc memory           # Manage CLAUDE.md tiers
clawc mcp              # Start MCP stdio server
clawc daemon           # Start background daemon for sub-5ms dispatch
```

## Architecture

```
clawc/
├── hooks/          # One handler per Claude Code event
├── pipeline/       # 8-stage compression pipeline + safe-mode router
├── formatters/     # Per-tool-runner output formatters
├── cache/          # SHA-256 dedup store (SQLite + WAL + FTS5)
├── tokens/         # Token counting
├── memory/         # CLAUDE.md and MEMORY.md writers
├── budget/         # Context window budget tracking
├── router/         # Confidence and model routing
├── mcp/            # MCP stdio server
└── daemon/         # Unix socket daemon for low-latency dispatch
```

## Compression pipeline stages

1. `strip_ansi` — remove ANSI escape codes
2. `strip_nulls` — drop null JSON fields
3. `strip_fields` — remove noisy debug/meta fields from JSON
4. `condense_logs` — RLE on repeated lines (max 3 repeats)
5. `truncate_strings` — bound overly long strings in JSON
6. `flatten_json` — flatten deeply nested objects
7. `collapse_arrays` — uniform JSON arrays → ASCII table (or TOON format)
8. `prose_textrank` — PageRank sentence ranking for prose-heavy output

## Safe mode

Routes to 0% compression when:
- Shannon entropy > 5.2 bits/byte (secrets, base64 blobs)
- PEM key headers
- JWT format
- SQL DDL statements (migrations)
- Python/JS stack traces

## Benchmark results (verified)

- Repeated log lines (20×): **76.8% reduction** on first call
- Repeat call to identical content: **96.8% reduction** via `§ref§`
- Stack traces: **0% modification** (safe mode passthrough)

## Requirements

- Python ≥ 3.11
- Claude Code ≥ v2.1.121 (for `PostToolUse.updatedToolOutput` support)
