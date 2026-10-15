import re

import uvicorn
from fastmcp import Context, FastMCP
from fastmcp.server.lifespan import lifespan
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, WebSocketRoute

from brain.factory import create_brain, create_summarizer
from config import get_settings
from memory import History, SqliteMemoryStore
from messages import ToolDescription
from speech import PollySynthesizer, create_speak_endpoint
from tools.cancel_request import cancel_request as cancel
from tools.do_confirmed_request import do_confirmed_request as do_confirmed
from tools.resume_unfinished import resume_unfinished as resume
from tools.understand_speech import understand
from transcription import create_transcribe_endpoint

settings = get_settings()


@lifespan
async def resources(server: FastMCP):
    store = SqliteMemoryStore(settings.memory.db_path, settings.memory.unfinished_ttl_hours)
    history = History(
        store, create_summarizer(settings), settings.memory.recent_messages, settings.memory.summary_trigger_words
    )
    yield {"brain": create_brain(settings), "store": store, "history": history}
    store.close()


mcp = FastMCP(settings.server.name, lifespan=resources)

# Lets the browser frontend in web/ call /mcp directly. Pages on localhost are always allowed, on any
# port, matching FastMCP's own trust of loopback origins; MCP_CORS_ORIGINS adds any others.
# The session id header must be exposed, or the browser hides it and the client cannot keep its MCP session.
LOCAL_ORIGIN = r"http://(localhost|127\.0\.0\.1)(:\d+)?"

cors = Middleware(
    CORSMiddleware,
    allow_origin_regex=LOCAL_ORIGIN,
    allow_origins=settings.server.cors_origins,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


def is_allowed_origin(origin: str | None) -> bool:
    """The same pages CORS allows. No origin means a non-browser client, which CORS does not limit either."""
    return origin is None or bool(re.fullmatch(LOCAL_ORIGIN, origin)) or origin in settings.server.cors_origins


@mcp.tool(description=ToolDescription.UNDERSTAND_SPEECH)
def understand_speech(user_id: str, heard: str, ctx: Context) -> dict:
    r = ctx.lifespan_context
    return understand(r["brain"], r["store"], r["history"], settings.memory.company_id, user_id, heard)


@mcp.tool(description=ToolDescription.DO_CONFIRMED_REQUEST)
def do_confirmed_request(user_id: str, pending_id: str, ctx: Context) -> dict:
    return do_confirmed(ctx.lifespan_context["store"], settings.memory.company_id, user_id, pending_id)


@mcp.tool(description=ToolDescription.RESUME_UNFINISHED)
def resume_unfinished(user_id: str, ctx: Context) -> dict:
    return resume(ctx.lifespan_context["store"], settings.memory.company_id, user_id)


@mcp.tool(description=ToolDescription.CANCEL_REQUEST)
def cancel_request(user_id: str, ctx: Context) -> dict:
    return cancel(ctx.lifespan_context["store"], settings.memory.company_id, user_id)


def create_app():
    """The MCP app at /mcp, plus the voice WebSocket, which FastMCP's own routes cannot express."""
    app = mcp.http_app(path=settings.server.path, transport=settings.server.transport, middleware=[cors])
    transcribe = create_transcribe_endpoint(settings.transcribe, is_allowed_origin)
    app.router.routes.append(WebSocketRoute(settings.transcribe.path, transcribe))
    speak = create_speak_endpoint(PollySynthesizer(settings.polly))
    app.router.routes.append(Route(settings.polly.path, speak, methods=["POST"]))
    return app


if __name__ == "__main__":
    uvicorn.run(create_app(), host=settings.server.host, port=settings.server.port)
