from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAX_LINES = 100


def _tier_paths(cwd: str = "") -> dict[str, Path]:
    project_root = Path(cwd) if cwd else Path.cwd()
    return {
        "global": Path.home() / ".claude" / "CLAUDE.md",
        "project": project_root / "CLAUDE.md",
        "local": project_root / ".claude" / "CLAUDE.local.md",
    }


def read_tier(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def write_tier(path: Path, content: str, max_lines: int = MAX_LINES) -> None:
    lines = content.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def sync_build_commands(project_root: Path) -> dict[str, str]:
    cmds: dict[str, str] = {}
    manifests: dict[str, Any] = {
        "pyproject.toml": _parse_pyproject,
        "package.json": _parse_package_json,
        "Cargo.toml": _parse_cargo,
        "Makefile": _parse_makefile,
    }
    for name, parser in manifests.items():
        f = project_root / name
        if f.exists():
            try:
                cmds.update(parser(f.read_text(encoding="utf-8")))
            except Exception:
                pass
    return cmds


def _parse_pyproject(content: str) -> dict[str, str]:
    cmds: dict[str, str] = {}
    try:
        import tomllib
    except ImportError:
        return cmds
    try:
        data = tomllib.loads(content)
    except Exception:
        return cmds
    scripts = data.get("tool", {}).get("hatch", {}).get("envs", {}).get("default", {}).get("scripts", {})
    for name, cmd in scripts.items():
        cmds[name] = cmd if isinstance(cmd, str) else cmd[0] if cmd else ""
    for name, ep in data.get("project", {}).get("scripts", {}).items():
        cmds[f"run:{name}"] = ep
    return cmds


def _parse_package_json(content: str) -> dict[str, str]:
    try:
        data = json.loads(content)
        scripts = data.get("scripts", {})
        return {f"npm run {k}": v for k, v in scripts.items()}
    except Exception:
        return {}


def _parse_cargo(content: str) -> dict[str, str]:
    cmds: dict[str, str] = {}
    if "[[bin]]" in content:
        cmds["build"] = "cargo build"
        cmds["test"] = "cargo test"
    return cmds


def _parse_makefile(content: str) -> dict[str, str]:
    import re
    targets = re.findall(r"^([a-zA-Z][a-zA-Z0-9_-]*):", content, re.MULTILINE)
    return {t: f"make {t}" for t in targets[:10]}


def build_claude_md_block(cmds: dict[str, str]) -> str:
    if not cmds:
        return ""
    lines = ["## Build & Test Commands", ""]
    for name, cmd in list(cmds.items())[:15]:
        lines.append(f"- `{cmd}` ({name})")
    return "\n".join(lines)
