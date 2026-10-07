import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from fastmcp import Client

SERVER_SCRIPT = Path(__file__).resolve().parents[1] / "mcp-server" / "server.py"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_until_listening(process: subprocess.Popen, port: int, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(process.stderr.read().decode())
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise TimeoutError(f"server did not listen on port {port}")


def start_server(path: str = "/mcp", **env: str) -> tuple[subprocess.Popen, str]:
    port = free_port()
    variables = {**os.environ, "MCP_HOST": "127.0.0.1", "MCP_PORT": str(port), "MCP_PATH": path, **env}
    process = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT)],
        env=variables,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    wait_until_listening(process, port)
    return process, f"http://127.0.0.1:{port}{path}"


def with_client(url: str, action) -> Any:
    async def run():
        async with Client(url) as client:
            return await action(client)

    return asyncio.run(run())
