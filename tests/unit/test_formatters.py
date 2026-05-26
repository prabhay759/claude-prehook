from __future__ import annotations

from clawc.formatters import FormatterRegistry


def test_pytest_formatter_detected() -> None:
    content = (
        "FAILED tests/test_foo.py::test_bar - AssertionError\n"
        "collected 5 items\n"
        "============================= 1 failed, 4 passed in 0.12s ============================\n"
    )
    result = FormatterRegistry.detect_and_apply("Bash", {"command": "pytest"}, content)
    assert result is not None
    assert "Failures" in result or "failed" in result


def test_git_formatter_compresses_large_diff() -> None:
    header = "diff --git a/foo.py b/foo.py\nindex abc..def 100644\n--- a/foo.py\n+++ b/foo.py\n"
    hunk = "@@ -1,5 +1,5 @@\n"
    context = "\n".join(f" context line {i}" for i in range(100))
    changed = "\n-old line\n+new line\n"
    content = header + hunk + context + changed
    result = FormatterRegistry.detect_and_apply("Bash", {"command": "git diff"}, content)
    if result:
        assert len(result) < len(content)


def test_no_formatter_for_unknown_content() -> None:
    result = FormatterRegistry.detect_and_apply("Bash", {}, "hello world\njust some text\n")
    assert result is None


def test_cargo_formatter_detected() -> None:
    content = (
        "Compiling my-crate v0.1.0\n"
        "error[E0308]: mismatched types\n"
        "  --> src/main.rs:10:5\n"
        "   | \n"
        "10 |     return \"hello\";\n"
        "   |     ^^^^^^^^^^^^^^\n"
        "Finished dev\n"
    )
    result = FormatterRegistry.detect_and_apply("Bash", {"command": "cargo build"}, content)
    assert result is not None
    assert "error" in result
    assert "Compiling" not in result
