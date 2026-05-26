from __future__ import annotations

from ._base import Formatter


class PytestFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        head = self._head(content, 400)
        return (
            tool_name == "Bash"
            and ("passed" in head or "failed" in head or "error" in head)
            and ("FAILED" in content or "passed" in content)
            and ("==" in content)
        )

    def format(self, content: str) -> str:
        lines = content.splitlines()
        failures: list[str] = []
        summary_lines: list[str] = []
        in_failure = False
        failure_block: list[str] = []

        for line in lines:
            if line.startswith("FAILED ") or line.startswith("ERROR "):
                if failure_block:
                    failures.append("\n".join(failure_block))
                failure_block = [line]
                in_failure = True
            elif in_failure and line.startswith("="):
                failure_block.append(line)
                failures.append("\n".join(failure_block))
                failure_block = []
                in_failure = False
                summary_lines.append(line)
            elif in_failure:
                failure_block.append(line)
            elif line.startswith("=") and ("passed" in line or "failed" in line or "error" in line):
                summary_lines.append(line)

        if failure_block:
            failures.append("\n".join(failure_block))

        parts: list[str] = []
        if failures:
            parts.append("### Failures\n" + "\n---\n".join(failures))
        if summary_lines:
            parts.append("### Summary\n" + "\n".join(summary_lines))

        return "\n\n".join(parts) if parts else content
