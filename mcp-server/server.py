from fastmcp import FastMCP
from tools.understand_speech import understand

mcp = FastMCP("speech-resilient-alexa")


@mcp.tool()
def understand_speech(user_id: str, heard: str) -> dict:
    return understand(user_id, heard)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")