from __future__ import annotations

from ._base import Formatter


class NpmFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        cmd = tool_input.get("command", "")
        return tool_name == "Bash" and (cmd.startswith("npm ") or cmd.startswith("npx "))

    def format(self, content: str) -> str:
        lines = content.splitlines()
        out = [
            ln for ln in lines
            if not ln.startswith("npm warn") and not ln.startswith("npm notice")
        ]
        return "\n".join(out) if out else content
