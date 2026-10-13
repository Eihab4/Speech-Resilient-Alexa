import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from config import Settings
from enums import LlmProvider

SERVER_SCRIPT = Path(__file__).resolve().parents[1] / "mcp-server" / "server.py"


def real_llm_ready() -> bool:
    """True when LLM_PROVIDER names a hosted model whose API key is set, so real-LLM tests can run."""
    settings = Settings()
    keys = {LlmProvider.OPENROUTER: settings.openrouter.api_key, LlmProvider.GROQ: settings.groq.api_key}
    return bool(keys.get(settings.llm.provider))


needs_real_llm = pytest.mark.skipif(
    not real_llm_ready(), reason="needs LLM_PROVIDER=openrouter or groq with its API key"
)


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


def start_server(path: str = "/mcp", **env: str | None) -> tuple[subprocess.Popen, str]:
    port = free_port()
    overrides = {"MCP_HOST": "127.0.0.1", "MCP_PORT": str(port), "MCP_PATH": path, **env}
    variables = {key: value for key, value in {**os.environ, **overrides}.items() if value is not None}
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
