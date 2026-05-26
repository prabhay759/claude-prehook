from __future__ import annotations

from ._base import Formatter


class GitFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        head = self._head(content, 200)
        if tool_name != "Bash":
            return False
        cmd = tool_input.get("command", "")
        return (
            cmd.startswith("git ")
            or "On branch" in head
            or "diff --git" in head
            or "files changed" in content
        )

    def format(self, content: str) -> str:
        lines = content.splitlines()
        if content.count("\n") > 80 and "diff --git" in content:
            return self._compress_diff(lines)
        return content

    def _compress_diff(self, lines: list[str]) -> str:
        out: list[str] = []
        for line in lines:
            if (
                line.startswith("diff --git")
                or line.startswith("index ")
                or line.startswith("---")
                or line.startswith("+++")
                or line.startswith("@@")
                or line.startswith("+")
                or line.startswith("-")
                or line.startswith("Binary")
            ):
                out.append(line)
        return "\n".join(out)
