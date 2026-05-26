from __future__ import annotations

from ._base import Formatter


class EslintFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        return tool_name == "Bash" and (
            "eslint" in tool_input.get("command", "")
            or ("✖ " in content and "problem" in content)
        )

    def format(self, content: str) -> str:
        lines = content.splitlines()
        out: list[str] = []
        for line in lines:
            if line.strip() and not line.startswith("  ") or "error" in line or "warning" in line:
                out.append(line)
        return "\n".join(out) if out else content
