import pytest
from mcp.shared.exceptions import MCPError

from support import base_url, http, sign_up, token_for, with_client

LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


async def say(client, heard):
    return (await client.call_tool("understand_speech", {"heard": heard})).structured_content


async def tool_inputs(client):
    return {tool.name: set(tool.input_schema["properties"]) for tool in await client.list_tools()}


def test_the_tools_need_a_sign_in(server):
    url = server()

    assert http(url, "POST", LIST_TOOLS)[0] == 401
    with pytest.raises(MCPError):
        with_client(url, lambda client: say(client, "tomorrow"))


def test_a_made_up_token_is_refused(server):
    url = server()

    assert http(url, "POST", LIST_TOOLS, token="not-a-session")[0] == 401


def test_a_signed_out_token_is_refused(server):
    url = server()
    token = sign_up(url, "rana_h")
    assert "understand_speech" in with_client(url, tool_inputs, token)

    http(f"{base_url(url)}/signout", "POST", token=token)

    assert http(url, "POST", LIST_TOOLS, token=token)[0] == 401


def test_no_tool_takes_a_user_id(server):
    url = server()

    inputs = with_client(url, tool_inputs, token_for(url))

    assert inputs["understand_speech"] == {"heard", "pauses_ms"}
    assert all("user_id" not in fields for fields in inputs.values())


def test_each_person_only_reaches_their_own_memory(server):
    url = server()

    with_client(url, lambda client: say(client, "tomorrow"), token_for(url, "rana_h"))
    with_client(url, lambda client: say(client, "doctor ten"), token_for(url, "rana_h"))
    eihab = with_client(url, lambda client: say(client, "ten"), token_for(url, "eihab_m"))

    assert "doctor" not in eihab["say"]
