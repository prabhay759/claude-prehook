from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_hook(stdin_data: dict, env_extras: dict | None = None) -> tuple[int, dict]:
    import os

    env = os.environ.copy()
    if env_extras:
        env.update(env_extras)

    proc = subprocess.run(
        [sys.executable, "-m", "clawc", "hook", "PostToolUse"],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        env=env,
    )
    stdout = proc.stdout.strip()
    out = json.loads(stdout) if stdout else {}
    return proc.returncode, out


def make_input(content: str, tool_name: str = "Bash") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "session_id": "integration-test",
        "cwd": "/tmp",
        "tool_name": tool_name,
        "tool_input": {"command": "git status"},
        "tool_result": content,
    }


def test_first_read_returns_compressed(tmp_path: Path) -> None:
    db = str(tmp_path / "test.db")
    content = "On branch main\nnothing to commit\n" * 20
    code, out = run_hook(make_input(content), {"CLAWC_DB_PATH": db})
    assert code == 0
    if "hookSpecificOutput" in out:
        assert "updatedToolOutput" in out["hookSpecificOutput"]


def test_second_read_returns_ref_token(tmp_path: Path) -> None:
    db = str(tmp_path / "test.db")
    content = "On branch main\nnothing to commit\n" * 20
    inp = make_input(content)

    run_hook(inp, {"CLAWC_DB_PATH": db})
    _, out = run_hook(inp, {"CLAWC_DB_PATH": db})

    assert "hookSpecificOutput" in out
    updated = out["hookSpecificOutput"].get("updatedToolOutput", "")
    assert updated.startswith("§ref:")
    assert updated.endswith("§")


def test_safe_mode_passthrough(tmp_path: Path) -> None:
    db = str(tmp_path / "test.db")
    content = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    code, out = run_hook(make_input(content, "Read"), {"CLAWC_DB_PATH": db})
    assert code == 0
    if "hookSpecificOutput" in out:
        assert "updatedToolOutput" not in out["hookSpecificOutput"]


def test_short_content_passthrough(tmp_path: Path) -> None:
    db = str(tmp_path / "test.db")
    content = "ok"
    code, out = run_hook(make_input(content), {"CLAWC_DB_PATH": db})
    assert code == 0


def test_repeated_log_lines_compressed(tmp_path: Path) -> None:
    db = str(tmp_path / "test.db")
    content = "INFO: processing item\n" * 20
    code, out = run_hook(make_input(content), {"CLAWC_DB_PATH": db})
    assert code == 0
    if "hookSpecificOutput" in out:
        updated = out["hookSpecificOutput"].get("updatedToolOutput", "")
        assert len(updated) < len(content)
