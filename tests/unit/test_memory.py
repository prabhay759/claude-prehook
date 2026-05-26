from __future__ import annotations

from pathlib import Path

from clawc.memory.claude_md import (
    MAX_LINES,
    build_claude_md_block,
    read_tier,
    write_tier,
)


def test_write_tier_creates_file(tmp_path: Path) -> None:
    p = tmp_path / "CLAUDE.md"
    write_tier(p, "# Test\n\n- item one\n- item two")
    assert p.exists()
    assert "item one" in p.read_text()


def test_write_tier_truncates_to_max_lines(tmp_path: Path) -> None:
    p = tmp_path / "CLAUDE.md"
    content = "\n".join(f"line {i}" for i in range(200))
    write_tier(p, content, max_lines=MAX_LINES)
    lines = p.read_text().splitlines()
    assert len(lines) <= MAX_LINES


def test_read_tier_missing_file(tmp_path: Path) -> None:
    p = tmp_path / "nonexistent.md"
    assert read_tier(p) == ""


def test_build_claude_md_block_format() -> None:
    cmds = {"test": "pytest tests/", "lint": "ruff check ."}
    block = build_claude_md_block(cmds)
    assert "## Build & Test Commands" in block
    assert "pytest" in block
    assert "ruff" in block


def test_build_claude_md_block_empty() -> None:
    assert build_claude_md_block({}) == ""
