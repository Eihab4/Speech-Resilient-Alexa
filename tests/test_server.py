import asyncio
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import boto3
import pytest
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import InvalidStatus

from enums import TranscriptType
from support import token_for, with_client


def preflight(url: str, origin: str):
    request = Request(url, method="OPTIONS", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    with urlopen(request) as response:
        return response.status, response.headers


async def describe(client):
    tools = await client.list_tools()
    return client.protocol_version, [tool.name for tool in tools]


def test_server_runs_on_configured_port_and_path(server):
    url = server(path="/speech", LLM_PROVIDER="bedrock")

    version, tools = with_client(url, describe, token_for(url))

    assert version >= "2025-11-25"
    assert "understand_speech" in tools


def test_browser_frontend_may_call_the_server_from_any_local_port(server):
    url = server()

    for origin in ["http://localhost:5180", "http://127.0.0.1:3000"]:
        status, headers = preflight(url, origin)

        assert status == 200
        assert headers["access-control-allow-origin"] == origin


def test_extra_origins_can_be_allowed(server):
    url = server(MCP_CORS_ORIGINS='["https://demo.example.com"]')

    status, headers = preflight(url, "https://demo.example.com")

    assert status == 200
    assert headers["access-control-allow-origin"] == "https://demo.example.com"


def test_other_sites_are_not_allowed(server):
    url = server()

    try:
        _, headers = preflight(url, "http://evil.example.com")
    except HTTPError as error:
        headers = error.headers

    assert "access-control-allow-origin" not in headers


def transcribe_url(url: str) -> str:
    return url.replace("http://", "ws://").rsplit("/", 1)[0] + "/transcribe"


def test_voice_socket_refuses_other_sites(server):
    url = transcribe_url(server())

    async def connect():
        async with ws_connect(url, origin="http://evil.example.com"):
            pass

    with pytest.raises(InvalidStatus):
        asyncio.run(connect())


async def first_message(url, **options):
    async with ws_connect(url, origin="http://localhost:5180", **options) as socket:
        return json.loads(await socket.recv())


def test_voice_socket_refuses_a_stranger(server):
    url = transcribe_url(server())

    with pytest.raises(InvalidStatus):
        asyncio.run(first_message(url))

    with pytest.raises(InvalidStatus):
        asyncio.run(first_message(url, subprotocols=["bearer", "not-a-session"]))


def test_voice_socket_opens_for_a_signed_in_person(server):
    url = server(AWS_ACCESS_KEY_ID="invalid", AWS_SECRET_ACCESS_KEY="invalid", AWS_SESSION_TOKEN=None)

    message = asyncio.run(first_message(transcribe_url(url), subprotocols=["bearer", token_for(url)]))

    assert message["type"] == TranscriptType.UNAVAILABLE


@pytest.mark.skipif(not boto3.Session().get_credentials(), reason="needs AWS credentials")
def test_voice_socket_streams_to_transcribe(server):
    url = server()
    token = token_for(url)
    url = transcribe_url(url)

    async def stream_silence():
        async with ws_connect(url, origin="http://localhost:5180", subprotocols=["bearer", token]) as socket:
            for _ in range(10):
                await socket.send(b"\x00\x00" * 1600)  # 100 ms of 16 kHz silence
            await socket.send("stop")
            return [json.loads(message) async for message in socket]

    messages = asyncio.run(stream_silence())

    assert all(message["type"] != TranscriptType.UNAVAILABLE for message in messages)
    assert all(message["type"] != TranscriptType.ERROR for message in messages)
