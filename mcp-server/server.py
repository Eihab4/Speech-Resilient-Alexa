from brain.factory import create_brain
from fastmcp import FastMCP
from tools.understand_speech import understand

mcp = FastMCP("speech-resilient-alexa")
brain = create_brain()


@mcp.tool()
def understand_speech(user_id: str, heard: str) -> dict:
    return understand(brain, user_id, heard)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
