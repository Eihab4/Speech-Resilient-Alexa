from fastmcp import Context, FastMCP
from fastmcp.server.lifespan import lifespan

from brain.factory import create_brain
from config import get_settings
from memory import SqliteMemoryStore
from messages import ToolDescription
from tools.cancel_request import cancel_request as cancel
from tools.do_confirmed_request import do_confirmed_request as do_confirmed
from tools.understand_speech import understand

settings = get_settings()


@lifespan
async def resources(server: FastMCP):
    store = SqliteMemoryStore(settings.memory.db_path)
    yield {"brain": create_brain(settings), "store": store}
    store.close()


mcp = FastMCP(settings.server.name, lifespan=resources)


@mcp.tool(description=ToolDescription.UNDERSTAND_SPEECH)
def understand_speech(user_id: str, heard: str, ctx: Context) -> dict:
    resources = ctx.lifespan_context
    return understand(resources["brain"], resources["store"], settings.memory.company_id, user_id, heard)


@mcp.tool(description=ToolDescription.DO_CONFIRMED_REQUEST)
def do_confirmed_request(user_id: str, pending_id: str, ctx: Context) -> dict:
    return do_confirmed(ctx.lifespan_context["store"], settings.memory.company_id, user_id, pending_id)


@mcp.tool(description=ToolDescription.CANCEL_REQUEST)
def cancel_request(user_id: str, ctx: Context) -> dict:
    return cancel(ctx.lifespan_context["store"], settings.memory.company_id, user_id)


if __name__ == "__main__":
    mcp.run(
        transport=settings.server.transport,
        host=settings.server.host,
        port=settings.server.port,
        path=settings.server.path,
    )
