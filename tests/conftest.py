from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "test.db"
    monkeypatch.setenv("CLAWC_DB_PATH", str(db))
    return db


@pytest.fixture()
def sample_bash_repeated() -> str:
    return "line one\n" * 20


@pytest.fixture()
def sample_json_array() -> str:
    items = [{"id": i, "name": f"item{i}", "value": i * 10} for i in range(10)]
    return json.dumps(items)


@pytest.fixture()
def hook_input_factory():
    def _make(event: str, tool_name: str = "Bash", tool_result: str = "", **kwargs) -> dict:
        return {
            "hook_event_name": event,
            "session_id": "test-session",
            "cwd": "/tmp",
            "tool_name": tool_name,
            "tool_input": kwargs.get("tool_input", {"command": "echo test"}),
            "tool_result": tool_result,
        }
    return _make
