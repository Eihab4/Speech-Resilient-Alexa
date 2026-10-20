import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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


def with_client(url: str, action, token: str | None = None) -> Any:
    async def run():
        async with Client(url, auth=token) as client:
            return await action(client)

    return asyncio.run(run())


class RunNow:
    def __init__(self, target, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)

    def join(self, timeout=None):
        pass


def base_url(url: str) -> str:
    """The server's root, from its /mcp URL, for the page's own routes."""
    return url.rsplit("/", 1)[0]


def http(url: str, method: str = "GET", body: Any = None, token: str | None = None) -> tuple[int, Any]:
    request = Request(url, data=json.dumps(body).encode() if body is not None else None, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"null")
    except HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


TOKENS: dict[tuple[str, str], str] = {}


def token_for(url: str, username: str = "user1") -> str:
    """Signs the person in on the server at url, creating the account the first time."""
    if (url, username) not in TOKENS:
        status, session = http(f"{base_url(url)}/signin", "POST", {"username": username, "password": "secret1"})
        TOKENS[(url, username)] = session["token"] if status == 200 else sign_up(url, username, username.title())
    return TOKENS[(url, username)]


def sign_up(url: str, username: str = "ahmed", name: str = "Ahmed", password: str = "secret1") -> str:
    """Creates an account on the server at url and returns its token."""
    status, session = http(
        f"{base_url(url)}/signup", "POST", {"username": username, "name": name, "password": password}
    )
    assert status == 201, session
    return session["token"]
