from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="clawc", no_args_is_help=True, help="Claude Code compression & memory hooks")
console = Console()


@app.command()
def hook(
    event: str = typer.Argument(..., help="Hook event name (PostToolUse, SessionStart, …)"),
) -> None:
    """Dispatch a Claude Code hook event (stdin → stdout, used by settings.json)."""
    from clawc.hooks import posttooluse, precompact, pretooluse, sessionstart, stop
    from clawc.hooks._protocol import HookInput

    inp = HookInput.from_stdin()
    if event and not inp.hook_event_name:
        inp.hook_event_name = event

    dispatch = {
        "PreToolUse": pretooluse.handle,
        "PostToolUse": posttooluse.handle,
        "SessionStart": sessionstart.handle,
        "PreCompact": precompact.handle,
        "Stop": stop.handle,
    }
    handler = dispatch.get(inp.hook_event_name or event)
    if handler:
        handler(inp)
    sys.exit(0)


@app.command()
def compress(
    input: typer.FileText = typer.Argument(default="-", help="Input file (- for stdin)"),  # noqa: B008
    tool_name: str = typer.Option("Bash", "--tool", help="Pretend output came from this tool"),
) -> None:
    """Compress text through the pipeline and print result."""
    from clawc.pipeline import run as pipeline_run

    content = input.read()
    result = pipeline_run(content, tool_name=tool_name)
    console.print(result.text, end="")
    console.print(
        f"\n[dim]({result.original_tokens} → {result.compressed_tokens} tokens, "
        f"{result.reduction_pct:.1f}% reduction, stages: {result.stages_applied})[/dim]",
        err=True,
    )


@app.command()
def expand(
    ref: str = typer.Argument(..., help="§ref:HASH§ token to expand"),
) -> None:
    """Expand a §ref:HASH§ token back to its compressed content."""
    from clawc.cache.store import CacheStore

    store = CacheStore.open()
    entry = store.lookup_by_ref(ref)
    if entry:
        console.print(entry["compressed"])
    else:
        console.print(f"[red]Ref not found in cache: {ref}[/red]", err=True)
        raise typer.Exit(1)


