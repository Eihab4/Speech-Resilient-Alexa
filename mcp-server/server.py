from brain.factory import create_brain
from config import get_settings
from fastmcp import FastMCP
from tools.understand_speech import understand

settings = get_settings()
mcp = FastMCP(settings.server.name)
brain = create_brain(settings)


@mcp.tool()
def understand_speech(user_id: str, heard: str) -> dict:
    return understand(brain, user_id, heard)


if __name__ == "__main__":
    mcp.run(
        transport=settings.server.transport,
        host=settings.server.host,
        port=settings.server.port,
        path=settings.server.path,
    )
