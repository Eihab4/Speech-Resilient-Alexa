from support import with_client


async def describe(client):
    tools = await client.list_tools()
    return client.protocol_version, [tool.name for tool in tools]


def test_server_runs_on_configured_port_and_path(server):
    url = server(path="/speech", LLM_PROVIDER="bedrock")

    version, tools = with_client(url, describe)

    assert version >= "2025-11-25"
    assert "understand_speech" in tools
