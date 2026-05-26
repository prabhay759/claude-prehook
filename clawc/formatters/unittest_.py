from __future__ import annotations

from ._base import Formatter


class UnittestFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        return tool_name == "Bash" and (
            "Ran " in content and ("OK" in content or "FAILED" in content)
            and "------" in content
        )

    def format(self, content: str) -> str:
        lines = content.splitlines()
        out: list[str] = []
        for line in lines:
            if (
                line.startswith("ERROR:")
                or line.startswith("FAIL:")
                or line.startswith("Traceback")
                or "------" in line
                or line.startswith("Ran ")
                or line.startswith("OK")
                or line.startswith("FAILED")
            ):
                out.append(line)
        return "\n".join(out) if out else content
