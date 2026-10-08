from fastmcp import Context, FastMCP
from fastmcp.server.lifespan import lifespan

from brain.factory import create_brain
from config import get_settings
from memory import SqliteMemoryStore
from tools.understand_speech import understand

settings = get_settings()


@lifespan
async def resources(server: FastMCP):
    store = SqliteMemoryStore(settings.memory.db_path)
    yield {"brain": create_brain(settings), "store": store}
    store.close()


mcp = FastMCP(settings.server.name, lifespan=resources)


@mcp.tool()
def understand_speech(user_id: str, heard: str, ctx: Context) -> dict:
    brain, store = ctx.lifespan_context["brain"], ctx.lifespan_context["store"]
    return understand(brain, store, settings.memory.company_id, user_id, heard)


if __name__ == "__main__":
    mcp.run(
        transport=settings.server.transport,
        host=settings.server.host,
        port=settings.server.port,
        path=settings.server.path,
    )
