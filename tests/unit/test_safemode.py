from __future__ import annotations

import pytest

from clawc.pipeline.safemode import is_unsafe


@pytest.mark.parametrize(
    "content,expected",
    [
        ("-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----", True),
        ("-----BEGIN CERTIFICATE-----\nABC\n-----END CERTIFICATE-----", True),
        ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.abc123XYZ", True),
        ('  File "app.py", line 42, in main', True),
        ('  File "test.py", line 1, in <module>', True),
        ("normal git status output\nOn branch main", False),
        ("def foo():\n    return 42\n", False),
        ("import os\nimport sys\n\nprint('hello')", False),
        ("test result: ok. 5 passed in 0.12s", False),
        ("CREATE TABLE users (id INTEGER PRIMARY KEY)", True),
        ("ALTER TABLE users ADD COLUMN email TEXT", True),
    ],
)
def test_safemode_detection(content: str, expected: bool) -> None:
    assert is_unsafe(content) == expected


def test_stack_trace_always_safe() -> None:
    traceback = (
        'Traceback (most recent call last):\n'
        '  File "app.py", line 10, in main\n'
        '    result = divide(1, 0)\n'
        '  File "math.py", line 5, in divide\n'
        '    return a / b\n'
        "ZeroDivisionError: division by zero"
    )
    assert is_unsafe(traceback) is True