@app.command()
def stats(
    session: str | None = typer.Option(None, "--session", "-s", help="Filter by session ID"),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show compression statistics."""
    from clawc.cache.store import CacheStore

    store = CacheStore.open()
    data = store.stats(session)

    if json_out:
        console.print(json.dumps(data, indent=2))
        return

    table = Table(title="clawc Compression Stats", show_header=True)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Total compressions", str(data.get("total_compressions", 0)))
    table.add_row("Original tokens", str(data.get("total_original_tokens", 0)))
    table.add_row("Compressed tokens", str(data.get("total_compressed_tokens", 0)))
    table.add_row("Tokens saved", f"[green]{data.get('tokens_saved', 0)}[/green]")
    table.add_row("Reduction %", f"[green]{data.get('reduction_pct', 0):.1f}%[/green]")
    table.add_row("Cache hits", str(data.get("cache_hits", 0)))
    table.add_row("Safe-mode passes", str(data.get("safe_mode_passes", 0)))
    console.print(table)


@app.command()
def init(
    scope: str = typer.Option(
        "global", "--scope", help="Scope: global (~/.claude) | project (.claude/) | local"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would change, don't write"),
) -> None:
    """Wire clawc hooks into Claude Code settings.json."""
    def _cmd(event: str, timeout: int, matcher: str = "") -> list:
        entry: dict = {"type": "command", "command": f"clawc hook {event}", "timeout": timeout}
        hook: dict = {"hooks": [entry]}
        if matcher:
            hook["matcher"] = matcher
        return [hook]

    _HOOK_WIRING = {
        "hooks": {
            "PreToolUse": _cmd("PreToolUse", 10, "Bash"),
            "PostToolUse": _cmd("PostToolUse", 15, "Bash|Read|Edit|MultiEdit|Grep|Glob"),
            "SessionStart": _cmd("SessionStart", 5),
            "PreCompact": _cmd("PreCompact", 5),
            "Stop": _cmd("Stop", 10),
        }
    }

    if scope == "global":
        settings_path = Path.home() / ".claude" / "settings.json"
    elif scope == "project":
        settings_path = Path.cwd() / ".claude" / "settings.json"
    else:
        settings_path = Path.cwd() / ".claude" / "settings.local.json"

    existing: dict = {}
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            existing = {}

    merged = _deep_merge_hooks(existing, _HOOK_WIRING)

    if dry_run:
        console.print(f"[bold]Would write to:[/bold] {settings_path}")
        console.print(json.dumps(merged, indent=2))
        return

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(merged, indent=2) + "\n")
    console.print(f"[green]✓[/green] Hook wiring written to {settings_path}")
    console.print("[dim]Restart Claude Code to apply the new hooks.[/dim]")


def _deep_merge_hooks(base: dict, overlay: dict) -> dict:
    result = dict(base)
    for key, value in overlay.items():
        if key == "hooks" and isinstance(value, dict):
            base_hooks = result.get("hooks", {})
            merged_hooks: dict = dict(base_hooks)
            for event, entries in value.items():
                existing_entries = merged_hooks.get(event, [])
                clawc_cmds = {
                    h["command"]
                    for e in existing_entries
                    for h in e.get("hooks", [])
                    if "clawc hook" in h.get("command", "")
                }
                new_entries = [
                    e for e in entries
                    if not any("clawc hook" in h.get("command", "") for h in e.get("hooks", []))
                    or not clawc_cmds
                ]
                merged_hooks[event] = existing_entries + new_entries
            result["hooks"] = merged_hooks
        else:
            result[key] = value
    return result


@app.command()
def memory(
    tier: str = typer.Option("project", "--tier", help="global | project | local"),
    sync: bool = typer.Option(False, "--sync", help="Sync build commands from project manifests"),
    show: bool = typer.Option(False, "--show", help="Print current CLAUDE.md content"),
) -> None:
    """Manage CLAUDE.md memory files."""
    from clawc.memory.claude_md import (
        MAX_LINES,
        _tier_paths,
        build_claude_md_block,
        read_tier,
        sync_build_commands,
        write_tier,
    )

    paths = _tier_paths(str(Path.cwd()))
    path = paths.get(tier, paths["project"])

    if show:
        content = read_tier(path)
        console.print(content or "[dim](empty)[/dim]")
        return

    if sync:
        cmds = sync_build_commands(Path.cwd())
        if not cmds:
            console.print("[yellow]No build commands found in project manifests.[/yellow]")
            return
        block = build_claude_md_block(cmds)
        existing = read_tier(path)
        marker = "## Build & Test Commands"
        if marker in existing:
            before = existing[: existing.index(marker)]
            write_tier(path, before.rstrip() + "\n\n" + block)
        else:
            write_tier(path, (existing.rstrip() + "\n\n" + block).strip())
        console.print(f"[green]✓[/green] Synced {len(cmds)} commands to {path}")
        return

    console.print(f"CLAUDE.md path ({tier}): {path}")
    console.print(f"Max lines: {MAX_LINES}")
    if path.exists():
        lines = path.read_text().splitlines()
        console.print(f"Current lines: {len(lines)}")


@app.command()
def mcp() -> None:
    """Start the clawc MCP stdio server."""
    from clawc.mcp.server import main
    main()


@app.command()
def daemon(
    stop: bool = typer.Option(False, "--stop", help="Stop the running daemon"),
) -> None:
    """Start (or stop) the background daemon for sub-5ms hook dispatch."""
    from clawc.daemon.server import SOCKET_PATH

    if stop:
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
            console.print("[green]✓[/green] Daemon socket removed.")
        else:
            console.print("[yellow]No daemon socket found.[/yellow]")
        return

    console.print("Starting clawc daemon…")
    import subprocess
    subprocess.Popen(
        [sys.executable, "-m", "clawc.daemon.server"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    console.print(f"[green]✓[/green] Daemon started at {SOCKET_PATH}")


if __name__ == "__main__":
    app()
