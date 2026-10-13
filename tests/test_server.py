from urllib.error import HTTPError
from urllib.request import Request, urlopen

from support import with_client


def preflight(url: str, origin: str):
    request = Request(url, method="OPTIONS", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    with urlopen(request) as response:
        return response.status, response.headers


async def describe(client):
    tools = await client.list_tools()
    return client.protocol_version, [tool.name for tool in tools]


def test_server_runs_on_configured_port_and_path(server):
    url = server(path="/speech", LLM_PROVIDER="bedrock")

    version, tools = with_client(url, describe)

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
