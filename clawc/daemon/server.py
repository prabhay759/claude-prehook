from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

SOCKET_PATH = Path.home() / ".clawc" / "daemon.sock"
_BUFSIZE = 1 << 20


def _handle_request(data: bytes) -> bytes:
    try:
        inp_dict = json.loads(data)
    except json.JSONDecodeError:
        return b"{}"

    from clawc.hooks._protocol import HookInput
    from clawc.hooks import posttooluse, pretooluse, sessionstart, precompact, stop

    inp = HookInput(**{k: inp_dict.get(k, v.default) for k, v in HookInput.__dataclass_fields__.items()})  # type: ignore[attr-defined]

    import io
    sys.stdout = buf = io.StringIO()

    try:
        dispatch = {
            "PreToolUse": pretooluse.handle,
            "PostToolUse": posttooluse.handle,
            "SessionStart": sessionstart.handle,
            "PreCompact": precompact.handle,
            "Stop": stop.handle,
        }
        handler = dispatch.get(inp.hook_event_name)
        if handler:
            try:
                handler(inp)
            except SystemExit:
                pass
    finally:
        sys.stdout = sys.__stdout__

    return buf.getvalue().encode("utf-8")


def run_daemon() -> None:
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as srv:
        srv.bind(str(SOCKET_PATH))
        srv.listen(8)
        while True:
            conn, _ = srv.accept()
            with conn:
                chunks: list[bytes] = []
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                response = _handle_request(b"".join(chunks))
                conn.sendall(response)


def try_daemon_call(inp_dict: dict) -> str | None:
    if not SOCKET_PATH.exists():
        return None
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(str(SOCKET_PATH))
            s.sendall(json.dumps(inp_dict).encode("utf-8"))
            s.shutdown(socket.SHUT_WR)
            chunks: list[bytes] = []
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks).decode("utf-8")
    except (ConnectionRefusedError, FileNotFoundError, TimeoutError):
        return None


if __name__ == "__main__":
    run_daemon()
