import re
from threading import Event, Thread

import uvicorn
from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.lifespan import lifespan
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, WebSocketRoute

from brain.factory import create_brain, create_summarizer
from config import get_settings
from location import create_geocoder
from memory import History, SqliteMemoryStore
from messages import ToolDescription
from notify import HelperLinker, create_bot, create_notifier
from pacing import Pacing
from people import Guard, Sessions, SessionVerifier, create_people_routes
from speech import PollySynthesizer, create_speak_endpoint
from tools.cancel_request import cancel_request as cancel
from tools.do_confirmed_request import do_confirmed_request as do_confirmed
from tools.emergency_sos import emergency_sos as send_sos
from tools.resume_unfinished import resume_unfinished as resume
from tools.speech_trend import speech_trend as trend
from tools.understand_speech import understand
from transcription import create_transcribe_endpoint

settings = get_settings()
bot = create_bot(settings)


def open_store() -> SqliteMemoryStore:
    return SqliteMemoryStore(settings.memory.db_path, settings.memory.unfinished_ttl_hours)


people = open_store()
sessions = Sessions(people, settings.memory.company_id, settings.session.ttl_hours)
guard = Guard(sessions)


@lifespan
async def resources(server: FastMCP):
    store = open_store()
    history = History(
        store, create_summarizer(settings), settings.memory.recent_messages, settings.memory.summary_trigger_words
    )
    # Helpers link themselves by opening the bot; a background thread reads those messages, on its own connection.
    stop, links = Event(), open_store()
    if bot:
        Thread(target=HelperLinker(bot, links).run, args=(stop,), daemon=True).start()
    yield {
        "brain": create_brain(settings),
        "store": store,
        "history": history,
        "notifier": create_notifier(bot),
        "geocoder": create_geocoder(settings),
        "pacing": Pacing(store, settings.pause),
    }
    stop.set()
    # A summary may still be being written; closing the store under it can crash SQLite.
    history.wait(timeout=10)
    links.close()
    store.close()


mcp = FastMCP(settings.server.name, lifespan=resources, auth=SessionVerifier(sessions))


def caller() -> str:
    return get_access_token().subject


# Lets the browser frontend in web/ call /mcp directly. Pages on localhost are always allowed, on any
# port, matching FastMCP's own trust of loopback origins; MCP_CORS_ORIGINS adds any others.
# The session id header must be exposed, or the browser hides it and the client cannot keep its MCP session.
LOCAL_ORIGIN = r"http://(localhost|127\.0\.0\.1)(:\d+)?"

cors = Middleware(
    CORSMiddleware,
    allow_origin_regex=LOCAL_ORIGIN,
    allow_origins=settings.server.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


def is_allowed_origin(origin: str | None) -> bool:
    """The same pages CORS allows. No origin means a non-browser client, which CORS does not limit either."""
    return origin is None or bool(re.fullmatch(LOCAL_ORIGIN, origin)) or origin in settings.server.cors_origins


@mcp.tool(description=ToolDescription.UNDERSTAND_SPEECH)
def understand_speech(heard: str, ctx: Context, pauses_ms: list[int] | None = None) -> dict:
    r = ctx.lifespan_context
    return understand(
        r["brain"],
        r["store"],
        r["history"],
        settings.memory.company_id,
        caller(),
        heard,
        settings.sos.countdown_seconds,
        r["pacing"],
        pauses_ms,
        settings.yes_no.after_tries,
    )


@mcp.tool(description=ToolDescription.DO_CONFIRMED_REQUEST)
def do_confirmed_request(pending_id: str, ctx: Context) -> dict:
    return do_confirmed(ctx.lifespan_context["store"], settings.memory.company_id, caller(), pending_id)


@mcp.tool(description=ToolDescription.RESUME_UNFINISHED)
def resume_unfinished(ctx: Context) -> dict:
    return resume(ctx.lifespan_context["store"], settings.memory.company_id, caller())


@mcp.tool(description=ToolDescription.CANCEL_REQUEST)
def cancel_request(ctx: Context) -> dict:
    return cancel(ctx.lifespan_context["store"], settings.memory.company_id, caller())


@mcp.tool(description=ToolDescription.SPEECH_TREND)
def speech_trend(ctx: Context) -> dict:
    return trend(ctx.lifespan_context["store"], settings.memory.company_id, caller(), settings.trend.days)


@mcp.tool(description=ToolDescription.EMERGENCY_SOS)
def emergency_sos(ctx: Context, latitude: float | None = None, longitude: float | None = None) -> dict:
    r = ctx.lifespan_context
    return send_sos(
        r["store"],
        r["notifier"],
        r["geocoder"],
        settings.sos,
        settings.memory.company_id,
        caller(),
        latitude,
        longitude,
    )


def create_app():
    """The MCP app at /mcp, plus the voice routes and the family's setup routes, which FastMCP's own routes
    cannot express."""
    app = mcp.http_app(path=settings.server.path, transport=settings.server.transport, middleware=[cors])
    transcribe = create_transcribe_endpoint(settings.transcribe, is_allowed_origin, guard.user)
    app.router.routes.append(WebSocketRoute(settings.transcribe.path, transcribe))
    speak = create_speak_endpoint(PollySynthesizer(settings.polly))
    app.router.routes.append(
        Route(settings.polly.path, guard.require(lambda request, _: speak(request)), methods=["POST"])
    )
    app.router.routes.extend(
        create_people_routes(people, sessions, guard, bot, settings.memory.company_id, Pacing(people, settings.pause))
    )
    return app


if __name__ == "__main__":
    uvicorn.run(create_app(), host=settings.server.host, port=settings.server.port)
