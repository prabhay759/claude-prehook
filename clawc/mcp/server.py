from __future__ import annotations

import asyncio
from pathlib import Path


async def _serve() -> None:
    try:
        from mcp.server import Server  # type: ignore[import]
        from mcp.server.stdio import stdio_server  # type: ignore[import]
        from mcp import types  # type: ignore[import]
    except ImportError:
        raise SystemExit("mcp package not installed. Run: pip install mcp")

    from clawc.cache.store import CacheStore
    from clawc.pipeline import run as pipeline_run

    app: Server = Server("clawc")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="clawc_read_file",
                description=(
                    "Read a file with compression and deduplication. "
                    "Returns §ref:HASH§ if content was seen before this session."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Absolute path to the file"},
                        "session_id": {"type": "string"},
                    },
                    "required": ["path"],
                },
            ),
            types.Tool(
                name="clawc_expand_ref",
                description="Expand a §ref:HASH§ token back to its original (compressed) content.",
                inputSchema={
                    "type": "object",
                    "properties": {"ref": {"type": "string"}},
                    "required": ["ref"],
                },
            ),
            types.Tool(
                name="clawc_search_cache",
                description="Full-text search the compression cache for previous tool outputs.",
                inputSchema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        store = CacheStore.open()

        if name == "clawc_read_file":
            path = Path(arguments["path"])
            if not path.exists():
                return [types.TextContent(type="text", text=f"File not found: {path}")]
            content = path.read_text(errors="replace")
            from clawc.cache.dedup import sha256_hex
            content_hash = sha256_hex(content)
            entry = store.lookup(content_hash)
            if entry:
                store.record_hit(content_hash)
                return [types.TextContent(type="text", text=entry["ref_token"])]
            result = pipeline_run(content, tool_name="Read")
            store.store(content_hash, content, result.text, "Read")
            return [types.TextContent(type="text", text=result.text)]

        elif name == "clawc_expand_ref":
            ref = arguments["ref"]
            entry = store.lookup_by_ref(ref)
            text = entry["compressed"] if entry else ref
            return [types.TextContent(type="text", text=text)]

        elif name == "clawc_search_cache":
            results = store.search(arguments["query"])
            if not results:
                return [types.TextContent(type="text", text="No cache entries matched.")]
            lines = [f"{r['content_hash'][:8]}: {r['compressed'][:100]}" for r in results]
            return [types.TextContent(type="text", text="\n".join(lines))]

        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    asyncio.run(_serve())
