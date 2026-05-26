from __future__ import annotations

from ._base import Formatter


class JestFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        return tool_name == "Bash" and (
            "PASS " in content or "FAIL " in content
        ) and ("Tests:" in content or "Test Suites:" in content)

    def format(self, content: str) -> str:
        lines = content.splitlines()
        out: list[str] = []
        for line in lines:
            if (
                line.startswith("PASS ")
                or line.startswith("FAIL ")
                or line.startswith("  ●")
                or line.startswith("Tests:")
                or line.startswith("Test Suites:")
                or line.startswith("Snapshots:")
                or line.startswith("Time:")
            ):
                out.append(line)
        return "\n".join(out) if out else content
