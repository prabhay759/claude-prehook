from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _memory_path(cwd: str = "") -> Path:
    project_root = Path(cwd) if cwd else Path.cwd()
    project_slug = str(project_root).replace("/", "-").lstrip("-")
    return Path.home() / ".claude" / "projects" / project_slug / "memory" / "MEMORY.md"


def write_session_summary(stats: dict[str, Any], cwd: str = "") -> None:
    if os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY"):
        return

    tokens_saved = stats.get("tokens_saved", 0)
    if tokens_saved == 0:
        return

    path = _memory_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = (
        f"\n## Session {now}\n"
        f"- Compressions: {stats.get('total_compressions', 0)}\n"
        f"- Tokens saved: {tokens_saved} ({stats.get('reduction_pct', 0):.1f}% reduction)\n"
        f"- Cache hits: {stats.get('cache_hits', 0)}\n"
    )

    existing = path.read_text(encoding="utf-8") if path.exists() else "# clawc Session Memory\n"
    path.write_text(existing + entry, encoding="utf-8")
