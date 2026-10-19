import logging
import re
from http import HTTPStatus

from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from memory import Helper, MemoryStore, Profile
from messages import TELEGRAM_LINK, ErrorMessage
from notify import TelegramBot, TelegramError
from people.guard import Guard, bearer
from people.passwords import check_password, hash_password
from people.sessions import Sessions

logger = logging.getLogger(__name__)

USERNAME = re.compile(r"[a-z0-9._-]{3,30}")
MIN_PASSWORD_LENGTH = 6
# Checked when the username doesn't exist, so a wrong username takes as long as a wrong password.
NO_ACCOUNT = hash_password("no account")


class Body(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class SignUpBody(Body):
    username: str = ""
    name: str = ""
    password: str = ""


class SignInBody(Body):
    username: str = ""
    password: str = ""


class ProfileBody(Body):
    name: str = ""
    home_address: str | None = None


class HelperBody(Body):
    name: str = ""


def _error(message: ErrorMessage, status: HTTPStatus) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def _read[T: Body](request: Request, model: type[T]) -> T:
    """The request's JSON body; anything unreadable counts as empty, and the checks after say what's missing."""
    try:
        return model.model_validate_json(await request.body())
    except ValidationError:
        return model()


def create_people_routes(
    store: MemoryStore, sessions: Sessions, guard: Guard, bot: TelegramBot | None, company_id: str
) -> list[Route]:
    """The page's own account and setup, done on a screen, not by voice: signing in, the person's profile, and
    who gets their emergency alerts. Plain routes, not MCP tools, so they stay out of the tools an AI host
    chooses from. The username is the person's user_id in the MCP tools."""

    def session_for(username: str) -> dict:
        token = sessions.open(username)
        profile = store.profile(company_id, username)
        return {"token": token, "username": username, "name": profile.name if profile else username}

    async def sign_up(request: Request) -> Response:
        body = await _read(request, SignUpBody)
        username = body.username.lower()
        if not USERNAME.fullmatch(username):
            return _error(ErrorMessage.USERNAME_INVALID, HTTPStatus.BAD_REQUEST)
        if not body.name:
            return _error(ErrorMessage.NAME_MISSING, HTTPStatus.BAD_REQUEST)
        if len(body.password) < MIN_PASSWORD_LENGTH:
            return _error(ErrorMessage.PASSWORD_TOO_SHORT, HTTPStatus.BAD_REQUEST)
        password_hash = await run_in_threadpool(hash_password, body.password)
        if not store.create_account(company_id, username, password_hash):
            return _error(ErrorMessage.USERNAME_TAKEN, HTTPStatus.CONFLICT)
        earlier = store.profile(company_id, username)
        store.save_profile(
            company_id, username, Profile(name=body.name, home_address=earlier.home_address if earlier else None)
        )
        return JSONResponse(session_for(username), status_code=HTTPStatus.CREATED)

    async def sign_in(request: Request) -> Response:
        body = await _read(request, SignInBody)
        username = body.username.lower()
        stored = store.password_hash(company_id, username)
        matches = await run_in_threadpool(check_password, body.password, stored or NO_ACCOUNT)
        if stored is None or not matches:
            return _error(ErrorMessage.SIGN_IN_FAILED, HTTPStatus.UNAUTHORIZED)
        return JSONResponse(session_for(username))

    async def sign_out(request: Request) -> Response:
        if token := bearer(request):
            sessions.close(token)
        return Response(status_code=HTTPStatus.NO_CONTENT)

    async def me(request: Request, username: str) -> Response:
        profile = store.profile(company_id, username)
        return JSONResponse({"username": username, "name": profile.name if profile else username})

    async def bot_name() -> str | None:
        if bot is None:
            return None
        try:
            return await run_in_threadpool(bot.username)
        except TelegramError:
            logger.exception(ErrorMessage.TELEGRAM_UNREACHABLE.format(method="getMe"))
            return None

    def helper_json(helper: Helper, username: str | None) -> dict:
        # The link is only shown until the helper opens it.
        link = None if helper.linked or not username else TELEGRAM_LINK.format(username=username, code=helper.link_code)
        return {"id": helper.id, "name": helper.name, "linked": helper.linked, "link": link}

    async def get_profile(request: Request, username: str) -> Response:
        profile = store.profile(company_id, username) or Profile(name="")
        return JSONResponse(profile.model_dump())

    async def save_profile(request: Request, username: str) -> Response:
        body = await _read(request, ProfileBody)
        if not body.name:
            return _error(ErrorMessage.NAME_MISSING, HTTPStatus.BAD_REQUEST)
        profile = Profile(name=body.name, home_address=body.home_address or None)
        store.save_profile(company_id, username, profile)
        return JSONResponse(profile.model_dump())

    async def list_helpers(request: Request, username: str) -> Response:
        bot_username = await bot_name()
        helpers = [helper_json(helper, bot_username) for helper in store.helpers(company_id, username)]
        return JSONResponse({"telegram": bot_username is not None, "helpers": helpers})

    async def add_helper(request: Request, username: str) -> Response:
        body = await _read(request, HelperBody)
        if not body.name:
            return _error(ErrorMessage.NAME_MISSING, HTTPStatus.BAD_REQUEST)
        helper = store.add_helper(company_id, username, Helper(name=body.name))
        return JSONResponse(helper_json(helper, await bot_name()), status_code=HTTPStatus.CREATED)

    async def remove_helper(request: Request, username: str) -> Response:
        if not store.remove_helper(company_id, username, request.path_params["helper_id"]):
            return _error(ErrorMessage.HELPER_NOT_FOUND, HTTPStatus.NOT_FOUND)
        return Response(status_code=HTTPStatus.NO_CONTENT)

    return [
        Route("/signup", sign_up, methods=["POST"]),
        Route("/signin", sign_in, methods=["POST"]),
        Route("/signout", sign_out, methods=["POST"]),
        Route("/me", guard.require(me), methods=["GET"]),
        Route("/profile", guard.require(get_profile), methods=["GET"]),
        Route("/profile", guard.require(save_profile), methods=["PUT"]),
        Route("/helpers", guard.require(list_helpers), methods=["GET"]),
        Route("/helpers", guard.require(add_helper), methods=["POST"]),
        Route("/helpers/{helper_id}", guard.require(remove_helper), methods=["DELETE"]),
    ]
